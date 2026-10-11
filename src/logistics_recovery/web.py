import json
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from .assignments import AssignmentService
from .auth import authenticate
from .config import Settings
from .domain import DomainError, Identifier, Nonnegative, Operator, Record, WorkflowRunner


class DecisionRequest(Record):
    proposal_id: Identifier
    incident_version: Nonnegative
    decision: Literal["approve", "reject"]


class CommitRequest(Record):
    proposal_id: Identifier


async def read_input(request: Request, record_type):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 8192: raise HTTPException(413, "Request too large")
    content_type = request.headers.get("content-type", "").split(";", 1)[0]
    try:
        if content_type == "application/json":
            data = json.loads(body)
        elif content_type == "application/x-www-form-urlencoded":
            pairs = parse_qsl(body.decode("utf-8"), keep_blank_values=True, max_num_fields=10, strict_parsing=True)
            data = dict(pairs)
            if len(data) != len(pairs): raise ValueError("Duplicate fields")
            if "incident_version" in data:
                value = data["incident_version"]
                if not value.isascii() or not value.isdigit(): raise ValueError("Invalid version")
                data["incident_version"] = int(value)
        else:
            raise HTTPException(415, "Unsupported request format")
        return record_type.model_validate(data)
    except (ValueError, UnicodeError, ValidationError):
        raise HTTPException(422, "Invalid request") from None


def create_app(settings: Settings, service: AssignmentService, workflow: WorkflowRunner | None = None) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    repository = service.repository
    templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
    security = HTTPBasic()
    app.state.settings, app.state.service, app.state.workflow = settings, service, workflow

    def operator_dependency(credentials: HTTPBasicCredentials = Depends(security)) -> Operator:
        try:
            return authenticate(credentials.username, credentials.password, settings)
        except DomainError:
            raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Basic"}) from None

    def origin_dependency(request: Request) -> None:
        if request.headers.get("origin") != settings.origin:
            raise HTTPException(403, "Origin not allowed")

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, error: DomainError):
        status = 404 if error.code.endswith("not_found") else 403 if error.code == "operator_mismatch" else 503 if error.code == "workflow_unavailable" else 409
        return JSONResponse({"code": error.code}, status_code=status)

    @app.middleware("http")
    async def private_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Content-Security-Policy": "default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'"})
        return response

    def require_proposal(incident_id: str, proposal_id: str):
        repository.snapshot(incident_id)
        proposal = repository.proposal(proposal_id)
        if proposal.incident_id != incident_id: raise DomainError("incident_mismatch")
        return proposal

    def action_response(request: Request, incident_id: str, result: dict):
        if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
            return RedirectResponse(f"/incidents/{incident_id}", status_code=303)
        return JSONResponse(result)

    def context():
        return {"mode_label": "Scripted replay" if settings.mode == "replay" else "Live model"}

    @app.get("/")
    def incident_list(request: Request, operator: Operator = Depends(operator_dependency)):
        incidents = [{"snapshot": repository.snapshot(i), "assignment": repository.assignment(i)} for i in repository.list_incidents()]
        return templates.TemplateResponse(request=request, name="list.html", context={**context(), "incidents": incidents})

    @app.get("/incidents/{incident_id}")
    def incident_detail(incident_id: str, request: Request, operator: Operator = Depends(operator_dependency)):
        snapshot = repository.snapshot(incident_id)
        return templates.TemplateResponse(request=request, name="detail.html", context={**context(), "snapshot": snapshot, "case_status": repository.terminal_status(incident_id), "proposal": repository.latest_proposal(incident_id), "assignment": repository.assignment(incident_id), "history": repository.history(incident_id), "stats": repository.stats(incident_id), "pretty": lambda value: json.dumps(value, indent=2)})

    @app.post("/incidents/{incident_id}/investigate")
    async def investigate(incident_id: str, request: Request, operator: Operator = Depends(operator_dependency), origin: None = Depends(origin_dependency)):
        repository.snapshot(incident_id)
        if workflow is None: raise DomainError("workflow_unavailable")
        result = await run_in_threadpool(workflow.start, incident_id)
        return action_response(request, incident_id, result.model_dump(mode="json"))

    @app.post("/incidents/{incident_id}/decision")
    async def decision(incident_id: str, request: Request, operator: Operator = Depends(operator_dependency), origin: None = Depends(origin_dependency)):
        data = await read_input(request, DecisionRequest)
        require_proposal(incident_id, data.proposal_id)
        if data.decision == "reject":
            service.reject(data.proposal_id, operator)
            result = {"status": "rejected"}
        else:
            result = service.approve(data.proposal_id, data.incident_version, operator).model_dump(mode="json")
            if workflow is not None:
                result = (await run_in_threadpool(workflow.resume, incident_id, data.proposal_id)).model_dump(mode="json")
        return action_response(request, incident_id, result)

    @app.post("/incidents/{incident_id}/commit")
    async def commit(incident_id: str, request: Request, operator: Operator = Depends(operator_dependency), origin: None = Depends(origin_dependency)):
        data = await read_input(request, CommitRequest)
        require_proposal(incident_id, data.proposal_id)
        return action_response(request, incident_id, service.commit(data.proposal_id, operator).model_dump(mode="json"))

    return app

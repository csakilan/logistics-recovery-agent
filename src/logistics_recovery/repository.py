import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .domain import Approval, Assignment, Courier, DomainError, IncidentEvent, Job, Policy, Proposal, Quote, Snapshot

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS couriers(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS policies(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS incidents(
 id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id), policy_id TEXT NOT NULL REFERENCES policies(id),
 version INTEGER NOT NULL, now_min INTEGER NOT NULL, model_calls INTEGER NOT NULL DEFAULT 0,
 proposal_attempts INTEGER NOT NULL DEFAULT 0, terminal_status TEXT);
CREATE TABLE IF NOT EXISTS quotes(id TEXT PRIMARY KEY, incident_id TEXT NOT NULL REFERENCES incidents(id), payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source_events(incident_id TEXT NOT NULL REFERENCES incidents(id), id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(incident_id,id));
CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY, incident_id TEXT NOT NULL REFERENCES incidents(id), payload TEXT NOT NULL, rejected INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY, proposal_id TEXT UNIQUE NOT NULL REFERENCES proposals(id), incident_version INTEGER NOT NULL, operator_id TEXT NOT NULL, consumed INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS assignments(id TEXT PRIMARY KEY, incident_id TEXT UNIQUE NOT NULL REFERENCES incidents(id), proposal_id TEXT NOT NULL REFERENCES proposals(id), courier_id TEXT NOT NULL REFERENCES couriers(id), operation_id TEXT UNIQUE NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, incident_id TEXT NOT NULL REFERENCES incidents(id), kind TEXT NOT NULL, operation_id TEXT, payload TEXT NOT NULL, UNIQUE(kind,operation_id));
"""


class Repository:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path, isolation_level=None, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self):
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def seed(self, snapshot: Snapshot) -> None:
        with self.transaction() as connection:
            if connection.execute("SELECT 1 FROM incidents WHERE id=?", (snapshot.incident_id,)).fetchone():
                raise DomainError("incident_exists")
            for table, records in (("jobs", (snapshot.job,)), ("policies", (snapshot.policy,)), ("couriers", snapshot.couriers)):
                for record in records:
                    connection.execute(f"INSERT OR IGNORE INTO {table}(id,payload) VALUES (?,?)", (record.id, record.model_dump_json()))
            connection.execute("INSERT INTO incidents(id,job_id,policy_id,version,now_min) VALUES (?,?,?,?,?)", (snapshot.incident_id, snapshot.job.id, snapshot.policy.id, snapshot.incident_version, snapshot.now_min))
            for quote in snapshot.quotes:
                connection.execute("INSERT INTO quotes VALUES (?,?,?)", (quote.id, snapshot.incident_id, quote.model_dump_json()))
            for event in snapshot.events:
                connection.execute("INSERT INTO source_events VALUES (?,?,?)", (snapshot.incident_id, event.id, event.model_dump_json()))

    def _snapshot(self, connection, incident_id: str) -> Snapshot:
        incident = connection.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if incident is None: raise DomainError("incident_not_found")
        job = Job.model_validate_json(connection.execute("SELECT payload FROM jobs WHERE id=?", (incident["job_id"],)).fetchone()[0])
        policy = Policy.model_validate_json(connection.execute("SELECT payload FROM policies WHERE id=?", (incident["policy_id"],)).fetchone()[0])
        return Snapshot(
            incident_id=incident_id, incident_version=incident["version"], now_min=incident["now_min"], job=job, policy=policy,
            couriers=tuple(Courier.model_validate_json(row[0]) for row in connection.execute("SELECT payload FROM couriers ORDER BY id")),
            quotes=tuple(Quote.model_validate_json(row[0]) for row in connection.execute("SELECT payload FROM quotes WHERE incident_id=? ORDER BY id", (incident_id,))),
            events=tuple(IncidentEvent.model_validate_json(row[0]) for row in connection.execute("SELECT payload FROM source_events WHERE incident_id=? ORDER BY id", (incident_id,))),
        )

    def snapshot(self, incident_id: str) -> Snapshot:
        with self.connection() as connection:
            connection.execute("BEGIN")
            return self._snapshot(connection, incident_id)

    def _assignment(self, connection, incident_id: str) -> Assignment | None:
        row = connection.execute("SELECT * FROM assignments WHERE incident_id=?", (incident_id,)).fetchone()
        return Assignment.model_validate(dict(row)) if row else None

    def assignment(self, incident_id: str) -> Assignment | None:
        with self.connection() as connection:
            return self._assignment(connection, incident_id)

    def _proposal(self, connection, proposal_id: str) -> Proposal:
        row = connection.execute("SELECT payload FROM proposals WHERE id=?", (proposal_id,)).fetchone()
        if row is None: raise DomainError("proposal_not_found")
        return Proposal.model_validate_json(row[0])

    def proposal(self, proposal_id: str) -> Proposal:
        with self.connection() as connection:
            return self._proposal(connection, proposal_id)

    def approval(self, proposal_id: str) -> Approval | None:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM approvals WHERE proposal_id=?", (proposal_id,)).fetchone()
            return Approval.model_validate(dict(row)) if row else None

    def latest_proposal(self, incident_id: str) -> Proposal | None:
        with self.connection() as connection:
            row = connection.execute("SELECT payload FROM proposals WHERE incident_id=? ORDER BY rowid DESC LIMIT 1", (incident_id,)).fetchone()
            return Proposal.model_validate_json(row[0]) if row else None

    def list_incidents(self) -> list[str]:
        with self.connection() as connection:
            return [row[0] for row in connection.execute("SELECT id FROM incidents ORDER BY id")]

    def audit(self, connection, incident_id: str, kind: str, payload: dict, operation_id: str | None = None) -> None:
        connection.execute("INSERT INTO audit(incident_id,kind,operation_id,payload) VALUES (?,?,?,?)", (incident_id, kind, operation_id, json.dumps(payload)))

    def _history(self, connection, incident_id: str) -> list[dict]:
        activity = [{"kind": row["kind"], "payload": json.loads(row["payload"])} for row in connection.execute("SELECT kind,payload FROM audit WHERE incident_id=? ORDER BY seq", (incident_id,))]
        simulated_ids = {item["payload"]["id"] for item in activity if item["kind"] in {"simulated_pickup", "simulated_delivery"}}
        initial = [{"kind": "source_event", "payload": json.loads(row[0])} for row in connection.execute("SELECT payload FROM source_events WHERE incident_id=? ORDER BY rowid", (incident_id,)) if json.loads(row[0])["id"] not in simulated_ids]
        return initial + activity

    def history(self, incident_id: str) -> list[dict]:
        with self.connection() as connection:
            connection.execute("BEGIN")
            self._snapshot(connection, incident_id)
            return self._history(connection, incident_id)

    def _stats(self, connection, incident_id: str) -> dict[str, int]:
        row = connection.execute("SELECT model_calls,proposal_attempts FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if row is None: raise DomainError("incident_not_found")
        return {"model_calls": row[0], "proposal_attempts": row[1],
            "assignments": connection.execute("SELECT count(*) FROM assignments WHERE incident_id=?", (incident_id,)).fetchone()[0],
            "commit_events": connection.execute("SELECT count(*) FROM audit WHERE incident_id=? AND kind='assignment_committed'", (incident_id,)).fetchone()[0]}

    def stats(self, incident_id: str) -> dict[str, int]:
        with self.connection() as connection:
            return self._stats(connection, incident_id)

    def read_incident(self, incident_id: str) -> dict:
        """Materialize the complete dispatcher state at one database snapshot."""
        with self.connection() as connection:
            connection.execute("BEGIN")
            snapshot = self._snapshot(connection, incident_id)
            assignment = self._assignment(connection, incident_id)
            if assignment:
                proposal = self._proposal(connection, assignment.proposal_id)
            else:
                row = connection.execute("SELECT payload FROM proposals WHERE incident_id=? ORDER BY rowid DESC LIMIT 1", (incident_id,)).fetchone()
                proposal = Proposal.model_validate_json(row[0]) if row else None
            row = connection.execute("SELECT * FROM approvals WHERE proposal_id=?", (proposal.id,)).fetchone() if proposal else None
            approval = Approval.model_validate(dict(row)) if row else None
            terminal = connection.execute("SELECT terminal_status FROM incidents WHERE id=?", (incident_id,)).fetchone()[0]
            return {"snapshot": snapshot, "assignment": assignment, "proposal": proposal,
                "approval": approval, "terminal": terminal, "history": self._history(connection, incident_id),
                "stats": self._stats(connection, incident_id)}

    def log_event(self, incident_id: str, kind: str, payload: dict) -> None:
        with self.transaction() as connection:
            self.audit(connection, incident_id, kind, payload)

    def terminal_status(self, incident_id: str) -> str | None:
        with self.connection() as connection:
            row = connection.execute("SELECT terminal_status FROM incidents WHERE id=?", (incident_id,)).fetchone()
            if row is None: raise DomainError("incident_not_found")
            return row[0]

    def set_terminal(self, incident_id: str, status: str, detail: str = "") -> None:
        if status not in {"assigned", "rejected", "escalated"}: raise DomainError("invalid_status")
        with self.transaction() as connection:
            row = connection.execute("SELECT terminal_status FROM incidents WHERE id=?", (incident_id,)).fetchone()
            if row is None: raise DomainError("incident_not_found")
            if row[0] != status:
                connection.execute("UPDATE incidents SET terminal_status=? WHERE id=?", (status, incident_id))
                self.audit(connection, incident_id, f"case_{status}", {"detail": detail})

    def _reserve_count(self, incident_id: str, column: str, limit: int) -> int:
        with self.transaction() as connection:
            row = connection.execute(f"SELECT {column} FROM incidents WHERE id=?", (incident_id,)).fetchone()
            if row is None: raise DomainError("incident_not_found")
            if row[0] >= limit: raise DomainError("budget_exhausted")
            connection.execute(f"UPDATE incidents SET {column}={column}+1 WHERE id=?", (incident_id,))
            return row[0] + 1

    def reserve_model_call(self, incident_id: str, limit: int = 6) -> int:
        return self._reserve_count(incident_id, "model_calls", min(limit, 6))

    def reserve_proposal_attempt(self, incident_id: str, limit: int = 3) -> int:
        return self._reserve_count(incident_id, "proposal_attempts", min(limit, 3))

    def change_courier(self, courier_id: str, available: bool) -> None:
        if type(available) is not bool: raise DomainError("invalid_availability")
        with self.transaction() as connection:
            row = connection.execute("SELECT payload FROM couriers WHERE id=?", (courier_id,)).fetchone()
            if row is None: raise DomainError("courier_not_found")
            courier = Courier.model_validate_json(row[0])
            changed = courier.model_copy(update={"available": available, "version": courier.version + 1})
            connection.execute("UPDATE couriers SET payload=? WHERE id=?", (changed.model_dump_json(), courier_id))

    def advance_clock(self, incident_id: str, now_min: int) -> None:
        if type(now_min) is not int or now_min < 0: raise DomainError("invalid_clock")
        with self.transaction() as connection:
            snapshot = self._snapshot(connection, incident_id)
            if now_min < snapshot.now_min: raise DomainError("invalid_clock")
            if now_min != snapshot.now_min:
                connection.execute("UPDATE incidents SET now_min=?, version=version+1 WHERE id=?", (now_min, incident_id))
                self.audit(connection, incident_id, "simulated_clock", {"now_min": now_min})

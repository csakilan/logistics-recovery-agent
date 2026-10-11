from uuid import uuid4

from .domain import Approval, Assignment, Candidate, DomainError, Operator, Proposal
from .policy import evidence_records, validate_candidate
from .repository import Repository


class AssignmentService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def _current(self, connection, proposal: Proposal):
        snapshot = self.repository._snapshot(connection, proposal.incident_id)
        current = evidence_records(snapshot)
        if snapshot.incident_version != proposal.incident_version or any(current.get(name) != version for name, version in proposal.observed_versions):
            raise DomainError("stale_proposal")
        if not validate_candidate(proposal.candidate, snapshot).valid:
            raise DomainError("stale_proposal")
        return snapshot

    def propose(self, incident_id: str, candidate: Candidate, revision: int = 0) -> Proposal:
        with self.repository.transaction() as connection:
            snapshot = self.repository._snapshot(connection, incident_id)
            if self.repository._assignment(connection, incident_id): raise DomainError("assignment_conflict")
            report = validate_candidate(candidate, snapshot)
            if not report.valid: raise DomainError("invalid_proposal", ",".join(report.errors))
            versions = tuple(sorted((reference.rsplit("@", 1)[0], int(reference.rsplit("@", 1)[1])) for reference in set(candidate.evidence_ids)))
            proposal = Proposal(id=uuid4().hex, incident_id=incident_id, incident_version=snapshot.incident_version, candidate=candidate, observed_versions=versions, revision=revision)
            connection.execute("INSERT INTO proposals(id,incident_id,payload) VALUES (?,?,?)", (proposal.id, incident_id, proposal.model_dump_json()))
            self.repository.audit(connection, incident_id, "proposal_created", {"proposal_id": proposal.id, "quote_id": candidate.quote_id})
            return proposal

    def approve(self, proposal_id: str, expected_version: int, operator: Operator) -> Approval:
        with self.repository.transaction() as connection:
            proposal = self.repository._proposal(connection, proposal_id)
            row = connection.execute("SELECT rejected FROM proposals WHERE id=?", (proposal_id,)).fetchone()
            if row[0]: raise DomainError("proposal_rejected")
            if expected_version != proposal.incident_version: raise DomainError("stale_proposal")
            existing = connection.execute("SELECT * FROM approvals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if existing:
                approval = Approval.model_validate(dict(existing))
                if approval.operator_id != operator.id: raise DomainError("operator_mismatch")
                return approval
            self._current(connection, proposal)
            approval = Approval(id=uuid4().hex, proposal_id=proposal_id, incident_version=expected_version, operator_id=operator.id)
            connection.execute("INSERT INTO approvals VALUES (?,?,?,?,?)", (approval.id, proposal_id, expected_version, operator.id, 0))
            self.repository.audit(connection, proposal.incident_id, "proposal_approved", {"proposal_id": proposal_id, "operator_id": operator.id})
            return approval

    def reject(self, proposal_id: str, operator: Operator) -> None:
        with self.repository.transaction() as connection:
            proposal = self.repository._proposal(connection, proposal_id)
            if self.repository._assignment(connection, proposal.incident_id): raise DomainError("assignment_conflict")
            connection.execute("UPDATE proposals SET rejected=1 WHERE id=?", (proposal_id,))
            connection.execute("UPDATE incidents SET terminal_status='rejected' WHERE id=?", (proposal.incident_id,))
            self.repository.audit(connection, proposal.incident_id, "proposal_rejected", {"proposal_id": proposal_id, "operator_id": operator.id})

    def commit(self, proposal_id: str, operator: Operator) -> Assignment:
        with self.repository.transaction() as connection:
            proposal = self.repository._proposal(connection, proposal_id)
            approval = connection.execute("SELECT * FROM approvals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if approval is None: raise DomainError("approval_required")
            if approval["operator_id"] != operator.id: raise DomainError("operator_mismatch")
            existing = self.repository._assignment(connection, proposal.incident_id)
            if existing:
                if existing.proposal_id != proposal_id: raise DomainError("assignment_conflict")
                return existing
            rejected = connection.execute("SELECT rejected FROM proposals WHERE id=?", (proposal_id,)).fetchone()[0]
            if rejected: raise DomainError("proposal_rejected")
            if approval["consumed"]: raise DomainError("approval_consumed")
            snapshot = self._current(connection, proposal)
            quote = next(q for q in snapshot.quotes if q.id == proposal.candidate.quote_id)
            courier = next(c for c in snapshot.couriers if c.id == quote.courier_id)
            reserved = courier.model_copy(update={"free_capacity": courier.free_capacity - snapshot.job.parcel_count, "version": courier.version + 1})
            connection.execute("UPDATE couriers SET payload=? WHERE id=?", (reserved.model_dump_json(), courier.id))
            assignment = Assignment(id=uuid4().hex, incident_id=proposal.incident_id, proposal_id=proposal_id, courier_id=courier.id, operation_id=proposal.incident_id)
            connection.execute("INSERT INTO assignments(id,incident_id,proposal_id,courier_id,operation_id,status) VALUES (?,?,?,?,?,?)", (assignment.id, assignment.incident_id, assignment.proposal_id, assignment.courier_id, assignment.operation_id, assignment.status))
            connection.execute("UPDATE approvals SET consumed=1 WHERE proposal_id=?", (proposal_id,))
            connection.execute("UPDATE incidents SET version=version+1, terminal_status='assigned' WHERE id=?", (proposal.incident_id,))
            self.repository.audit(connection, proposal.incident_id, "assignment_committed", assignment.model_dump(), assignment.operation_id)
            return assignment

import pytest
from logistics_recovery.domain import DomainError


@pytest.fixture
def registry(repo):
    from logistics_recovery.tools import ToolRegistry
    return ToolRegistry(repo)


def call(name, arguments=None):
    from logistics_recovery.model import ToolCall
    return ToolCall(id="call-1", name=name, arguments=arguments or {})


@pytest.mark.parametrize("name,record_id", [("get_order", "job:j1@1"), ("get_couriers", "courier:c1@1"), ("get_quotes", "quote:q1@1"), ("get_policy", "policy:p1@1"), ("get_events", "event:e1@1")])
def test_scoped_read_returns_evidence(registry, name, record_id):
    result = registry.execute("i1", call(name))
    assert record_id in result["evidence_ids"]
    assert result["records"]


@pytest.mark.parametrize("name", ["commit_assignment", "approve", "execute_sql", "read_file", "fetch_url"])
def test_agent_cannot_dispatch_writes_or_arbitrary_access(registry, name):
    with pytest.raises(DomainError, match="tool_not_allowed"):
        registry.execute("i1", call(name))


@pytest.mark.parametrize("arguments", [{"incident_id": "i2"}, {"url": "https://attacker.invalid"}, {"sql": "DROP TABLE incidents"}])
def test_extra_tool_arguments_rejected(registry, arguments):
    with pytest.raises(DomainError, match="invalid_tool_arguments"):
        registry.execute("i1", call("get_order", arguments))


def test_quotes_filtered_without_arbitrary_job_access(registry):
    result = registry.execute("i1", call("get_quotes", {"courier_ids": ["c2"]}))
    assert [record["id"] for record in result["records"]] == ["q2"]
    with pytest.raises(DomainError, match="invalid_tool_arguments"):
        registry.execute("i1", call("get_quotes", {"quote_id": "foreign"}))

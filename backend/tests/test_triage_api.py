from app.api.deps import get_llm_client
from tests.fakes import ScriptedLLM, ask_tools, final_answer


def triage_url(code: str) -> str:
    return f"/api/admin/complaints/{code}/triage"


def test_triage_without_an_llm_uses_the_rule_based_fallback(client, submit, admin_headers):
    code = submit(description="Deep pothole near the school gate where children cross").json()["complaint_id"]
    response = client.post(triage_url(code), headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert "No LLM provider" in body["fallback_reason"]
    assert body["category"] == "Road Damage"
    assert body["priority"] == "High"                       # medium, raised for children
    assert [s["tool_name"] for s in body["steps"]] == ["classify_text", "find_duplicates"]
    assert [s["step_number"] for s in body["steps"]] == [1, 2]


def test_triage_with_a_working_llm_records_the_agents_steps(client, submit, admin_headers):
    llm = ScriptedLLM([ask_tools("classify_text"), final_answer(category="Road Damage")])
    client.app.dependency_overrides[get_llm_client] = lambda: llm
    code = submit().json()["complaint_id"]
    body = client.post(triage_url(code), headers=admin_headers).json()
    assert body["source"] == "agent"
    assert body["fallback_reason"] is None
    assert [s["tool_name"] for s in body["steps"]] == ["classify_text"]
    assert body["steps"][0]["output"]["category"] == "Road Damage"


def test_latest_suggestion_can_be_fetched_and_the_newest_run_wins(client, submit, admin_headers):
    code = submit().json()["complaint_id"]
    assert client.get(triage_url(code), headers=admin_headers).status_code == 404

    client.post(triage_url(code), headers=admin_headers)
    llm = ScriptedLLM([final_answer(priority="Critical")])
    client.app.dependency_overrides[get_llm_client] = lambda: llm
    client.post(triage_url(code), headers=admin_headers)

    latest = client.get(triage_url(code), headers=admin_headers).json()
    assert latest["source"] == "agent"
    assert latest["priority"] == "Critical"


def test_similar_nearby_complaints_are_reported_as_possible_duplicates(client, submit, admin_headers):
    first = submit(description="Big pothole near the school gate").json()["complaint_id"]
    second = submit(description="Big pothole near the school gate").json()["complaint_id"]
    body = client.post(triage_url(second), headers=admin_headers).json()
    assert body["possible_duplicates"] == [first]


def test_triage_requires_an_administrator(client, submit):
    code = submit().json()["complaint_id"]
    assert client.post(triage_url(code)).status_code == 401
    assert client.get(triage_url(code)).status_code == 401


def test_triage_of_an_unknown_complaint_gives_404(client, admin_headers):
    assert client.post(triage_url("RW-2026-999999"), headers=admin_headers).status_code == 404

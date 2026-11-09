from app.cli.try_llm import check_connection, describe, run_agent
from tests.fakes import ScriptedLLM, ask_tools, final_answer
from app.ai.llm import LLMReply


def test_connection_check_returns_the_models_word(settings):
    assert check_connection(ScriptedLLM([LLMReply(content=" ready\n")])) == "ready"


def test_the_sample_triage_runs_and_describes_its_steps(settings):
    llm = ScriptedLLM([ask_tools("classify_text"), final_answer()])
    text = describe(run_agent(llm, settings, "Deep pothole near the school gate"))
    assert "Source: agent" in text
    assert "Step 1: classify_text" in text
    assert '"category": "Road Damage"' in text


def test_a_failing_model_is_shown_as_a_fallback_with_its_reason(settings):
    text = describe(run_agent(ScriptedLLM([LLMReply(content="not json")]), settings, "Pothole near school"))
    assert "Source: fallback (reason: invalid LLM output" in text

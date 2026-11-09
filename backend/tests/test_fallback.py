from app.ai.fallback import FallbackTriage
from app.ai.triage_tools import build_tools
from app.core.enums import ComplaintCategory, Priority
from tests.fakes import CONTEXT, FixedClassifier, FixedDuplicates
from app.ai.duplicates import DuplicateMatch


def triage(category, description, duplicates=0):
    matches = [DuplicateMatch(f"RW-2026-00000{i}", 10, 0.5) for i in range(2, 2 + duplicates)]
    tools = build_tools(CONTEXT, FixedClassifier(category), FixedDuplicates(matches))
    result, steps = FallbackTriage(tools, description).run()
    return result, steps


def test_base_priorities_follow_the_category():
    assert triage(ComplaintCategory.TRAFFIC_CONGESTION, "long jam")[0].priority == Priority.LOW
    assert triage(ComplaintCategory.ROAD_DAMAGE, "a pothole")[0].priority == Priority.MEDIUM
    assert triage(ComplaintCategory.RAILWAY_CROSSING, "gate broken")[0].priority == Priority.HIGH


def test_danger_words_raise_the_priority_one_level():
    result, _ = triage(ComplaintCategory.ROAD_DAMAGE, "a pothole where children cross")
    assert result.priority == Priority.HIGH
    assert "danger words" in result.rationale


def test_urdu_danger_words_are_recognised():
    assert triage(ComplaintCategory.ROAD_DAMAGE, "گڑھا اسکول کے سامنے ہے")[0].priority == Priority.HIGH


def test_many_similar_complaints_raise_the_priority_again_without_going_past_critical():
    result, _ = triage(ComplaintCategory.RAILWAY_CROSSING, "no gate, children cross", duplicates=3)
    assert result.priority == Priority.CRITICAL


def test_unit_and_duplicates_come_from_the_tools():
    result, steps = triage(ComplaintCategory.OTHER, "street lights off", duplicates=2)
    assert result.responsible_unit == "Municipal Services"
    assert result.possible_duplicates == ["RW-2026-000002", "RW-2026-000003"]
    assert [s.tool_name for s in steps] == ["classify_text", "find_duplicates"]

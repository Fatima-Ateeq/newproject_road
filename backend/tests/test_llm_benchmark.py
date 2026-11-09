from app.cli.llm_benchmark import DEV_SET, PacedLLM, format_table, run_benchmark
from app.ai.llm import LLMError, LLMReply
from tests.fakes import FakeClock, FixedClassifier, final_answer


class AlwaysAnswers:
    """A model that always answers 'Road Damage' for Roads Maintenance."""

    def generate(self, messages, tools):
        return final_answer()


class AlwaysFails:
    def generate(self, messages, tools):
        raise LLMError("the request to Gemini timed out")


def run(settings, models: dict):
    clock = FakeClock(step=1.0)
    return run_benchmark(
        list(models), lambda name: PacedLLM(models[name], min_interval=0, clock=clock, sleep=lambda s: None),
        FixedClassifier(), settings, agent_timeout=1000, clock=clock,
    )


class ManualClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class SlowModel:
    """Takes 2 seconds per request on the manual clock."""

    def __init__(self, clock: ManualClock) -> None:
        self._clock = clock

    def generate(self, messages, tools):
        self._clock.now += 2
        return final_answer()


def test_paced_client_waits_between_requests_and_counts_them():
    waits: list[float] = []
    clock = ManualClock()
    paced = PacedLLM(SlowModel(clock), min_interval=6, clock=clock, sleep=lambda s: (waits.append(s), setattr(clock, "now", clock.now + s)))
    paced.generate([], [])
    paced.generate([], [])
    assert waits == [4]                      # 6 seconds apart, and the first request already took 2
    assert paced.calls == 2


def test_model_time_does_not_include_our_own_pauses():
    clock = ManualClock()
    paced = PacedLLM(SlowModel(clock), min_interval=30, clock=clock, sleep=lambda s: setattr(clock, "now", clock.now + s))
    for _ in range(3):
        paced.generate([], [])
    assert paced.busy_seconds == 6           # 3 requests x 2 seconds, although 60 seconds passed in total
    assert clock.now > 60


def test_a_reliable_model_is_measured_and_a_failing_one_is_reported_with_its_reason(settings):
    good, bad = run(settings, {"good-model": AlwaysAnswers(), "bad-model": AlwaysFails()})
    assert (good.runs, good.agent_runs, good.http_calls) == (len(DEV_SET), len(DEV_SET), len(DEV_SET))
    assert good.correct == 2                       # it answers Road Damage, which two dev complaints expect
    assert bad.agent_runs == 0
    assert "LLM unavailable: the request to Gemini timed out" in bad.problems


def test_the_dev_set_includes_a_prompt_injection_that_must_not_change_the_routing(settings):
    injected = [c for c in DEV_SET if "IGNORE ALL PREVIOUS" in c.text]
    assert injected and injected[0].expected_unit == "Roads Maintenance"


def test_the_table_names_the_fastest_model_that_answered_everything_itself(settings):
    results = run(settings, {"good-model": AlwaysAnswers(), "bad-model": AlwaysFails()})
    table = format_table(results)
    assert "Fastest model that answered every complaint itself: good-model" in table
    assert "fell back" in table


def test_the_table_says_so_when_no_model_was_reliable(settings):
    table = format_table(run(settings, {"bad-model": AlwaysFails()}))
    assert "No model answered every complaint itself" in table

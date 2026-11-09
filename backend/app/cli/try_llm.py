"""Try the language model from the command line, without the database or the web server.

    python -m app.cli.try_llm --list-models        (which model names can my key use?)
    python -m app.cli.try_llm                      (connection check, then triage a sample complaint)
    python -m app.cli.try_llm --text "Deep pothole near the school gate"

The API key and model are read from backend/.env (GEMINI_API_KEY and GEMINI_MODEL).
"""

import argparse
import json
import sys
import time

from app.ai.agent import AgentRun, TriageAgent
from app.ai.context import ComplaintContext
from app.ai.duplicates import DuplicateMatch
from app.ai.fallback import FallbackTriage
from app.ai.gemini_client import GeminiClient
from app.ai.llm import LLMClient, LLMError, Message
from app.ai.triage_tools import build_tools
from app.api.deps import get_text_classifier
from app.cli.llm_benchmark import DEV_SET, PacedLLM, format_table, run_benchmark
from app.core.config import Settings, get_settings

SAMPLE = "Deep pothole near the school gate on Canal Road, children cross here every morning and two bikes slipped."


class _NoDuplicates:
    """There is no database in this check, so there is nothing to compare with."""

    def find(self, context: ComplaintContext) -> list[DuplicateMatch]:
        return []


def check_connection(client: LLMClient) -> str:
    """Ask the model for one word. Raises LLMError with a clear message if anything is wrong."""
    reply = client.generate([Message("user", "Reply with the single word: ready")], [])
    return reply.content.strip()


def run_agent(client: LLMClient, settings: Settings, text: str) -> AgentRun:
    context = ComplaintContext(0, "RW-TEST", text, 31.52, 74.35, False)
    tools = build_tools(context, get_text_classifier(settings), _NoDuplicates())
    agent = TriageAgent(
        client, tools, FallbackTriage(tools, text), settings.triage_max_tool_calls, settings.triage_timeout_seconds
    )
    return agent.run(text, has_photo=False)


def describe(run: AgentRun) -> str:
    lines = [f"Source: {run.source.value}" + (f" (reason: {run.fallback_reason})" if run.fallback_reason else "")]
    for step in run.steps:
        lines.append(f"Step {step.number}: {step.tool_name} -> {json.dumps(step.output, ensure_ascii=False)}")
    lines.append("Result: " + run.result.model_dump_json(indent=2))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Try the Gemini connection and the triage agent.")
    parser.add_argument("--list-models", action="store_true", help="List the model names this key can use")
    parser.add_argument("--text", default=SAMPLE, help="Complaint text to triage")
    parser.add_argument("--benchmark", nargs="+", metavar="MODEL",
                        help="Compare these models on a small dev set: speed, reliability, accuracy")
    parser.add_argument("--thinking-level", default=None, help="Override GEMINI_THINKING_LEVEL for this run (minimal, low, medium, high)")
    parser.add_argument("--pause", type=float, default=7.0, help="Seconds between requests in --benchmark (stays under about 8 per minute)")
    parser.add_argument("--agent-timeout", type=float, default=90, help="Time limit per complaint in --benchmark")
    args = parser.parse_args()

    settings = get_settings()
    if args.thinking_level:
        settings = settings.model_copy(update={"gemini_thinking_level": args.thinking_level})
    if not settings.gemini_api_key:
        print("GEMINI_API_KEY is not set in backend/.env")
        return 1
    key = settings.gemini_api_key.get_secret_value()

    try:
        if args.benchmark:
            def make_client(model: str) -> PacedLLM:
                inner = GeminiClient(key, model, settings.llm_timeout_seconds,
                                     thinking_level=settings.gemini_thinking_level or None)
                return PacedLLM(inner, args.pause)

            print(f"Benchmarking {len(args.benchmark)} model(s) on {len(DEV_SET)} complaints "
                  f"(thinking level: {settings.gemini_thinking_level or 'model default'}). This takes a few minutes.")
            print(format_table(run_benchmark(args.benchmark, make_client, get_text_classifier(settings),
                                             settings, args.agent_timeout)))
            return 0
        if args.list_models:
            print("\n".join(GeminiClient(key, "", settings.llm_timeout_seconds).list_models()))
            return 0
        if not settings.gemini_model:
            print("GEMINI_MODEL is not set in backend/.env. Run with --list-models and pick a name.")
            return 1
        client = GeminiClient(key, settings.gemini_model, settings.llm_timeout_seconds,
                              thinking_level=settings.gemini_thinking_level or None)
        started = time.perf_counter()
        print(f"Connection check ({settings.gemini_model}): {check_connection(client)!r} "
              f"in {time.perf_counter() - started:.1f} s")
    except LLMError as error:
        print(f"Could not use Gemini: {error}")
        return 1

    started = time.perf_counter()
    run = run_agent(client, settings, args.text)
    print(describe(run))
    print(f"\nWhole triage took {time.perf_counter() - started:.1f} s. Token usage of the last reply: {client.last_usage}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

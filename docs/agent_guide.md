# Triage agent guide

How the AI triage works, file by file, and how to extend it. Read this before the viewing or changing `backend/app/ai`.

## What it does

When an administrator calls `POST /api/admin/complaints/{id}/triage`, the system suggests a category, a priority, a
responsible unit, a short note and possible duplicates. The suggestion is saved with a full record of every tool call.
**The administrator decides.** Nothing in the agent changes a complaint's status or category.

## The path of one request

```
admin request -> route -> TriageService -> TriageAgent
                                             |-- asks the model (LLMClient) what to do next
                                             |-- runs the tool it chose (ToolRegistry) ... at most 5 times
                                             |-- model gives a final JSON answer -> checked against TriageResult
                                             '-- anything goes wrong -> FallbackTriage (rules)
              TriageService saves TriageSuggestion + one AgentLog row per tool call
```

## Files

| File (`backend/app/`) | One job |
|---|---|
| `ai/llm.py` | The contract every model provider must follow (`LLMClient`) and the message types. Also `UnavailableLLM`, used when no provider is configured |
| `ai/gemini_client.py`, `ai/gemini_format.py` | The Gemini adapter: HTTP, retries, error messages, and translation to and from Gemini's JSON |
| `cli/try_llm.py` | Command-line check of the Gemini connection and the agent, without the database |
| `ai/agent.py` | The loop: ask the model, run its tool, repeat, with limits. Falls back to rules on any failure |
| `ai/tools.py` | What a tool is, and the registry that runs them. Only registered tools can ever run |
| `ai/triage_tools.py` | The tools the agent can call: `classify_text` and `find_duplicates` |
| `ai/classifier.py` | The text classifier interface, plus the keyword baseline (the comparison and the safety net) |
| `ai/sklearn_classifier.py` | Loads the trained classifier file. Used when the file exists and loads, otherwise the keyword baseline is used |
| `ai/duplicates.py` | Finds unresolved complaints within 100 m with similar words |
| `ai/fallback.py` | Rule-based triage, used when the model fails |
| `ai/prompts.py` | The instructions sent to the model |
| `ai/schemas.py` | The shape of a valid answer (`TriageResult`) |
| `ai/steps.py` | One recorded tool call, and the helper that runs and times it |
| `ai/units.py` | Which unit handles which category (edit here to change routing) |
| `services/triage_service.py` | Builds the agent for a complaint, runs it, saves the result |
| `repositories/triage_repository.py` | Database access for suggestions |
| `models/triage.py` | The two tables: `triage_suggestions` and `agent_logs` |

## Safety rules built in

- **Limits:** at most 5 tool calls (`TRIAGE_MAX_TOOL_CALLS`), a 20 second limit (`TRIAGE_TIMEOUT_SECONDS`) checked between
  steps, and a hard cap on turns so a misbehaving model cannot loop forever.
- **Allow-list of tools:** an unknown tool name is refused and logged, never executed.
- **Read-only:** tools only read data. The agent cannot change statuses, delete anything or contact citizens.
- **Complaint text is data:** it is wrapped in markers, and the prompt tells the model to ignore instructions inside it.
- **Validated output:** the final answer must match `TriageResult`. Duplicate ids the model invents are dropped.
- **Fallback:** an unreachable model, a timeout or an invalid answer all lead to rule-based triage, and the reason is saved.
- **Tools take no arguments:** they read the complaint from the server, so the model cannot alter what they analyse.

## Today versus later

| Part | Today | Planned |
|---|---|---|
| Model provider | Gemini adapter built and tested against a pretend server. Switched on by two lines in `.env` | Confirm with a real call (`try_llm`), then tune the prompt |
| `classify_text` | Trained word and character n-gram TF-IDF + Logistic Regression (macro-F1 0.86 cross-validated on generated examples, versus 0.80 for the keyword baseline). Not yet measured on human-written complaints | Retrain with more data, then measure on the gold test set |
| `find_duplicates` | Distance plus word overlap | Better text similarity if needed |
| `detect_damage` | Not built | YOLO model on the complaint photo |
| `nearby_places` | Not built | Optional, if time allows |

## How to add a tool

1. Write a function inside `build_tools` in `ai/triage_tools.py` that returns a dict.
2. Add a `Tool(name, description, parameters, function)` to the list. The description is what the model reads.
3. Mention it in `ai/prompts.py` only if the model needs guidance on when to use it.
4. Add a test in `tests/test_agent.py` using the scripted model in `tests/fakes.py`.

## Using Gemini

`ai/gemini_client.py` talks to the Gemini REST API with `httpx`, and `ai/gemini_format.py` translates between our messages and
Gemini's JSON. The agent knows nothing about either.

| Detail | How it is handled |
|---|---|
| Switching it on | Set `GEMINI_API_KEY` and `GEMINI_MODEL` in `backend/.env`. With either missing, the system uses the rule-based fallback |
| Choosing a model | `python -m app.cli.try_llm --list-models` lists the names your key can use. Model names and free-tier availability change often, so there is no default |
| Checking it works | `python -m app.cli.try_llm` does a connection check, then runs the agent on a sample complaint and prints every step |
| The key | Sent in a header, never in the address. Hidden when settings are printed. Removed from any error text |
| Thinking level | `GEMINI_THINKING_LEVEL` (minimal, low, medium, high) limits how long a model reasons before answering. Newer models default to a lot, which can exceed the timeout. Unset means the model's default |
| Thought signatures | Newer Gemini models return a signature with each tool call and require it back on the next request. It travels in `ToolCall.extra`, untouched by the agent |
| Tools without arguments | Gemini rejects an empty object schema, so the adapter leaves `parameters` out for them |
| Rate limits and outages | HTTP 429 and 5xx are retried twice, waiting at most 5 seconds. Anything else, or a timeout (30 seconds by default), becomes a clear `LLMError`, and the agent falls back to rules |
| Time limit | The agent's 20 seconds are checked between steps. One slow Gemini call can take up to its own timeout. On the free tier, which allows only a few requests per minute, occasional fallbacks are normal. Raise `TRIAGE_TIMEOUT_SECONDS` if needed |
| Privacy | Content sent on the free tier can be used by Google to improve its products. Only the complaint text is sent, never contact details |

## Testing without a model

`tests/fakes.py` has `ScriptedLLM`, which replays prepared answers. This is how the agent's limits, fallback and safety
rules are tested without any API key or internet.

## Retraining the text classifier

```powershell
cd E:\work_folder\RoadWatch_AI
python -m ml.text.preprocess            # cleans and splits the training text
python -m ml.text.train_classifier      # measures, then saves backend/app/ai/artifacts/text_classifier.joblib
```

The script prints cross-validated and validation scores next to the keyword baseline, and saves a small card
(`text_classifier_card.json`) with the numbers and date. The saved model learns from every example. If the file cannot be
loaded (for example a different scikit-learn version), the backend logs a warning and uses the keyword baseline, so
nothing breaks. Retraining on your machine fixes it. Only load model files made by our own script: a pickle file can run
code when opened.

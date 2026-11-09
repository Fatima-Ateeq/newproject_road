# Decision log

Short record of what was decided and why. Add a line whenever something changes.

| Date | Decision | Why |
|---|---|---|
| 2026-10-26 | Backend uses FastAPI + SQLAlchemy 2 + PostgreSQL, migrations with Alembic | Matches the SRS stack; migrations make later schema changes cheap |
| 2026-10-26 | Layers: routes -> services -> repositories -> models | One job per layer (SRP). Routes handle HTTP, services hold rules, repositories hold queries |
| 2026-10-26 | Controlled values (status, category, priority) live in `app/core/enums.py` | Single place to edit if the professor changes the lists |
| 2026-10-26 | Complaint ID `RW-YYYY-NNNNNN` is derived from creation year + database id, not stored | No extra column, no way to get duplicates |
| 2026-10-26 | Action notes are public: citizens see them in the tracking timeline | Keeps one note field. Internal-only notes can be added later if needed |
| 2026-10-26 | Photos are validated by file signature (JPEG or PNG), not by file name | A renamed text file must not pass as an image |
| 2026-10-26 | One photo per complaint, stored on disk; the database keeps a relative path | Matches the SRS; simple to move or back up |
| 2026-10-26 | Frontend stays React (presentation matters) | Team decision |
| 2026-10-26 | LLM: hosted API with tool calling. Classifier and YOLO are the models we train | Training an LLM is out of scope for the timeline |
| 2026-10-27 | No registration or CNIC. A complaint is tracked by its ID; contact details are optional and admin-only | CNIC is sensitive and cannot be verified without an official integration; it also discourages reporting |
| 2026-10-27 | Submit endpoint has a per-IP rate limit (default 10 per hour) and a hidden honeypot field | Cheap protection against floods and simple bots (SRS FR-8) |
| 2026-10-27 | `duplicate_of_id` is not in the schema yet; duplicate detection arrives in Milestone 5 | Nothing uses it yet; adding it later is one migration |
| 2026-10-27 | Errors carry their own HTTP headers (`DomainError.headers`) | Removes the special case for 401 and lets 429 send `Retry-After` |
| 2026-10-28 | RDD2022 was downloaded as one 12.4 GB zip from Figshare and kept outside the repo (`E:\work_folder\datasets`) | Dataset Ninja's download tool fetched nothing; image data must never be committed to Git |
| 2026-10-28 | We build our own validation and test split from the labeled training images | The official RDD2022 test images have no public labels |
| 2026-10-28 | Data and model scripts live in `ml/`; the category list is read from the backend enum | One source of truth for categories |
| 2026-10-28 | The text test set is written and labeled by people (two labelers, agreement measured). Generated data is for training only | If an AI wrote or labeled the test set, evaluating our AI agent would look better than it really is |
| 2026-10-28 | Open 311 datasets are not used for complaint text | They mostly hold category fields and short descriptors, not citizen-written complaints |
| 2026-10-28 | Never `pip install` outside an activated environment | A global install replaced about 17 packages and needed a manual restore |
| 2026-10-28 | Image splits keep groups of 20 consecutive photos together | Neighbouring photos can be near-copies; separating them across train and test would inflate the results |
| 2026-10-29 | Training images are limited to about 10% background (no damage) images; validation and test keep their natural mix | The first conversion produced about 41% background images, which can make the detector too cautious. Evaluation must still show false alarms |
| 2026-10-29 | LLM: Gemini API (free tier) behind a provider-independent wrapper; Groq kept as a possible fallback | Better Urdu and Roman Urdu understanding and native function calling. Free limits and model names change, so the wrapper keeps switching cheap |
| 2026-10-29 | Code is hosted in a private GitHub repository, with feature branches and pull requests for code changes | Clean history and reviewable changes. See `docs/git_workflow.md` |
| 2026-10-29 | The text test pool is collected with a shared Excel sheet and merged by script. The scenario column is for coverage checks only and is never shown to labelers | Gets human-written complaints across all categories without leaking a label |
| 2026-10-29 | Training text: two generated batches (300 complaints, 60 per category). More batches only if validation results show it is needed | Enough to start. The real test is the human-written pool |
| 2026-11-02 | The agent reaches the language model only through the `LLMClient` contract. Until a provider is configured, `UnavailableLLM` makes every run use the rule-based fallback | The whole system works and is testable without an API key. A provider is one small adapter |
| 2026-11-02 | Tools take no arguments and read the complaint from the server | The model cannot alter the data a tool analyses, which removes a way to hallucinate or inject |
| 2026-11-02 | Duplicate finder uses distance (100 m) and word overlap, and does not require the same category. This departs from SRS FR-19 | Most complaints have no confirmed category yet. Word overlap is a simple baseline that can be improved later |
| 2026-11-02 | A keyword classifier is the first `classify_text` and the fallback classifier. The trained model replaces it, and the baseline stays as the comparison | A transparent baseline is something the trained model must beat. It scored 78% on our generated examples, which is optimistic because the same hand wrote both |
| 2026-11-02 | Agent limits: 5 tool calls, 20 seconds checked between steps, a hard turn cap, unknown tools refused, invented duplicate ids dropped | Keeps the agent bounded and auditable. Every tool call is stored in `agent_logs` |
| 2026-11-03 | Date filters in the administrator list mean whole days in the configured time zone (`TIMEZONE`, default `Asia/Karachi`), converted to UTC for the query | A complaint filed at 02:00 in Pakistan is stored as the previous day in UTC, and a UTC-day filter would hide it. Found when a test failed after midnight local time |
| 2026-11-03 | Text classifier: word and character n-gram TF-IDF with Logistic Regression, saved as a joblib file in `backend/app/ai/artifacts`. The backend uses the keyword baseline if the file is missing or unreadable | Character n-grams cope with Roman Urdu's unfixed spelling. Only scikit-learn parts are saved, so the file needs none of our code. The final model learns from all 300 generated examples |
| 2026-11-03 | The classifier's scores so far are on generated text (cross-validated macro-F1 0.86 versus 0.80 for the baseline) and are not the final result | The same hand wrote the examples, so they are optimistic. The human-written gold test set gives the real number |
| 2026-11-04 | The Gemini adapter uses the REST API through `httpx`, not the Google SDK | One small dependency, and the adapter can be tested against a pretend server with no key or internet |
| 2026-11-04 | Provider-specific data such as Gemini thought signatures travels in `ToolCall.extra`, which the agent passes along without reading | Newer Gemini models reject a tool conversation without the signatures. The agent stays provider-neutral |
| 2026-11-04 | `GEMINI_MODEL` has no default and must be chosen with `try_llm --list-models` | Model names and free-tier availability changed several times during 2026. A hard-coded name would break silently |
| 2026-11-04 | Gemini failures: retry 429 and 5xx twice (waits capped at 5 seconds), 10-second timeout, then fall back to rules with the reason saved | The agent has a time limit, and the system must keep working when the model does not answer |
| 2026-11-04 | Pin exact Gemini model names, not `-latest` aliases, for anything that is measured or demonstrated | An alias can move to a different model without notice, which would change speed, answers and limits mid-project |
| 2026-11-04 | Provisional model: a Flash-Lite model (`gemini-3.5-flash-lite`), chosen for the highest free limits among current models. To be confirmed with `try_llm --benchmark` | Flash models are limited to about 20 requests per day on the free tier, far too few for development and evaluation |
| 2026-11-04 | Optional `GEMINI_THINKING_LEVEL`, and the default Gemini timeout raised from 10 to 30 seconds | Models that think by default timed out at 10 seconds on the first real calls |
| 2026-11-04 | Model comparison uses a small dev set kept separate from the human-written test pool | Tuning on the test pool would make the final results look better than they are |
| 2026-11-05 | Tests use `IsolatedSettings` (ignores `.env` and environment variables) and refuse real HTTP calls | A real `GEMINI_API_KEY` in `backend/.env` made two tests call the real API and fail on one machine. Tests must behave the same everywhere and never spend quota |
| 2026-11-05 | The model benchmark times only the model's own waiting time, not our pauses between requests | The first version counted a 7-second pause per request and made the models look 3 times slower than they are |
| 2026-11-05 | YOLO: fine-tune a pretrained nano model at 640 px, batch 8, 40 epochs with early stopping. Choices are made on the validation split. The test split is scored once with `--evaluate-test` | Fits a 6 GB card, and keeps the final measurement honest |
| 2026-11-05 | The GPU training environment (`ml\.venv`) is separate from the backend environment, and model weights (`*.pt`) and `runs/` are not committed | PyTorch is several gigabytes. Final weights are added deliberately with `git add -f` once chosen |

## Known limitations

State these ourselves in the presentation. Each one has a planned or possible fix.

| Limitation | Why it is acceptable now | Possible improvement |
|---|---|---|
| Nothing verifies a complaint is true, and a determined person can still submit false ones | Every AI output is only a suggestion and an administrator approves all decisions, so a false complaint costs a reviewer seconds and triggers no action | CAPTCHA, contact verification with a one-time code, official identity integration |
| Rate-limit counts live in server memory | Fine for a single-process prototype | Shared store such as Redis |
| Behind a proxy, all users appear to share one IP address | The demo runs locally, with no proxy | Read the real client address from trusted proxy headers |
| Complaint IDs are sequential, so nearby IDs can be guessed | Tracking shows only status and timeline: no name, contact, location or description | Add a random suffix to the public ID |
| Duplicates are only suggested, using distance and word overlap | The administrator confirms. Word overlap misses duplicates described in different words | Better text similarity, a `duplicate_of_id` link |
| The honeypot only stops simple bots | It is a cheap first layer, not the only one | CAPTCHA |
| Action notes are public to the citizen | Keeps one note field | Add an internal-only note |
| Free-tier Gemini content may be used by Google to improve its products, and request limits are low | Only complaint text is sent, never contact details. Occasional fallbacks are expected | A paid tier, or a different provider through a new adapter |
| The free tier caps how many complaints can be triaged per day (about 500 requests a day for Flash-Lite models) | Enough for development and a 100-complaint evaluation spread over a day | A paid tier, or spreading evaluation runs over several days |

# Progress log

Keep this file current: add a dated line whenever something important is done or decided.
Last updated: 2026-11-05

## Milestone 4 at a glance (data and backend foundation)

| Deliverable | Status | Notes |
|---|---|---|
| Database/schema | Done | Four tables, Alembic migration `0001`, applied to PostgreSQL |
| Basic backend functionality | Done | Submit, track, admin login, list, detail, update, photo; 47 tests pass |
| Initial Git/project structure | Done | Private GitHub repository, pushed, tag `milestone-4` (2026-11-02) |
| Dataset: text | Mostly done | 300 generated training examples (2 batches). Collection sheet and merge tool ready. Test pool still to be collected and labeled by people |
| Dataset: images (RDD2022) | Done | India and Japan converted to YOLO format (train 2,101 / val 404 / test 404), all four classes in every split, background images in train limited to 10%. Stored at `E:\work_folder\datasets\rdd2022_yolo` (0.2 GB) |
| Preprocessing | Done | Text cleaning and splitting, and image conversion with our own split |

## Milestone 5 at a glance (LLM and agent integration)

| Part | Status |
|---|---|
| Agent loop with limits, fallback and logging | Built and tested with a scripted model |
| Tools: `classify_text` (trained model, keyword baseline as safety net), `find_duplicates` | Built |
| Database: `triage_suggestions`, `agent_logs` (migration 0002) | Done |
| API: run and fetch triage (admin) | Done |
| Gemini adapter | **Verified on the real API.** `gemini-3.5-flash-lite` with low thinking answered all 6 dev complaints itself and correctly, including a prompt-injection test. A whole triage took about 13 s. Final model to be pinned after the corrected benchmark |
| GPU environment for YOLO | Verified: PyTorch 2.15 with CUDA runs real calculations on the GTX 1660 Ti, Ultralytics 8.4.202 installed. Training script written and tested; first run pending |
| Trained text classifier | Built: macro-F1 0.86 cross-validated on generated examples (keyword baseline 0.80). Real measurement waits for the human-written test set |
| YOLO damage detector and `detect_damage` tool | Not started (needs the `nvidia-smi` output) |
| Initial agent testing with the real model | After the Gemini adapter |

## What exists in the project

- `backend/`: FastAPI + SQLAlchemy + PostgreSQL API. Layers: routes, services, repositories, models. Includes the triage agent in `app/ai`. 126 backend tests, 67 `ml` tests.
- `ml/text/`: labeling tool, agreement check, gold test set builder, cleaning and splitting.
- `ml/images/`: RDD2022 to YOLO converter with our own train, validation and test split. 12 tests.
- `ml/data/text/generated_seed.csv` and `generated_seed_2.csv`: 300 generated complaints (English, Roman Urdu, Urdu), training use only.
- `docs/`: `setup.md`, `git_workflow.md`, `decisions.md`, `agent_guide.md` (how the triage agent works), this file.

## Environment

- Windows 11, VS Code, Windows PowerShell. Python 3.13. PostgreSQL 18.6 (database `roadwatch`, UTF8).
- Project: `E:\work_folder\RoadWatch_AI`. Datasets, kept outside Git: `E:\work_folder\datasets`.
- Backend virtual environment: `backend\.venv`. Always activate it before running anything.

## Timeline

| Date | What happened |
|---|---|
| 2026-10-26 | Backend foundation built and tested. PostgreSQL 18 installed, database created, migration applied, admin created, all endpoints tried in the browser |
| 2026-10-27 | Anti-spam added: rate limit (10 per hour per IP) and honeypot field. Decisions and known limitations documented |
| 2026-10-28 | Dataset Ninja tool failed and changed global Python packages by mistake. Global Python restored to its previous versions. RDD2022 obtained from Figshare as a 12.4 GB zip. `ml` package added: text labeling tools and seed data |
| 2026-10-29 | LLM provider chosen: Gemini (Groq as fallback). Second batch of 150 training complaints, collection sheet and merge tool added. Converter run on India and Japan succeeded, then rerun with the background limit. Inner dataset zip extracted. `pytest ml` passes (36). Image converter built. First run reported no countries found, because the release holds one zip per country (`India.zip`, `Japan.zip`, ...). Converter updated to read them |

## Open issues

0. **Gemini:** run `python -m app.cli.try_llm --list-models`, set `GEMINI_MODEL`, then `python -m app.cli.try_llm` and report the result.
1. **Test pool:** about 100 complaints still to be written (collection sheet) and labeled by two team members.
3. **GPU check:** run `nvidia-smi` to choose the right PyTorch build for local YOLO training (GTX 1660 Ti, 6 GB).

## Next: Milestone 5 (AI integration)

LLM integration (Gemini), prompt design, agent workflow with tool calling, text classifier, YOLO fine-tuning,
duplicate finder, fallback and logging.

## Handy commands

```powershell
cd E:\work_folder\RoadWatch_AI\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload        # start the API, then open http://127.0.0.1:8000/docs
pytest                               # backend tests (from backend)
cd ..; pytest ml                     # ml tests (from the project root)
```

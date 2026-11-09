# Setup guide (Windows 11, PowerShell)

Records the exact steps that worked on the first machine. Tested with Python 3.13 and PostgreSQL 18.6.
Update this file whenever a setup step or the project structure changes.

## 1. Prerequisites

- Python 3.11 or newer (`python --version`)
- Git
- VS Code (optional but recommended)

## 2. Backend environment

Run from the project's `backend` folder:

```powershell
cd E:\work_folder\RoadWatch_AI\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

`(.venv)` must appear at the start of the prompt. Packages install into `.venv` only, so they never
touch other Python projects. Run the `Activate.ps1` line again in every new terminal.

## 3. PostgreSQL

1. Download the Windows installer from https://www.postgresql.org/download/windows/ (latest stable).
2. Keep these components: PostgreSQL Server, pgAdmin 4, Command Line Tools. Keep port 5432.
3. Choose a simple password for the `postgres` user (letters and numbers only) and remember it.
4. Check the service from a new PowerShell:

```powershell
Get-Service postgresql*
```

Expected: Status `Running`.

5. Check `psql`:

```powershell
psql --version
```

If PowerShell says `psql` is not recognized, add PostgreSQL to the PATH (see Troubleshooting), then
open a new PowerShell.

6. Create the database (asks for the password):

```powershell
psql -U postgres -c "CREATE DATABASE roadwatch;"
psql -U postgres -l
```

Expected: `CREATE DATABASE`, and `roadwatch` listed with encoding `UTF8` (needed for Urdu text).

## 4. Configure `.env`

Generate a secret key and copy the output:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Edit `backend\.env` so it contains (one `DATABASE_URL` line only, no spaces around `=`):

```
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/roadwatch
SECRET_KEY=paste_the_generated_key_here
```

`.env` is private and ignored by Git. Each teammate makes their own.

## 5. Create the tables and run the tests

```powershell
alembic upgrade head
pytest
```

Expected: `Running upgrade -> 0001, create initial tables`, then `39 passed`.
One warning about `httpx` and `starlette.testclient` being deprecated is harmless.

## 6. Create an administrator and start the server

```powershell
python -m app.cli.create_admin
uvicorn app.main:app --reload
```

- API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

In the docs page, use `POST /api/admin/login`, copy the `access_token`, click **Authorize**, and paste it
to try the administrator endpoints.

## Troubleshooting

| Problem | Fix |
|---|---|
| `psql` is not recognized | Find the folder: `Get-CimInstance Win32_Service -Filter "Name='postgresql-x64-18'" \| Select-Object PathName`. Add its `bin` folder to the PATH: `$pgBin = "C:\Program Files\PostgreSQL\18\bin"` then `[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";$pgBin", "User")`. Open a new PowerShell. |
| `Activate.ps1` is blocked | Run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `password authentication failed` | The password is wrong. Nothing shows while typing. In `.env`, the password must match the `postgres` password. |
| Password contains `@ : / # %` | Pick a simpler password, or URL-encode the characters in `DATABASE_URL`. |
| `SECRET_KEY` validation error | The key must be at least 32 characters. Generate one with the command in section 4. |
| `could not connect to server` | Check the service is running (`Get-Service postgresql*`) and the port in `DATABASE_URL` is 5432. |
| `No module named ...` | The virtual environment is not active. Run `Activate.ps1`, then `pip install -r requirements-dev.txt`. |

## Working rules

- **Never `pip install` outside an activated environment.** Check that `(something)` appears at the start of the
  prompt first. A global install can silently replace packages used by other projects.
- **Keep datasets outside the repository,** for example in `E:\work_folder\datasets`. Image data is large and
  must never be committed to Git.
- Run the text tools from the project root, for example `python -m ml.text.label_tool ...`. See `ml/README.md`.
- Run the ml tests from the project root with the backend environment active: `pytest ml`.
- Convert the road-damage dataset with `python -m ml.images.prepare_rdd2022` (see `ml/README.md`). It reads the
  per-country zips directly, so the dataset never needs to be fully extracted.

## Where to run each command

| Command | Run it from |
|---|---|
| `alembic ...`, `pytest` (backend tests), `uvicorn app.main:app --reload`, `python -m app.cli.create_admin` | `E:\work_folder\RoadWatch_AI\backend` |
| `pytest ml`, `python -m ml.text...`, `python -m ml.images...`, all `git` commands | `E:\work_folder\RoadWatch_AI` (the project root) |

`alembic` reads `alembic.ini`, which lives in `backend`. Running it from the project root fails with
`No 'script_location' key found in configuration`.

## Gemini (the language model)

1. Create an API key at https://aistudio.google.com/apikey. Keep it private: it goes only in `backend\.env`, never in chat, code or Git.
2. In `backend\.env` add `GEMINI_API_KEY=your_key`.
3. List the models your key can use, and pick a Flash or Flash-Lite one that AI Studio marks as free:
   ```powershell
   cd E:\work_folder\RoadWatch_AI\backend
   python -m app.cli.try_llm --list-models
   ```
4. Add `GEMINI_MODEL=the_name_you_picked` to `backend\.env`.
5. Check it: `python -m app.cli.try_llm`. It prints a connection check, then the agent's steps and result.
6. Restart the server. `POST .../triage` now shows `source: agent` when Gemini answers, and `source: fallback` with a reason when it does not.

### Choosing the model

- **Pin an exact name.** Names ending in `-latest` are aliases that can move to a different model, changing speed, answers
  and limits without notice. Use them for quick experiments only. The final evaluation must use a pinned name.
- **Free limits decide.** Google no longer prints a per-model table. The real numbers are in the rate-limit view of
  Google AI Studio for your project. One third-party tracker (October 2026) reported: Flash models (3.8, 3.6) 5 requests per
  minute and 20 per day; Flash-Lite models (3.5, 3.1) 10 per minute and 500 per day. One triage uses about 2 to 4 requests,
  so 20 per day is only 5 to 10 complaints, while 500 per day is 125 or more.
- **Thinking costs time.** Newer models reason a lot by default, which makes them slow. Triage is a short task, so set
  `GEMINI_THINKING_LEVEL=low` (or `minimal`) and compare.
- **Measure, do not guess.** This compares models on six dev complaints (including a prompt-injection attempt) and prints
  speed, reliability and accuracy. It paces requests to stay inside the free limit and uses about 20 requests per model:
  ```powershell
  python -m app.cli.try_llm --benchmark gemini-3.5-flash-lite gemini-3.1-flash-lite
  ```
- Suggested starting lines for `backend\.env`: `GEMINI_MODEL=gemini-3.5-flash-lite`, `GEMINI_THINKING_LEVEL=low`,
  `LLM_TIMEOUT_SECONDS=30`, `TRIAGE_TIMEOUT_SECONDS=60`.

If you see HTTP 404, the model name is wrong or retired: run `--list-models` again. HTTP 429 means the free-tier limit was reached: wait a minute.

## GPU training environment (for YOLO)

Kept separate from the backend environment, because PyTorch is several gigabytes. Tested on Windows, Python 3.13 and a
GTX 1660 Ti with 6 GB.

1. Free the graphics memory. Close games and their launchers, Discord, browsers and overlays, then check:
   ```powershell
   nvidia-smi --query-gpu=memory.used,memory.total --format=csv
   ```
   Under about 1 GB used is good. Ours dropped from 3.7 GB to 0.9 GB after closing apps.
2. Create the environment:
   ```powershell
   cd E:\work_folder\RoadWatch_AI\ml
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install PyTorch with CUDA. Get the command from https://pytorch.org/get-started/locally (Stable, Windows, Pip, CUDA).
   What worked for us (about 2 GB):
   ```powershell
   pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu132
   ```
4. Install the rest: `pip install -r requirements-train.txt`
5. Verify the card really computes (not just that it is detected):
   ```powershell
   python -c "import torch; x = torch.randn(2000, 2000, device='cuda'); print((x @ x).sum().item()); print(torch.cuda.mem_get_info())"
   python -c "import ultralytics; ultralytics.checks()"
   ```
   You want a number, then the free and total memory, then a line naming your card.
6. Optional: Ultralytics can send anonymous usage statistics. To turn that off: `yolo settings sync=False`

Run `pytest` and the backend only from the backend environment. The prompt looks the same for both, so check with
`python -c "import sys; print(sys.prefix)"`.

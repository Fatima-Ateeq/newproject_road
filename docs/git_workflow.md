# Git and GitHub workflow

How we keep the code in GitHub, and how every teammate works with it.

## First-time setup (once per computer)

1. Check Git is installed: `git --version`. If not, install it from https://git-scm.com/download/win and keep the defaults.
2. Tell Git who you are (this appears on every commit). Use the email of your GitHub account:

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## Creating the repository (once, by one person)

1. On GitHub, click **New repository** (https://github.com/new).
2. Name: `RoadWatch_AI`. Choose **Private**.
3. **Do not** tick "Add a README", ".gitignore" or "license". The project already has its own, and ticking them creates a conflict on the first push.
4. Click **Create repository**, and keep the page open. It shows the repository address.

## First commit and push (from the project folder)

```powershell
cd E:\work_folder\RoadWatch_AI
git init -b main
git add .
git status
```

Read the `git status` list before committing. It must **not** contain `.env`, `.venv`, `uploads`, `__pycache__`, any `.zip` file,
or any dataset. If it does, stop and ask. Then:

```powershell
git commit -m "Milestone 4: backend foundation, ml data tools, docs"
git remote add origin https://github.com/YOUR_USERNAME/RoadWatch_AI.git
git push -u origin main
```

A browser window asks you to sign in to GitHub the first time. Approve it, and the push continues.

Check the result:
- Refresh the GitHub page. You should see `backend`, `ml`, `docs`, `README.md`.
- In PowerShell, this should print nothing: `git ls-files | Select-String "\.env$|\.venv"`
- Mark the milestone: `git tag milestone-4` then `git push origin milestone-4`

## Adding teammates

1. GitHub, repository, **Settings**, **Collaborators**, **Add people**.
2. Each teammate runs `git clone https://github.com/YOUR_USERNAME/RoadWatch_AI.git`, then follows `docs/setup.md`
   (their own virtual environment, their own `.env`).

## Daily workflow

```powershell
git switch main
git pull                                  # get the latest work first
git switch -c feature/short-description   # one branch per piece of work
# ... work, run the tests ...
git add .
git status                                # check what is included
git commit -m "feat: short summary"
git push -u origin feature/short-description
```

Then open a **Pull Request** on GitHub. A teammate reads it and merges it into `main`. After the merge:
`git switch main` and `git pull`.

Small documentation fixes may go straight to `main`.

## Commit messages

`type: short summary in the present tense`. Types: `feat` (new behaviour), `fix`, `docs`, `test`, `refactor`, `chore`.
Examples: `feat: add duplicate finder tool`, `fix: reject photos over the size limit`, `docs: update setup guide`.
Make small commits that each do one thing, so the history is easy to follow and explain.

## What never goes into Git

- `.env` (passwords and keys) and any API key. If a secret is ever committed, treat it as leaked and replace it.
- `.venv`, `uploads`, `__pycache__`, `*.db`.
- Datasets, for example `E:\work_folder\datasets`. They are large and live outside the project folder.
- Update zips. Extract them, then delete the zip.

## Common problems

| Message | Meaning and fix |
|---|---|
| `Author identity unknown` | Run the two `git config --global` commands above |
| `LF will be replaced by CRLF` | A normal Windows line-ending notice. Ignore it |
| `fatal: not a git repository` | You are in the wrong folder. `cd` to the project folder |
| `rejected ... fetch first` on push | The remote has commits you do not have. Run `git pull --rebase origin main`, then push again |
| `remote origin already exists` | Fix the address with `git remote set-url origin https://github.com/YOUR_USERNAME/RoadWatch_AI.git` |

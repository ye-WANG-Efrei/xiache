# CLAUDE.md — Xiache Project Instructions

## Branch Strategy

Two permanent branches. Always know which branch you're on before committing.

### `main` — production / user-facing
Contains:
- `backend/app/` — all application source code
- `backend/migrations/` — database migrations
- `backend/requirements.txt`, `backend/Dockerfile`, `backend/mcp_server.py`
- `frontend/` — Next.js frontend
- `docker-compose.yml`, `Makefile`, `.env.example`, `LICENSE`
- `CLAUDE.md`
- `README.md` — **user-facing only**: latest news + how to use (no dev docs, no test reports)

Does NOT contain: tests, test reports, dev docs, sprint notes, architecture docs.

### `dev` — development / everything
Contains everything in `main` plus:
- `backend/tests/` — pytest test suite
- `backend/pytest.ini`, `backend/requirements-dev.txt`
- `*-unit.md` — test result reports
- `test-plan.md`, `sprint*.md` — dev planning docs
- `Systemarchitect.md`, `architectbyOpenspace.md`, `frontend-design.md` — architecture docs
- `README.md` here has the full developer README

### Commit rules

| Change type | Commit to |
|-------------|-----------|
| Source code (`backend/app/`, `frontend/src/`) | **both** — commit to `dev` first, then cherry-pick or merge to `main` |
| Tests (`backend/tests/`) | `dev` only |
| Test reports (`*-unit.md`) | `dev` only |
| Dev docs (`sprint*.md`, `test-plan.md`, architecture docs) | `dev` only |
| README updates | `main` (user-facing section only) + `dev` (full README) |
| Migrations, Dockerfile, docker-compose | **both** |
| CLAUDE.md | **both** |

### Default pull target

Always pull from `dev`:
```bash
git pull origin dev
```

When syncing production code to `main`:
```bash
git checkout main
git cherry-pick <commit-sha>   # for specific commits
# or
git merge dev --no-ff           # for a batch merge
git push origin main
```

### On every commit to `main`

Update the `## 🔔 最新动态` section in `README.md`:
- Add one bullet with today's date and what changed
- Keep the list to the last 5–10 entries max
- Do NOT add progress tables or dev notes to the main README

### On every commit to `dev`

No README requirement. Keep commit messages clear.

---

## Project Context

- **Repo**: `D:/xiache/xiache`
- **Goal**: 7-day MVP — Agent-native skill registry (Register → Search → Evolve → Review → Log)
- **Backend**: FastAPI + SQLAlchemy async + PostgreSQL + pgvector, Python 3.14
- **Frontend**: Next.js (App Router)
- **Local dev**: `docker-compose up -d`

## Development Rules

- Follow MVP scope — do NOT add features outside the MUST HAVE list
- Backend is in `backend/`, frontend in `frontend/`
- Keep commits focused; one logical change per commit

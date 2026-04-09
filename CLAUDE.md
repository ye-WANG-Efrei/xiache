# CLAUDE.md — Xiache Project Instructions

## On Every GitHub Commit

Before committing, update `README.md` to reflect current feature progress:

1. Find or create a `## Development Progress` section near the top of README.md (after the one-liner definition).
2. Update the checklist under each milestone day to reflect what is actually done (`- [x]`) vs pending (`- [ ]`).
3. Add a brief "Last updated" note with the date and what changed, e.g.:
   ```
   > Last updated: 2026-04-09 — Day 1 backend setup complete, /health endpoint live
   ```
4. Do not rewrite unrelated sections. Only touch the progress section.

## Project Context

- **Repo**: `D:/xiache/xiache`
- **Goal**: 7-day MVP — Agent-native skill registry (Register → Search → Evolve → Review → Log)
- **Milestone plan**: see `D:/xiache/milestone.md`
- **Architecture**: see `Systemarchitect.md`, `architectbyOpenspace.md`

## Development Rules

- Follow the MVP scope in `milestone.md` — do NOT add features outside the MUST HAVE list
- Backend is in `backend/`, frontend in `frontend/`
- Use `docker-compose.yml` for local dev environment
- Keep commits focused; one logical change per commit

## README Progress Section Format

```markdown
## Development Progress

### MVP Status (7-Day Plan)

| Day | Goal | Status |
|-----|------|--------|
| Day 1 | Backend Setup | ✅ Done |
| Day 2 | Skill Registration | 🔄 In Progress |
| Day 3 | Skill Search | ⬜ Pending |
| Day 4 | Evolution Submission | ⬜ Pending |
| Day 5 | Evolution Review | ⬜ Pending |
| Day 6 | Execution Run Logging | ⬜ Pending |
| Day 7 | Integration & Demo | ⬜ Pending |

> Last updated: YYYY-MM-DD — [what changed]
```

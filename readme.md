# Macad GH Test.md

This file provides guidance to the macad GH test  (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack MCQ quiz app — Flask REST API + Vue 3 SPA. No database; all state is stored in JSON files.

---

## Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
python app.py          # starts on http://localhost:5000
```

### Frontend
```bash
cd frontend
npm install
npm run dev            # starts on http://localhost:5173
npm run build          # production build → dist/
```

Vite proxies all `/api/*` requests to `http://localhost:5000`, so the frontend never hard-codes the API origin.

---

## Architecture

### Backend (`backend/`)

Single-file Flask app (`app.py`). No blueprints, no ORM.

**Auth:** JWT signed with `SECRET_KEY` (env var `JWT_SECRET`, defaults to a dev value). Two decorator factories gate routes:
- `@require_auth` — verifies JWT, sets `request.current_user`
- `@require_admin` — same + checks `is_admin` claim

**Persistence:** Two JSON files read/written on every request via `read_json` / `write_json` helpers:
- `data/users.json` — array of user objects (`id`, `username`, `password_hash`, `is_admin`, `results[]`)
- `data/questions.json` — array of question objects (`id`, `question`, `options[]`, `answer` index, `time_limit`)

First registered user is automatically `is_admin: true`.

`GET /api/quiz` strips the `answer` field before returning questions. `POST /api/quiz/submit` receives `{answers: {str(id): optionIndex|null}, time_taken}`, scores server-side, and appends to the user's `results[]`.

### Frontend (`frontend/src/`)

| File | Role |
|------|------|
| `stores/auth.js` | Pinia store — holds `token` + `user`, persists to `localStorage`, sets `axios.defaults.headers.common['Authorization']` on login |
| `router/index.js` | Route guards: `meta.guest` redirects logged-in users to `/quiz`; `meta.auth` redirects guests to `/login`; `meta.admin` redirects non-admins to `/quiz` |
| `views/QuizView.vue` | Fetches questions, runs per-question SVG countdown timer, auto-advances on timeout, POSTs answers on finish, stores result in `sessionStorage` |
| `views/ResultView.vue` | Reads result from `sessionStorage` (set by QuizView before navigating) |
| `views/AdminView.vue` | Slide-in panel for add/edit; inline confirm for delete; all via `/api/admin/*` |

**Tailwind v4** — configured via `@tailwindcss/vite` plugin; no `tailwind.config.js`. Import is `@import "tailwindcss"` in `src/style.css`.

### Data flow for quiz submission
1. `QuizView` accumulates `answers` as `{ [questionId]: optionIndex }` (unanswered → `null`)
2. POSTs to `/api/quiz/submit`
3. Stores full response in `sessionStorage.quizResult`
4. Navigates to `/result`
5. `ResultView` reads `sessionStorage.quizResult` on mount

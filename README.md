# CareerMAP — Deploy-Ready Build

Find who you are → explore the worlds of work → pick your paths → build your roadmap.

## ⚠️ Do these two things FIRST

1. **Rotate your secrets.** The `.env` you had before should be considered exposed. Get a **new Gemini API key** (delete the old one in Google AI Studio) and generate a **new SECRET_KEY**:
   `python -c "import secrets; print(secrets.token_hex(32))"`
2. **Never commit `.env`.** A `.gitignore` is included that excludes it. Use `backend/.env.example` as your template.

---

## What changed in this build (vs. your original)

**Bugs fixed (these would have crashed in production):**
- `requirements.txt` was missing `python-dotenv` and `gunicorn` → instant crash on deploy. Fixed.
- `summaries` table was missing `report_cached_json`, `calibration_feedback_score`, `prediction_ratings`, and `id` columns that the report code reads/writes. Fixed in `database.py` (with safe `ALTER ... IF NOT EXISTS` for existing databases).
- `canvas_steps` table was used by the API but never created. Created.
- The report queried `users.occupation`, which was never created. Created.
- Admin endpoints always returned 403 because the JWT had no email. The token now carries the email (with a DB fallback for old tokens) → `admin.html` works.
- `quiz_routes.py` had the admin block pasted twice at the bottom. Removed.
- Two conflicting auth modules (`auth.py` + `routes/auth_routes.py`). Consolidated into one; all routes import from it.
- `index.html` checked the **unprefixed** `intro_done` key while `intro.html` saved the **prefixed** one → returning users were sent to the intro again. Fixed.
- Hardcoded `127.0.0.1` URLs in `index.html`, `quiz.html`, `blueprint.html`. Everything now reads from `config.js`.

**New capabilities:**
- **Cross-device progress.** New `/api/user/state` endpoints + upgraded `userstore.js`: the user's journey (intro profile, selections, canvas queue, points) now syncs to the database automatically and is pulled down at login. Same `userStore` API, zero changes needed in page code.
- `/api/health` endpoint + frontend "waking up the server" message for free-tier cold starts.
- CORS lockable via `FRONTEND_ORIGIN` env var.
- `setup_db.py` — one command to create schema + seed questions + seed worlds.

**Product/safety changes:**
- The AI report prompt is rewritten: same incisive structure (archetype, gift/trap/misread/unlock, predictions), but written *to* the person, explicitly non-clinical, never cruel, and gentler when the user is under 18 or age is unknown. Output JSON shape is unchanged, so `analysis.html` works as-is.
- A visible disclaimer ("AI-generated reflection, not a clinical assessment") added to `analysis.html` and the login page.
- Unified branding: every page is now **CareerMAP** (the PersonaIQ/CareerMAP split is gone).
- New artistic entry page (`index.html`): animated topographic contour "map" signature, Fraunces + Outfit, warm paper + gold — matching your intro/profile identity.

**Removed dead files:** `auth.py` (root), `questions_data.py` (stale unfaceted question bank), `patch_db.py` (folded into `database.py`), `js/auth.js`, `js/quiz.js` (referenced element IDs that don't exist).

---

## Run locally

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then fill in your values
python setup_db.py          # creates schema + seeds questions + worlds (once)
python main.py              # http://127.0.0.1:5000

# Frontend (separate terminal)
cd frontend
python -m http.server 8000  # http://localhost:8000
```
`config.js` auto-detects localhost, so no changes needed for local dev.

---

## Deploy (free tier)

### 1. Database — Neon (recommended) or Supabase
- Create a free Postgres at https://neon.tech → copy the connection string (`postgresql://...`).
- (Render's own Postgres also works but the free one expires after 90 days; Neon doesn't.)

### 2. Backend — Render
1. Push this repo to GitHub.
2. Render → New → Web Service → pick the repo, **root directory: `backend`**.
3. Build command: `pip install -r requirements.txt`
   Start command: `gunicorn main:app`
4. Environment variables:
   - `DATABASE_URL` = your Neon string
   - `SECRET_KEY` = new random string
   - `GEMINI_API_KEY` = your **new** key
   - `ADMIN_EMAILS` = your login email (for admin.html)
   - `FRONTEND_ORIGIN` = your frontend URL (add after step 3, then redeploy)
5. Seed the production DB **once** — easiest way: on your own machine, set `DATABASE_URL` in `backend/.env` to the Neon string and run `python setup_db.py`. Then remove it from your local `.env`.

### 3. Frontend — Netlify (or Vercel / Cloudflare Pages)
1. Edit **one line** in `frontend/config.js`:
   `const PROD_BACKEND = "https://YOUR-SERVICE.onrender.com/api";`
2. Drag the `frontend/` folder into https://app.netlify.com/drop (or connect the repo with publish directory `frontend`).
3. Copy the Netlify URL into the backend's `FRONTEND_ORIGIN` env var.

### 4. Smoke test
Register → intro → quiz (75 Q + 2 writing prompts) → blueprint (4 questions) → analysis → worlds → gather → canvas. Then log in from a **different browser** and confirm your journey is still there (that's the new state sync working).

---

## Known limitations (be aware, not blockers)

- **Free Render sleeps** after ~15 min idle; first request takes ~30 s. The login page warns the user and pre-pings `/api/health`.
- **Admin content editor**: `admin.html` saves `industries.json` to the *backend's* filesystem, which is wiped on redeploy — and the live pages load the *frontend's* static copy anyway. For now treat `frontend/industries.json` as the source of truth: edit it locally (the admin page works great locally) and redeploy the frontend. Moving industries content into Postgres is the proper long-term fix.
- No email verification / password reset yet — fine for a beta, add before scaling.
- Gemini free tier has rate limits; if many users finish the quiz at once, some will see the "try again" message.

## Suggested next steps after launch
1. Move industries content into the database (kills the admin limitation).
2. Password reset via email (e.g. Resend free tier).
3. Unify the remaining inner pages onto the CareerMAP visual identity (the entry page sets the direction).

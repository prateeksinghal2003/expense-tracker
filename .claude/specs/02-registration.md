# Spec: Registration

## Overview
Implement the `POST /register` route to wire up the existing registration form to the database. When a user submits the form, the route validates input, checks for duplicate emails, hashes the password, inserts the new user into the `users` table, starts a Flask session, and redirects to the dashboard (or landing page until Step 4). The `GET /register` route and the `register.html` template already exist — this step is purely backend plumbing.

## Depends on
- Step 01 — Database setup (`get_db`, `init_db`, `users` table must exist)

## Routes
- `POST /register` — handle registration form submission — public

## Database changes
No database changes. The `users` table already has the required schema:
- `id`, `name`, `email` (UNIQUE), `password_hash`, `created_at`

## Templates
- **Create:** none
- **Modify:** `templates/register.html` — already renders `{{ error }}` block; no changes needed unless error display requires tweaking

## Files to change
- `app.py` — add `POST /register` route; import `session`, `redirect`, `url_for`, `request` from Flask; import `generate_password_hash` from werkzeug

## Files to create
None

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never f-strings in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Set `app.secret_key` (required for `session` to work) — use a hard-coded dev string for now, e.g. `"spendly-dev-secret"`
- After successful registration, store `session['user_id']` and `session['user_name']`
- On duplicate email, re-render `register.html` with `error="An account with that email already exists."`
- On missing/short fields, re-render with a descriptive `error` message
- Minimum password length: 8 characters — validate server-side
- Use `abort()` for unexpected server errors, not bare string returns

## Definition of done
- [ ] Submitting the form with valid data inserts a new row in the `users` table
- [ ] The inserted password is stored as a hash, not plaintext
- [ ] Duplicate email submission re-renders the form with an error message (no crash)
- [ ] Password shorter than 8 characters re-renders the form with an error message
- [ ] Empty name or email re-renders the form with an error message
- [ ] Successful registration sets `session['user_id']` (verifiable via Flask debug or a quick `print`)
- [ ] Successful registration redirects away from `/register` (no 200 with form still showing)
- [ ] App starts without errors after changes

# Spec: Login and Logout

## Overview
Implement `POST /login` to authenticate an existing user and `GET /logout` to end their session. The `GET /login` route and `login.html` template already exist — this step wires the login form to the database: look up the user by email, verify the password hash with `check_password_hash`, set the Flask session on success, and redirect. Logout simply clears the session and redirects to the landing page. This completes the full auth lifecycle begun in Step 02.

## Depends on
- Step 01 — Database setup (`get_db`, `users` table with `email` and `password_hash` columns)
- Step 02 — Registration (establishes `session['user_id']` and `session['user_name']` as the session convention)

## Routes
- `POST /login` — handle login form submission, verify credentials, start session — public
- `GET /logout` — clear session, redirect to landing — accessible to anyone (no auth guard needed)

## Database changes
No database changes. The `users` table already has all required columns (`id`, `email`, `password_hash`, `name`).

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — confirm form POSTs to `/login` with fields `email` and `password`; add `{{ error }}` display block if missing
  - `templates/base.html` — update navbar to show "Logout" link when `session.user_id` is set; show "Login" and "Register" links when not

## Files to change
- `app.py` — convert `/login` route to accept both `GET` and `POST`; implement `POST /login` logic; implement `GET /logout`; add `check_password_hash` to werkzeug import
- `templates/login.html` — verify form action and error display
- `templates/base.html` — conditional nav links based on session state

## Files to create
None

## New dependencies
No new dependencies. `check_password_hash` is already in `werkzeug.security` (installed).

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never f-strings in SQL
- Passwords verified with `werkzeug.security.check_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- On successful login, set `session['user_id']` and `session['user_name']`
- On invalid email or wrong password, re-render `login.html` with a single generic error: `"Invalid email or password."` — never reveal which field failed
- Empty email or password field should re-render with `"Email and password are required."`
- Logout must call `session.clear()` (not just pop keys) then `redirect(url_for('landing'))`
- `/logout` must redirect even when the user is not logged in — no crash, no error

## Definition of done
- [ ] Submitting the login form with correct credentials sets `session['user_id']` and `session['user_name']`
- [ ] Successful login redirects away from `/login`
- [ ] Wrong password re-renders the form with `"Invalid email or password."` (no crash)
- [ ] Non-existent email re-renders the form with the same generic error
- [ ] Empty email or password re-renders with `"Email and password are required."`
- [ ] Visiting `/logout` clears the session and redirects to the landing page
- [ ] Visiting `/logout` when already logged out also redirects cleanly (no error)
- [ ] Navbar shows "Logout" when logged in and "Login" / "Register" when not
- [ ] App starts without errors after changes

# Spec: Add Expense

## Overview
Step 7 implements the Add Expense feature, allowing logged-in users to record a
new expense through a form. The route currently returns a placeholder string;
this step replaces it with a real GET/POST cycle — GET renders the form,
POST validates the input, inserts the row into the `expenses` table, and
redirects to `/profile` on success. This is the primary data-entry point for
the app and is required before edit and delete (Steps 8 and 9) can be built.

## Depends on
- Step 1: Database setup (`expenses` table with `user_id`, `amount`, `category`,
  `date`, `description` columns)
- Step 2: Registration (users exist in the database)
- Step 3: Login / Logout (`session["user_id"]` is set on login)

## Routes
- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate form data, insert row, redirect to `/profile` — logged-in only

Both replace the existing stub in `app.py`.

## Database changes
No new tables or columns. The `expenses` table already has all required columns:
`user_id`, `amount`, `category`, `date`, `description`.

A new query helper `add_expense()` must be added to `database/queries.py` to
perform the INSERT. No schema migration needed.

## Templates
- **Create:** `templates/add_expense.html`
  - Extends `base.html`
  - Form with `method="POST"` and `action="{{ url_for('add_expense') }}"`
  - Fields:
    - `amount` — `<input type="number" step="0.01" min="0.01">` — required
    - `category` — `<select>` with fixed options: Food, Transport, Bills,
      Health, Entertainment, Shopping, Other — required
    - `date` — `<input type="date">` — required, defaults to today
    - `description` — `<input type="text">` — optional
  - Inline error message displayed when validation fails
  - Submit button labelled "Add Expense"
  - Link back to `/profile` for users who change their mind

## Files to change
- `app.py`
  - Replace the stub `add_expense()` route with a real GET/POST handler
  - Import `add_expense` from `database.queries`
  - GET: redirect to `/login` if not authenticated, otherwise render the form
    with today's date pre-filled
  - POST: redirect to `/login` if not authenticated; validate amount > 0,
    category is one of the allowed values, date is a valid `YYYY-MM-DD` string;
    on failure re-render the form with the error and the previously entered
    values preserved; on success call `add_expense()` and redirect to
    `url_for('profile')`
- `database/queries.py`
  - Add `add_expense(user_id, amount, category, date, description)` that
    executes a parameterised INSERT into `expenses` and commits

## Files to create
- `templates/add_expense.html` — form template (see Templates section)
- `static/css/add_expense.css` — page-specific styles using CSS variables;
  form layout consistent with `register.html` and `login.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never f-strings or string concatenation in SQL
- Passwords hashed with werkzeug (not relevant here, but applies to the project)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- The allowed category list must be defined once in `app.py` as a constant
  (`CATEGORIES`) and passed to the template — do not hardcode it in the template
- Amount must be cast to `float` and validated to be > 0 before inserting
- Date must be validated with `date.fromisoformat()` — reject anything that raises
  `ValueError` and re-render the form with an error
- On validation failure, re-render the form with all previously entered values
  preserved so the user does not have to retype everything
- After a successful insert, redirect with `redirect(url_for('profile'))` —
  do not render the form again (prevents duplicate submission on browser refresh)
- Both GET and POST must check `session.get("user_id")` and redirect to `/login`
  if not set

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in renders a form with Amount,
      Category, Date, and Description fields
- [ ] The Date field is pre-filled with today's date on first load
- [ ] Submitting the form with all valid values inserts a row into `expenses`
      and redirects to `/profile`
- [ ] The new expense appears in the transaction list on `/profile`
- [ ] Submitting with an empty amount shows an inline error and preserves the
      other field values
- [ ] Submitting with amount = 0 or a negative value shows an inline error
- [ ] Submitting with an invalid date shows an inline error
- [ ] Submitting without selecting a category shows an inline error
- [ ] Submitting with only a description (no amount/date) shows errors for the
      missing required fields
- [ ] The form renders without any inline `<style>` tags — all styling comes
      from `add_expense.css` and `style.css`

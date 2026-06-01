# Spec: Date Filter for Profile Page

## Overview
Step 6 adds a date-range filter to the profile page so users can slice their
expense data by time period. Currently the profile page shows all-time totals
and transactions with no way to narrow the view. This step adds a filter bar
at the top of the profile page with quick-select presets (This Month, Last 30
Days, Last 7 Days, All Time) and a custom date-range picker (from/to). Selecting
a filter resubmits the page via GET query parameters; the route reads those
parameters and passes them into the existing query helpers so all three data
sections — summary stats, transaction list, and category breakdown — update to
reflect the selected period.

## Depends on
- Step 1: Database setup (`get_db()`, `expenses` table with `date` column)
- Step 2: Registration (users exist in the database)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 4: Profile page UI (template structure already exists)
- Step 5: Backend connection (`database/queries.py` helpers are implemented)

## Routes
- `GET /profile` — existing route, extended to accept optional query parameters:
  - `?preset=this_month` | `last_30` | `last_7` | `all` (default: `all`)
  - `?from=YYYY-MM-DD&to=YYYY-MM-DD` — custom range (overrides preset)

No new routes.

## Database changes
No database changes. The `expenses.date` column (TEXT, `YYYY-MM-DD`) already
exists and is sufficient for date-range filtering with SQL `BETWEEN`.

## Templates
- **Modify:** `templates/profile.html`
  - Add a filter bar above the stats grid containing:
    - Four preset buttons: "This Month", "Last 30 Days", "Last 7 Days", "All Time"
    - A custom date range form with two `<input type="date">` fields (From / To)
      and a single "Apply" submit button
  - The active preset button must have an `active` class so the user can see
    which filter is currently selected
  - The custom From/To inputs must be pre-filled with the currently active date
    range values when the page loads
  - All four template variables (`stats`, `transactions`, `categories`, `user`)
    are already used — no structural changes to those sections needed

## Files to change
- `app.py` — extend the `profile()` route to:
  1. Parse `preset` and `from`/`to` query parameters from `request.args`
  2. Resolve the active date range (`date_from`, `date_to`) based on the preset
     or the custom values
  3. Pass `date_from` and `date_to` into all three query helpers
  4. Pass `active_preset`, `date_from`, and `date_to` to the template so the
     filter bar can reflect the current state
- `database/queries.py` — add optional `date_from` / `date_to` parameters to:
  - `get_summary_stats(user_id, date_from=None, date_to=None)`
  - `get_recent_transactions(user_id, limit=10, date_from=None, date_to=None)`
  - `get_category_breakdown(user_id, date_from=None, date_to=None)`
  - When both are provided, append `AND date BETWEEN ? AND ?` to the WHERE clause
  - When either is `None`, no date filter is applied (preserves existing behaviour)

## Files to create
- `static/css/filter-bar.css` — styles for the filter bar component:
  - Preset buttons row using CSS variables for colours and borders
  - Active state styling for the selected preset
  - Date inputs and Apply button styled consistently with the existing design system
  - Must import CSS variables from `style.css` — no hardcoded hex values

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never f-strings or string concatenation in SQL
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles in templates
- Date arithmetic must use Python's `datetime` module — no third-party libraries
- The `from` and `to` query parameters are user-supplied strings; validate that
  they match `YYYY-MM-DD` format before using them in queries — reject invalid
  values silently by falling back to the `all` preset
- The `profile()` route must still redirect unauthenticated users to `/login`
  before doing anything else
- The filter bar must submit via a standard HTML `<form method="GET">` — no
  JavaScript fetch or AJAX for this step
- Preset date resolution must happen in `app.py`, not in the query helpers
- `get_recent_transactions` must continue to return the most recent transactions
  within the filtered period (ordered by `date DESC`)
- If the filtered period has no expenses, all sections must return empty/zero
  values rather than raising exceptions

## Definition of done
- [ ] Visiting `/profile` with no query params shows all-time data (unchanged behaviour)
- [ ] Clicking "This Month" reloads the page and shows only expenses from the
      current calendar month
- [ ] Clicking "Last 30 Days" reloads and shows expenses from the past 30 days
- [ ] Clicking "Last 7 Days" reloads and shows expenses from the past 7 days
- [ ] Clicking "All Time" reloads and shows all expenses (same as no filter)
- [ ] Entering a custom From/To date and clicking Apply filters the data to that
      exact range (inclusive on both ends)
- [ ] The active preset button is visually highlighted
- [ ] The custom From/To inputs are pre-filled with the current filter's date range
- [ ] Summary stats, transaction list, and category breakdown all reflect the
      same filtered date range — they are consistent with each other
- [ ] A date range with no expenses shows ₹0.00 total, 0 transactions, and an
      empty category breakdown — no server error
- [ ] Invalid `from`/`to` query params (e.g. `?from=abc`) fall back to "All Time"
      without a 500 error

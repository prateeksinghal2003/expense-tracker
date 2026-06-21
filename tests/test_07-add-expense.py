"""
tests/test_07-add-expense.py

Tests for Step 07 — Add Expense feature.

Spec: .claude/specs/07-add-expense.md

Fixture strategy:
  - `app` / `client` are discovered from conftest.py
  - `controlled_user_id` provides a fresh user with 8 known expenses (from conftest.py)
  - `expense_user_id` provides a fresh user with no expenses (defined locally in this file)
  - Session is injected directly via `client.session_transaction()` — no login POST needed
  - All DB writes done by tests are scoped to users created in conftest fixtures and are
    cleaned up automatically when those fixtures tear down.

Route under test:
  GET  /expenses/add  — render the add-expense form (auth-guarded)
  POST /expenses/add  — validate, insert, redirect to /profile (auth-guarded)

The route function is named `add_expense_route` in app.py.
"""

import sqlite3
import pytest
from datetime import date

from database.db import DB_PATH


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

VALID_CATEGORIES = [
    "Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"
]

VALID_PAYLOAD = {
    "amount":      "250.50",
    "category":    "Food",
    "date":        "2026-06-15",
    "description": "Test lunch",
}


def _login(client, user_id, user_name="Test User"):
    """Inject a session so the client appears authenticated."""
    with client.session_transaction() as sess:
        sess["user_id"]   = user_id
        sess["user_name"] = user_name


# ------------------------------------------------------------------ #
# Local fixture                                                       #
# ------------------------------------------------------------------ #

@pytest.fixture
def expense_user_id():
    """
    A fresh user with no expenses.  Expense rows inserted during the test are
    deleted before the user row is removed so the teardown never hits an FK
    constraint (the schema has no ON DELETE CASCADE).

    Note: conftest.py's empty_user_id fixture uses a raw sqlite3.connect()
    without PRAGMA foreign_keys = ON, so its teardown would not enforce FKs —
    but it also does not clean up orphaned expense rows.  This local fixture
    is explicitly self-contained and leaves the DB clean after every test.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Expense Test User", "test-add-expense@spendly.com", "x"),
    )
    conn.commit()
    user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    yield user_id

    # Teardown: remove expenses first, then the user row.
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def _count_expenses_for_user(user_id):
    """Return how many rows exist in `expenses` for the given user_id."""
    conn = sqlite3.connect(DB_PATH)
    row  = conn.execute(
        "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row[0]


def _latest_expense_for_user(user_id):
    """Return the most recently inserted expense row for the given user_id, or None."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ------------------------------------------------------------------ #
# Auth guards                                                         #
# ------------------------------------------------------------------ #

class TestAuthGuard:
    """
    Spec: 'Both GET and POST must check session.get("user_id") and redirect
    to /login if not set.'
    """

    def test_get_unauthenticated_redirects_to_login(self, client):
        """GET /expenses/add without a session must redirect 302 to /login."""
        response = client.get("/expenses/add")
        assert response.status_code == 302, (
            "Unauthenticated GET must return 302"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login for unauthenticated GET"
        )

    def test_post_unauthenticated_redirects_to_login(self, client):
        """POST /expenses/add without a session must redirect 302 to /login."""
        response = client.post("/expenses/add", data=VALID_PAYLOAD)
        assert response.status_code == 302, (
            "Unauthenticated POST must return 302"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login for unauthenticated POST"
        )

    def test_get_unauthenticated_does_not_render_form(self, client):
        """Unauthenticated GET must not accidentally render the add-expense form."""
        response = client.get("/expenses/add", follow_redirects=True)
        # After redirect, we should be on the login page
        assert b"Login" in response.data or b"login" in response.data.lower(), (
            "Unauthenticated request must land on the login page, not the add-expense form"
        )


# ------------------------------------------------------------------ #
# GET — happy path                                                    #
# ------------------------------------------------------------------ #

class TestGetForm:
    """
    Spec: 'GET renders the add-expense form — logged-in only.'
    """

    def test_get_authenticated_returns_200(self, client, expense_user_id):
        """Authenticated GET to /expenses/add must return HTTP 200."""
        _login(client, expense_user_id)
        response = client.get("/expenses/add")
        assert response.status_code == 200, (
            "Authenticated GET /expenses/add must return 200"
        )

    def test_get_renders_add_expense_heading(self, client, expense_user_id):
        """Page must contain the 'Add Expense' heading."""
        _login(client, expense_user_id)
        response = client.get("/expenses/add")
        assert b"Add Expense" in response.data, (
            "The add-expense page must contain an 'Add Expense' heading"
        )

    def test_get_renders_amount_field(self, client, expense_user_id):
        """Form must include an input named 'amount'."""
        _login(client, expense_user_id)
        response = client.get("/expenses/add")
        assert b'name="amount"' in response.data, (
            "Form must contain an input element with name='amount'"
        )

    def test_get_renders_category_select(self, client, expense_user_id):
        """Form must include a select element named 'category'."""
        _login(client, expense_user_id)
        response = client.get("/expenses/add")
        assert b'name="category"' in response.data, (
            "Form must contain a select element with name='category'"
        )

    def test_get_renders_date_field(self, client, expense_user_id):
        """Form must include an input named 'date'."""
        _login(client, expense_user_id)
        response = client.get("/expenses/add")
        assert b'name="date"' in response.data, (
            "Form must contain an input element with name='date'"
        )

    def test_get_renders_description_field(self, client, expense_user_id):
        """Form must include an input named 'description'."""
        _login(client, expense_user_id)
        response = client.get("/expenses/add")
        assert b'name="description"' in response.data, (
            "Form must contain an input element with name='description'"
        )

    def test_get_renders_submit_button_labelled_add_expense(self, client, expense_user_id):
        """Submit button must be labelled 'Add Expense' per the spec."""
        _login(client, expense_user_id)
        response = client.get("/expenses/add")
        assert b"Add Expense" in response.data, (
            "The submit button must have the label 'Add Expense'"
        )

    def test_get_renders_all_category_options(self, client, expense_user_id):
        """All 7 allowed category options must appear in the rendered form."""
        _login(client, expense_user_id)
        response = client.get("/expenses/add")
        for cat in VALID_CATEGORIES:
            assert cat.encode() in response.data, (
                f"Category option '{cat}' must be present in the form"
            )

    def test_get_date_field_prefilled_with_today(self, client, expense_user_id):
        """
        Spec: 'The Date field is pre-filled with today's date on first load.'
        The response must contain today's ISO date string as the date field value.
        """
        _login(client, expense_user_id)
        response = client.get("/expenses/add")
        today_iso = date.today().isoformat().encode()
        assert today_iso in response.data, (
            f"The date field must be pre-filled with today's date ({today_iso.decode()})"
        )

    def test_get_contains_back_to_profile_link(self, client, expense_user_id):
        """
        Spec: 'Link back to /profile for users who change their mind.'
        The form page must include a link that navigates to /profile.
        """
        _login(client, expense_user_id)
        response = client.get("/expenses/add")
        assert b"/profile" in response.data, (
            "The add-expense page must contain a link back to /profile"
        )

    def test_get_no_inline_style_tags(self, client, expense_user_id):
        """
        Spec: 'The form renders without any inline <style> tags — all styling comes
        from add_expense.css and style.css.'
        """
        _login(client, expense_user_id)
        response = client.get("/expenses/add")
        assert b"<style>" not in response.data, (
            "The add-expense page must not contain inline <style> tags"
        )

    def test_get_no_error_shown_on_initial_load(self, client, expense_user_id):
        """On a fresh GET there should be no error message displayed."""
        _login(client, expense_user_id)
        response = client.get("/expenses/add")
        assert b"auth-error" not in response.data, (
            "No error div should be rendered on the initial GET request"
        )


# ------------------------------------------------------------------ #
# POST — happy path and DB side effects                               #
# ------------------------------------------------------------------ #

class TestPostHappyPath:
    """
    Spec: 'Submitting the form with all valid values inserts a row into expenses
    and redirects to /profile.'
    """

    def test_valid_post_redirects_to_profile(self, client, expense_user_id):
        """A fully valid POST must respond with a 302 redirect to /profile."""
        _login(client, expense_user_id)
        response = client.post("/expenses/add", data=VALID_PAYLOAD)
        assert response.status_code == 302, (
            "Valid POST must return 302 redirect"
        )
        assert "/profile" in response.headers["Location"], (
            "Successful POST must redirect to /profile"
        )

    def test_valid_post_inserts_row_in_db(self, client, expense_user_id):
        """
        Spec: DB side effect — after successful POST, a row must exist in the
        `expenses` table for this user.
        """
        _login(client, expense_user_id)
        before = _count_expenses_for_user(expense_user_id)
        client.post("/expenses/add", data=VALID_PAYLOAD)
        after = _count_expenses_for_user(expense_user_id)
        assert after == before + 1, (
            "Exactly one new row must be inserted into expenses on a valid POST"
        )

    def test_valid_post_correct_amount_stored(self, client, expense_user_id):
        """The inserted row must store the amount as a float matching the submitted value."""
        _login(client, expense_user_id)
        client.post("/expenses/add", data=VALID_PAYLOAD)
        row = _latest_expense_for_user(expense_user_id)
        assert row is not None, "A row must have been inserted"
        assert abs(row["amount"] - 250.50) < 0.001, (
            f"Stored amount must be 250.50, got {row['amount']}"
        )

    def test_valid_post_correct_category_stored(self, client, expense_user_id):
        """The inserted row must store the submitted category."""
        _login(client, expense_user_id)
        client.post("/expenses/add", data=VALID_PAYLOAD)
        row = _latest_expense_for_user(expense_user_id)
        assert row["category"] == "Food", (
            f"Stored category must be 'Food', got '{row['category']}'"
        )

    def test_valid_post_correct_date_stored(self, client, expense_user_id):
        """The inserted row must store the date in YYYY-MM-DD format."""
        _login(client, expense_user_id)
        client.post("/expenses/add", data=VALID_PAYLOAD)
        row = _latest_expense_for_user(expense_user_id)
        assert row["date"] == "2026-06-15", (
            f"Stored date must be '2026-06-15', got '{row['date']}'"
        )

    def test_valid_post_correct_description_stored(self, client, expense_user_id):
        """The inserted row must store the submitted description."""
        _login(client, expense_user_id)
        client.post("/expenses/add", data=VALID_PAYLOAD)
        row = _latest_expense_for_user(expense_user_id)
        assert row["description"] == "Test lunch", (
            f"Stored description must be 'Test lunch', got '{row['description']}'"
        )

    def test_valid_post_correct_user_id_stored(self, client, expense_user_id):
        """The inserted row must be linked to the authenticated user's ID."""
        _login(client, expense_user_id)
        client.post("/expenses/add", data=VALID_PAYLOAD)
        row = _latest_expense_for_user(expense_user_id)
        assert row["user_id"] == expense_user_id, (
            f"Stored user_id must match the logged-in user, "
            f"expected {expense_user_id}, got {row['user_id']}"
        )

    def test_valid_post_expense_appears_on_profile(self, client, expense_user_id):
        """
        Spec: 'The new expense appears in the transaction list on /profile.'
        After a successful insert, the description must be visible on /profile.
        """
        _login(client, expense_user_id)
        unique_description = "Unique test description 07xzy"
        payload = {**VALID_PAYLOAD, "description": unique_description}
        client.post("/expenses/add", data=payload)
        response = client.get("/profile")
        assert unique_description.encode() in response.data, (
            "The newly added expense's description must appear on the /profile page"
        )

    def test_valid_post_with_empty_description_succeeds(self, client, expense_user_id):
        """
        Spec: description is optional — an empty description must still result
        in a successful insert and a redirect to /profile.
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "description": ""}
        response = client.post("/expenses/add", data=payload)
        assert response.status_code == 302, (
            "A POST with empty description must still redirect (description is optional)"
        )
        assert "/profile" in response.headers["Location"], (
            "Successful POST with empty description must redirect to /profile"
        )

    def test_valid_post_without_description_key_succeeds(self, client, expense_user_id):
        """A POST with no description field at all must still insert and redirect."""
        _login(client, expense_user_id)
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "description"}
        response = client.post("/expenses/add", data=payload)
        assert response.status_code == 302, (
            "A POST with no description key must still succeed"
        )

    def test_valid_post_follow_redirects_shows_profile(self, client, expense_user_id):
        """Following the redirect after a valid POST must land on the profile page."""
        _login(client, expense_user_id)
        response = client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=True)
        assert response.status_code == 200, (
            "Following the redirect after valid POST must return 200 on /profile"
        )


# ------------------------------------------------------------------ #
# POST — validation errors: amount                                    #
# ------------------------------------------------------------------ #

class TestPostValidationAmount:
    """
    Spec: 'validate amount > 0 ... on failure re-render the form with the
    error and the previously entered values preserved.'
    """

    def test_empty_amount_returns_200_with_error(self, client, expense_user_id):
        """
        Spec: 'Submitting with an empty amount shows an inline error.'
        An empty amount string must not insert a row; it must re-render with an error.
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "amount": ""}
        response = client.post("/expenses/add", data=payload)
        assert response.status_code == 200, (
            "Empty amount must re-render the form (200), not redirect"
        )
        assert b"error" in response.data.lower() or b"valid" in response.data.lower(), (
            "Response must contain an error message when amount is empty"
        )

    def test_empty_amount_does_not_insert_row(self, client, expense_user_id):
        """An empty amount must not write any row to the expenses table."""
        _login(client, expense_user_id)
        before = _count_expenses_for_user(expense_user_id)
        client.post("/expenses/add", data={**VALID_PAYLOAD, "amount": ""})
        after = _count_expenses_for_user(expense_user_id)
        assert after == before, (
            "No row should be inserted when amount is empty"
        )

    @pytest.mark.parametrize("bad_amount", ["0", "0.00", "-1", "-0.01", "-100"])
    def test_zero_or_negative_amount_returns_200_with_error(
        self, client, expense_user_id, bad_amount
    ):
        """
        Spec: 'Submitting with amount = 0 or a negative value shows an inline error.'
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "amount": bad_amount}
        response = client.post("/expenses/add", data=payload)
        assert response.status_code == 200, (
            f"Amount '{bad_amount}' must re-render the form (200), not redirect"
        )
        assert b"auth-error" in response.data, (
            f"Amount '{bad_amount}' must display an inline error message"
        )

    @pytest.mark.parametrize("bad_amount", ["0", "0.00", "-1", "-0.01", "-100"])
    def test_zero_or_negative_amount_does_not_insert_row(
        self, client, expense_user_id, bad_amount
    ):
        """Zero or negative amount must not insert a row."""
        _login(client, expense_user_id)
        before = _count_expenses_for_user(expense_user_id)
        client.post("/expenses/add", data={**VALID_PAYLOAD, "amount": bad_amount})
        after = _count_expenses_for_user(expense_user_id)
        assert after == before, (
            f"No row should be inserted for amount='{bad_amount}'"
        )

    @pytest.mark.parametrize("bad_amount", ["abc", "twelve", "1,000", "₹500", "--5"])
    def test_non_numeric_amount_returns_200_with_error(
        self, client, expense_user_id, bad_amount
    ):
        """
        Spec: 'Amount must be cast to float and validated.'
        Non-numeric strings must fail validation and re-render the form with an error.
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "amount": bad_amount}
        response = client.post("/expenses/add", data=payload)
        assert response.status_code == 200, (
            f"Non-numeric amount '{bad_amount}' must re-render the form (200)"
        )
        assert b"auth-error" in response.data, (
            f"Non-numeric amount '{bad_amount}' must show an inline error"
        )

    @pytest.mark.parametrize("bad_amount", ["abc", "twelve", "1,000", "₹500"])
    def test_non_numeric_amount_does_not_insert_row(
        self, client, expense_user_id, bad_amount
    ):
        """Non-numeric amount must not write any row to the expenses table."""
        _login(client, expense_user_id)
        before = _count_expenses_for_user(expense_user_id)
        client.post("/expenses/add", data={**VALID_PAYLOAD, "amount": bad_amount})
        after = _count_expenses_for_user(expense_user_id)
        assert after == before, (
            f"No row should be inserted for non-numeric amount='{bad_amount}'"
        )


# ------------------------------------------------------------------ #
# POST — validation errors: category                                  #
# ------------------------------------------------------------------ #

class TestPostValidationCategory:
    """
    Spec: 'category is one of the allowed values ... on failure re-render with error.'
    """

    def test_missing_category_returns_200_with_error(self, client, expense_user_id):
        """
        Spec: 'Submitting without selecting a category shows an inline error.'
        An empty category string is not in CATEGORIES and must fail.
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "category": ""}
        response = client.post("/expenses/add", data=payload)
        assert response.status_code == 200, (
            "Missing category must re-render the form (200), not redirect"
        )
        assert b"auth-error" in response.data, (
            "Missing category must display an inline error message"
        )

    def test_missing_category_does_not_insert_row(self, client, expense_user_id):
        """An empty category must not write any row to the expenses table."""
        _login(client, expense_user_id)
        before = _count_expenses_for_user(expense_user_id)
        client.post("/expenses/add", data={**VALID_PAYLOAD, "category": ""})
        after = _count_expenses_for_user(expense_user_id)
        assert after == before, (
            "No row should be inserted when category is empty"
        )

    @pytest.mark.parametrize("bad_category", [
        "food",         # wrong case
        "FOOD",         # all-caps
        "Groceries",    # not in the allowed list
        "Travel",       # not in the allowed list
        "Unknown",      # not in the allowed list
        "<script>",     # injection attempt
    ])
    def test_invalid_category_returns_200_with_error(
        self, client, expense_user_id, bad_category
    ):
        """
        Spec: 'category is one of the allowed values.'
        Any value outside CATEGORIES must be rejected with an error.
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "category": bad_category}
        response = client.post("/expenses/add", data=payload)
        assert response.status_code == 200, (
            f"Invalid category '{bad_category}' must re-render the form (200)"
        )
        assert b"auth-error" in response.data, (
            f"Invalid category '{bad_category}' must display an inline error"
        )

    @pytest.mark.parametrize("bad_category", ["food", "FOOD", "Groceries", "Travel"])
    def test_invalid_category_does_not_insert_row(
        self, client, expense_user_id, bad_category
    ):
        """An invalid category value must not write a row to the DB."""
        _login(client, expense_user_id)
        before = _count_expenses_for_user(expense_user_id)
        client.post("/expenses/add", data={**VALID_PAYLOAD, "category": bad_category})
        after = _count_expenses_for_user(expense_user_id)
        assert after == before, (
            f"No row should be inserted for invalid category='{bad_category}'"
        )

    @pytest.mark.parametrize("valid_category", VALID_CATEGORIES)
    def test_each_valid_category_is_accepted(self, client, expense_user_id, valid_category):
        """Every category in CATEGORIES must be accepted by the route."""
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "category": valid_category}
        response = client.post("/expenses/add", data=payload)
        assert response.status_code == 302, (
            f"Category '{valid_category}' is valid and must trigger a redirect"
        )
        assert "/profile" in response.headers["Location"], (
            f"Valid category '{valid_category}' must redirect to /profile"
        )


# ------------------------------------------------------------------ #
# POST — validation errors: date                                      #
# ------------------------------------------------------------------ #

class TestPostValidationDate:
    """
    Spec: 'Date must be validated with date.fromisoformat() — reject anything
    that raises ValueError and re-render the form with an error.'
    """

    def test_empty_date_returns_200_with_error(self, client, expense_user_id):
        """
        Spec: 'Submitting with an invalid date shows an inline error.'
        An empty date string must fail validation.
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "date": ""}
        response = client.post("/expenses/add", data=payload)
        assert response.status_code == 200, (
            "Empty date must re-render the form (200), not redirect"
        )
        assert b"auth-error" in response.data, (
            "Empty date must display an inline error message"
        )

    def test_empty_date_does_not_insert_row(self, client, expense_user_id):
        """An empty date must not write any row to the expenses table."""
        _login(client, expense_user_id)
        before = _count_expenses_for_user(expense_user_id)
        client.post("/expenses/add", data={**VALID_PAYLOAD, "date": ""})
        after = _count_expenses_for_user(expense_user_id)
        assert after == before, (
            "No row should be inserted when date is empty"
        )

    @pytest.mark.parametrize("bad_date", [
        "15-06-2026",    # DD-MM-YYYY — wrong order
        "06/15/2026",    # MM/DD/YYYY — wrong separator
        "15 June 2026",  # long-form string
        "not-a-date",    # completely non-date
        "2026-13-01",    # month 13 — invalid calendar value
        "2026-00-10",    # month 0 — invalid calendar value
        "2026-05-32",    # day 32 — invalid calendar value
        "2026-02-30",    # February 30 — does not exist
        "20260615",      # ISO without separators
    ])
    def test_invalid_date_returns_200_with_error(
        self, client, expense_user_id, bad_date
    ):
        """
        Spec: 'Submitting with an invalid date shows an inline error.'
        Any date string that raises ValueError in date.fromisoformat() must be rejected.
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "date": bad_date}
        response = client.post("/expenses/add", data=payload)
        assert response.status_code == 200, (
            f"Invalid date '{bad_date}' must re-render the form (200)"
        )
        assert b"auth-error" in response.data, (
            f"Invalid date '{bad_date}' must display an inline error"
        )

    @pytest.mark.parametrize("bad_date", [
        "15-06-2026", "06/15/2026", "not-a-date", "2026-13-01", "2026-05-32",
    ])
    def test_invalid_date_does_not_insert_row(
        self, client, expense_user_id, bad_date
    ):
        """An invalid date must not write a row to the DB."""
        _login(client, expense_user_id)
        before = _count_expenses_for_user(expense_user_id)
        client.post("/expenses/add", data={**VALID_PAYLOAD, "date": bad_date})
        after = _count_expenses_for_user(expense_user_id)
        assert after == before, (
            f"No row should be inserted for invalid date='{bad_date}'"
        )


# ------------------------------------------------------------------ #
# POST — field preservation on validation failure                     #
# ------------------------------------------------------------------ #

class TestPostFieldPreservation:
    """
    Spec: 'on failure re-render the form with all previously entered values
    preserved so the user does not have to retype everything.'
    """

    def test_amount_preserved_when_category_invalid(self, client, expense_user_id):
        """
        When category validation fails, the previously entered amount must appear
        in the re-rendered form so the user does not lose their input.
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "amount": "999.99", "category": "BadCategory"}
        response = client.post("/expenses/add", data=payload)
        assert b"999.99" in response.data, (
            "The entered amount must be preserved in the form on validation failure"
        )

    def test_category_preserved_when_amount_invalid(self, client, expense_user_id):
        """
        When amount validation fails, the previously selected category must appear
        as the selected option in the re-rendered form.
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "amount": "-5", "category": "Transport"}
        response = client.post("/expenses/add", data=payload)
        assert b"Transport" in response.data, (
            "The entered category must be preserved in the form on validation failure"
        )

    def test_date_preserved_when_amount_invalid(self, client, expense_user_id):
        """
        When amount validation fails, the previously entered date must appear
        in the re-rendered form.
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "amount": "abc", "date": "2026-07-04"}
        response = client.post("/expenses/add", data=payload)
        assert b"2026-07-04" in response.data, (
            "The entered date must be preserved in the form on validation failure"
        )

    def test_description_preserved_when_date_invalid(self, client, expense_user_id):
        """
        When date validation fails, the previously entered description must appear
        in the re-rendered form.
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "date": "not-a-date", "description": "Dinner with team"}
        response = client.post("/expenses/add", data=payload)
        assert b"Dinner with team" in response.data, (
            "The entered description must be preserved in the form on validation failure"
        )

    def test_all_fields_preserved_when_amount_and_date_missing(self, client, expense_user_id):
        """
        Spec: 'Submitting with only a description (no amount/date) shows errors
        for the missing required fields.'
        The description and category must still appear in the re-rendered form.
        """
        _login(client, expense_user_id)
        payload = {
            "amount":      "",
            "category":    "Bills",
            "date":        "",
            "description": "Only description provided",
        }
        response = client.post("/expenses/add", data=payload)
        assert response.status_code == 200, (
            "Submitting with only a description must re-render the form (200)"
        )
        assert b"auth-error" in response.data, (
            "An error must be shown when amount is missing"
        )
        assert b"Bills" in response.data, (
            "The selected category must be preserved even when amount and date are missing"
        )
        assert b"Only description provided" in response.data, (
            "The entered description must be preserved when amount and date are missing"
        )


# ------------------------------------------------------------------ #
# POST — no duplicate submission on redirect                          #
# ------------------------------------------------------------------ #

class TestPostNoDuplicateOnRedirect:
    """
    Spec: 'After a successful insert, redirect with redirect(url_for("profile"))
    — do not render the form again (prevents duplicate submission on browser refresh).'
    """

    def test_successful_post_returns_redirect_not_rendered_form(self, client, expense_user_id):
        """
        A successful POST must return a 302, NOT a 200 with the form rendered.
        This is the POST/Redirect/GET pattern that prevents duplicate submissions.
        """
        _login(client, expense_user_id)
        response = client.post("/expenses/add", data=VALID_PAYLOAD)
        assert response.status_code == 302, (
            "A successful POST must redirect (302), not re-render the form (200)"
        )

    def test_each_post_inserts_exactly_one_row(self, client, expense_user_id):
        """Two separate valid POST submissions must result in exactly 2 new rows."""
        _login(client, expense_user_id)
        before = _count_expenses_for_user(expense_user_id)
        client.post("/expenses/add", data=VALID_PAYLOAD)
        client.post("/expenses/add", data={**VALID_PAYLOAD, "amount": "100"})
        after = _count_expenses_for_user(expense_user_id)
        assert after == before + 2, (
            "Each valid POST must insert exactly one row; two POSTs must insert two rows"
        )


# ------------------------------------------------------------------ #
# POST — edge cases and SQL-injection safety                          #
# ------------------------------------------------------------------ #

class TestPostEdgeCases:
    """
    Edge cases: very long input, SQL injection attempts in text fields.
    Parameterized queries must handle these safely without crashing.
    """

    def test_sql_injection_in_description_is_safe(self, client, expense_user_id):
        """
        A SQL injection attempt in the description field must be stored as literal text
        (parameterized queries) and must not crash the application or alter the DB schema.
        """
        _login(client, expense_user_id)
        payload = {
            **VALID_PAYLOAD,
            "description": "'); DROP TABLE expenses; --",
        }
        before = _count_expenses_for_user(expense_user_id)
        response = client.post("/expenses/add", data=payload)
        # Route should succeed — description is just text
        assert response.status_code == 302, (
            "SQL injection in description must be treated as plain text and not crash the app"
        )
        after = _count_expenses_for_user(expense_user_id)
        assert after == before + 1, (
            "The expenses table must still exist after a SQL injection attempt in description"
        )

    def test_sql_injection_in_amount_returns_error(self, client, expense_user_id):
        """
        A SQL injection string passed as amount must fail float() validation
        and re-render the form with an error — it must never reach the DB layer.
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "amount": "1; DROP TABLE expenses; --"}
        response = client.post("/expenses/add", data=payload)
        assert response.status_code == 200, (
            "SQL injection in amount must fail validation (200), not reach the DB"
        )

    def test_very_long_description_is_accepted(self, client, expense_user_id):
        """
        A very long description (500 chars) must be stored without error.
        SQLite TEXT columns have no length limit.
        """
        _login(client, expense_user_id)
        long_desc = "A" * 500
        payload = {**VALID_PAYLOAD, "description": long_desc}
        response = client.post("/expenses/add", data=payload)
        assert response.status_code == 302, (
            "A 500-character description must be accepted and result in a redirect"
        )
        row = _latest_expense_for_user(expense_user_id)
        assert row["description"] == long_desc, (
            "The full 500-character description must be stored verbatim"
        )

    def test_amount_with_many_decimal_places_is_validated(self, client, expense_user_id):
        """
        An amount like '0.001' is technically > 0 as a float. The route must
        accept it (spec only requires > 0, not a minimum precision).
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "amount": "0.001"}
        response = client.post("/expenses/add", data=payload)
        # 0.001 > 0, so this should pass validation
        assert response.status_code == 302, (
            "Amount 0.001 is > 0 and must be accepted per the spec"
        )

    def test_amount_with_whitespace_stripped_before_validation(self, client, expense_user_id):
        """
        The route strips whitespace from amount_raw before casting to float.
        '  250.50  ' must be treated as '250.50' and succeed.
        """
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "amount": "  250.50  "}
        response = client.post("/expenses/add", data=payload)
        assert response.status_code == 302, (
            "Amount with surrounding whitespace must be stripped and accepted"
        )


# ------------------------------------------------------------------ #
# POST — all valid categories accepted (parametrized)                 #
# ------------------------------------------------------------------ #

class TestPostAllCategoriesAccepted:
    """
    Spec: CATEGORIES = ["Food", "Transport", "Bills", "Health",
                        "Entertainment", "Shopping", "Other"]
    Each must be independently accepted.
    """

    @pytest.mark.parametrize("category", VALID_CATEGORIES)
    def test_category_inserts_row_with_correct_category(
        self, client, expense_user_id, category
    ):
        """Each valid category must result in an inserted row with that category stored."""
        _login(client, expense_user_id)
        payload = {**VALID_PAYLOAD, "category": category}
        client.post("/expenses/add", data=payload)
        row = _latest_expense_for_user(expense_user_id)
        assert row is not None, f"No row found after inserting with category='{category}'"
        assert row["category"] == category, (
            f"DB must store category='{category}', got '{row['category']}'"
        )

"""
tests/test_date_filter_profile.py

Tests for Step 06 — Date Filter on the Profile Page.

Spec: .claude/specs/06-date-filter-profile-page.md

Today's date (fixed for this test suite): 2026-06-01
Seed data: 8 expenses dated 2026-05-02 through 2026-05-24 (all in May 2026).

Fixture strategy mirrors conftest.py:
  - `app` / `client` imported from conftest via pytest auto-discovery
  - `controlled_user_id` is the fresh user with exactly the 8 known expenses
  - `seed_user_id` is the seeded demo@spendly.com user (for route-level auth tests)
  - All helper fixtures are defined in conftest.py and reused here without redefinition
"""

import datetime as _dt
import pytest
from database.queries import (
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #

class TestAuthGuard:
    """Unauthenticated access to /profile must always redirect to /login."""

    def test_unauthenticated_no_params_redirects_to_login(self, client):
        response = client.get("/profile")
        assert response.status_code == 302, "Expected redirect for unauthenticated user"
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login"
        )

    def test_unauthenticated_with_preset_param_redirects_to_login(self, client):
        response = client.get("/profile?preset=this_month")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_unauthenticated_with_custom_range_redirects_to_login(self, client):
        response = client.get("/profile?from=2026-05-01&to=2026-05-31")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ------------------------------------------------------------------ #
# Default / All-Time behaviour                                        #
# ------------------------------------------------------------------ #

class TestDefaultAndAllTime:
    """No query params or ?preset=all must show all-time data."""

    def test_no_params_returns_200(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile")
        assert response.status_code == 200, "Profile page must return 200 when authenticated"

    def test_no_params_shows_all_time_total(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile")
        assert "₹6,110.00".encode() in response.data, (
            "All-time total must be ₹6,110.00 when no date filter is applied"
        )

    def test_no_params_shows_all_8_transactions(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile")
        # Each transaction has a unique description; count occurrences of a known one
        assert b"Lunch at office canteen" in response.data
        assert b"Gift for colleague" in response.data

    def test_explicit_preset_all_returns_200(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?preset=all")
        assert response.status_code == 200

    def test_explicit_preset_all_shows_all_time_total(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?preset=all")
        assert "₹6,110.00".encode() in response.data, (
            "?preset=all must show same all-time total as no params"
        )


# ------------------------------------------------------------------ #
# Preset: this_month (2026-06-01 → June has 0 expenses)             #
# ------------------------------------------------------------------ #

class TestPresetThisMonth:
    """
    Today = 2026-06-01. This Month window = 2026-06-01 to 2026-06-01.
    No seeded expenses fall in June, so all three sections must return
    empty / zero values.
    """

    def _get(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        return client.get("/profile?preset=this_month")

    def test_this_month_returns_200(self, client, controlled_user_id):
        response = self._get(client, controlled_user_id)
        assert response.status_code == 200

    def test_this_month_shows_zero_total(self, client, controlled_user_id):
        response = self._get(client, controlled_user_id)
        assert "₹0.00".encode() in response.data, (
            "This Month must show ₹0.00 when no expenses exist in the current month"
        )

    def test_this_month_no_may_expenses_shown(self, client, controlled_user_id):
        response = self._get(client, controlled_user_id)
        assert b"Lunch at office canteen" not in response.data, (
            "May expenses must not appear under This Month filter"
        )


# ------------------------------------------------------------------ #
# Preset: last_30 (2026-05-02 to 2026-06-01 → all 8 rows)          #
# ------------------------------------------------------------------ #

class TestPresetLast30:
    """
    Window: today - 30 days = 2026-05-02 to 2026-06-01.
    All 8 seeded expenses (2026-05-02 through 2026-05-24) fall inside.
    """

    @pytest.fixture(autouse=True)
    def freeze_today(self, monkeypatch):
        fixed = _dt.date(2026, 6, 1)
        monkeypatch.setattr(
            "app.date",
            type("FixedDate", (), {
                "today": staticmethod(lambda: fixed),
                "fromisoformat": staticmethod(_dt.date.fromisoformat),
            }),
        )

    def _get(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        return client.get("/profile?preset=last_30")

    def test_last_30_returns_200(self, client, controlled_user_id):
        assert self._get(client, controlled_user_id).status_code == 200

    def test_last_30_shows_full_total(self, client, controlled_user_id):
        response = self._get(client, controlled_user_id)
        assert "₹6,110.00".encode() in response.data, (
            "Last 30 Days must show ₹6,110.00 — all 8 expenses are within range"
        )

    def test_last_30_shows_earliest_expense(self, client, controlled_user_id):
        """2026-05-02 is exactly 30 days before 2026-06-01, so it must be included."""
        response = self._get(client, controlled_user_id)
        assert b"Lunch at office canteen" in response.data, (
            "The 2026-05-02 expense must be included in the Last 30 Days window"
        )


# ------------------------------------------------------------------ #
# Preset: last_7 (2026-05-25 to 2026-06-01 → 0 expenses)           #
# ------------------------------------------------------------------ #

class TestPresetLast7:
    """
    Window: today - 7 days = 2026-05-25 to 2026-06-01.
    Latest seeded expense is 2026-05-24, so 0 expenses fall inside.
    """

    def _get(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        return client.get("/profile?preset=last_7")

    def test_last_7_returns_200(self, client, controlled_user_id):
        assert self._get(client, controlled_user_id).status_code == 200

    def test_last_7_shows_zero_total(self, client, controlled_user_id):
        response = self._get(client, controlled_user_id)
        assert "₹0.00".encode() in response.data, (
            "Last 7 Days must show ₹0.00 — no seeded expenses are from 2026-05-25 or later"
        )

    def test_last_7_shows_no_expenses(self, client, controlled_user_id):
        response = self._get(client, controlled_user_id)
        assert b"Gift for colleague" not in response.data, (
            "The 2026-05-24 expense must NOT appear in Last 7 Days window"
        )


# ------------------------------------------------------------------ #
# Custom date range                                                   #
# ------------------------------------------------------------------ #

class TestCustomDateRange:
    """Custom from/to parameters must filter all three data sections."""

    def test_custom_range_returns_200(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?from=2026-05-07&to=2026-05-17")
        assert response.status_code == 200

    def test_custom_range_correct_total(self, client, controlled_user_id):
        """
        2026-05-07 to 2026-05-17 covers:
          Bills ₹2200, Health ₹800, Entertainment ₹350, Shopping ₹1500 = ₹4,850.00
        """
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?from=2026-05-07&to=2026-05-17")
        assert "₹4,850.00".encode() in response.data, (
            "Custom range 2026-05-07..2026-05-17 must total ₹4,850.00"
        )

    def test_custom_range_includes_boundary_dates(self, client, controlled_user_id):
        """Inclusive on both ends: expenses on 2026-05-07 and 2026-05-17 must appear."""
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?from=2026-05-07&to=2026-05-17")
        assert b"Electricity bill May" in response.data, (
            "Expense on the 'from' boundary date (2026-05-07) must be included"
        )
        assert b"New headphones" in response.data, (
            "Expense on the 'to' boundary date (2026-05-17) must be included"
        )

    def test_custom_range_excludes_out_of_range_expenses(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?from=2026-05-07&to=2026-05-17")
        assert b"Lunch at office canteen" not in response.data, (
            "2026-05-02 expense must be excluded from the 2026-05-07..2026-05-17 range"
        )
        assert b"Gift for colleague" not in response.data, (
            "2026-05-24 expense must be excluded from the 2026-05-07..2026-05-17 range"
        )

    def test_custom_single_day_range(self, client, controlled_user_id):
        """A range where from == to must return exactly the expenses on that day."""
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?from=2026-05-02&to=2026-05-02")
        assert "₹450.00".encode() in response.data, (
            "Single-day range (2026-05-02) must show only the ₹450.00 lunch expense"
        )
        assert b"Auto-rickshaw to metro" not in response.data, (
            "2026-05-05 expense must not appear in a single-day range for 2026-05-02"
        )

    def test_custom_empty_range_returns_200(self, client, controlled_user_id):
        """A range with no expenses must not raise a 500 error."""
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?from=2026-04-01&to=2026-04-30")
        assert response.status_code == 200, (
            "An empty date range must return 200, not a 500 error"
        )

    def test_custom_empty_range_shows_zero_total(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?from=2026-04-01&to=2026-04-30")
        assert "₹0.00".encode() in response.data, (
            "An empty date range must show ₹0.00 total"
        )

    def test_custom_range_overrides_preset_param(self, client, controlled_user_id):
        """
        When both from/to and preset are supplied, the custom range must win.
        The total must match the custom range, not the preset range.
        """
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        # preset=last_7 would give 0 expenses, but custom range covers 4
        response = client.get("/profile?preset=last_7&from=2026-05-07&to=2026-05-17")
        assert "₹4,850.00".encode() in response.data, (
            "Custom from/to must override the preset parameter"
        )


# ------------------------------------------------------------------ #
# Invalid query parameters — fallback to all-time                    #
# ------------------------------------------------------------------ #

class TestInvalidParamFallback:
    """
    Malformed from/to values must fall back to all-time gracefully.
    No 500 errors; all 8 rows must appear.
    """

    def test_invalid_from_falls_back_to_all_time(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?from=abc&to=2026-05-24")
        assert response.status_code == 200, (
            "Invalid 'from' param must not raise a 500"
        )
        assert "₹6,110.00".encode() in response.data, (
            "Invalid 'from' param must fall back to all-time total"
        )

    def test_invalid_to_falls_back_to_all_time(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?from=2026-05-01&to=notadate")
        assert response.status_code == 200, (
            "Invalid 'to' param must not raise a 500"
        )
        assert "₹6,110.00".encode() in response.data, (
            "Invalid 'to' param must fall back to all-time total"
        )

    def test_both_invalid_falls_back_to_all_time(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?from=xyz&to=xyz")
        assert response.status_code == 200
        assert "₹6,110.00".encode() in response.data, (
            "Both invalid params must fall back to all-time total"
        )

    def test_from_without_to_ignored(self, client, controlled_user_id):
        """Supplying only 'from' with no 'to' should not apply a date filter."""
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?from=2026-05-10")
        assert response.status_code == 200
        # Without 'to', no custom range is formed — falls back to preset (default: all)
        assert "₹6,110.00".encode() in response.data, (
            "A 'from' param with no 'to' must not apply a partial filter"
        )

    def test_to_without_from_ignored(self, client, controlled_user_id):
        """Supplying only 'to' with no 'from' should not apply a date filter."""
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?to=2026-05-10")
        assert response.status_code == 200
        assert "₹6,110.00".encode() in response.data, (
            "A 'to' param with no 'from' must not apply a partial filter"
        )

    @pytest.mark.parametrize("bad_from,bad_to", [
        ("2026-13-01", "2026-05-31"),   # month 13 is invalid
        ("2026-05-32", "2026-05-31"),   # day 32 is invalid
        ("not-a-date", "not-a-date"),   # completely non-numeric
        ("", "2026-05-31"),             # empty string for from
    ])
    def test_various_invalid_date_formats_return_200(
        self, client, controlled_user_id, bad_from, bad_to
    ):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get(f"/profile?from={bad_from}&to={bad_to}")
        assert response.status_code == 200, (
            f"Invalid params from='{bad_from}' to='{bad_to}' must not cause a 500"
        )


# ------------------------------------------------------------------ #
# active_preset reflected in the response                            #
# ------------------------------------------------------------------ #

class TestActivePresetReflected:
    """
    The spec requires active_preset to be passed to the template so the
    filter bar can show which preset is currently selected. We verify the
    value appears in the rendered HTML.
    """

    def _authenticated_get(self, client, controlled_user_id, url):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        return client.get(url)

    def test_active_preset_all_in_response(self, client, controlled_user_id):
        response = self._authenticated_get(client, controlled_user_id, "/profile")
        assert b'filter-preset-btn active">All Time' in response.data, (
            "active_preset='all' must add the 'active' class to the All Time button"
        )

    def test_active_preset_this_month_in_response(self, client, controlled_user_id):
        response = self._authenticated_get(
            client, controlled_user_id, "/profile?preset=this_month"
        )
        assert b"this_month" in response.data, (
            "active_preset='this_month' must appear in the rendered page"
        )

    def test_active_preset_last_30_in_response(self, client, controlled_user_id):
        response = self._authenticated_get(
            client, controlled_user_id, "/profile?preset=last_30"
        )
        assert b"last_30" in response.data, (
            "active_preset='last_30' must appear in the rendered page"
        )

    def test_active_preset_last_7_in_response(self, client, controlled_user_id):
        response = self._authenticated_get(
            client, controlled_user_id, "/profile?preset=last_7"
        )
        assert b"last_7" in response.data, (
            "active_preset='last_7' must appear in the rendered page"
        )

    def test_active_preset_custom_when_from_to_supplied(self, client, controlled_user_id):
        """When from/to params override the preset, active_preset must be 'custom'."""
        response = self._authenticated_get(
            client, controlled_user_id, "/profile?from=2026-05-07&to=2026-05-17"
        )
        assert b"custom" in response.data, (
            "active_preset must be 'custom' when a custom date range is applied"
        )


# ------------------------------------------------------------------ #
# Date inputs pre-filled                                             #
# ------------------------------------------------------------------ #

class TestDateInputsPrefilled:
    """
    The spec requires the From/To inputs to be pre-filled with the active
    date range. We verify the date strings appear in the response HTML.
    """

    def test_custom_from_date_prefilled(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?from=2026-05-07&to=2026-05-17")
        assert b"2026-05-07" in response.data, (
            "The 'from' date must be pre-filled in the response HTML"
        )

    def test_custom_to_date_prefilled(self, client, controlled_user_id):
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?from=2026-05-07&to=2026-05-17")
        assert b"2026-05-17" in response.data, (
            "The 'to' date must be pre-filled in the response HTML"
        )

    def test_preset_this_month_prefills_date_from(self, client, controlled_user_id):
        """For preset=this_month, the resolved date_from (2026-06-01) must appear."""
        with client.session_transaction() as sess:
            sess["user_id"] = controlled_user_id
            sess["user_name"] = "Demo User"
        response = client.get("/profile?preset=this_month")
        assert b"2026-06-01" in response.data, (
            "The resolved date_from for this_month must be pre-filled"
        )


# ------------------------------------------------------------------ #
# Cross-section consistency                                           #
# ------------------------------------------------------------------ #

class TestCrossSectionConsistency:
    """
    The spec states all three data sections (stats, transactions, categories)
    must reflect the same filtered period consistently.
    We verify via the query helpers directly for precision.
    """

    def test_stats_count_matches_transactions_length_filtered(self, controlled_user_id):
        """
        For a filtered range, the transaction_count in stats must equal
        the number of rows returned by get_recent_transactions.
        """
        date_from = "2026-05-07"
        date_to   = "2026-05-17"
        stats = get_summary_stats(controlled_user_id, date_from, date_to)
        txns  = get_recent_transactions(controlled_user_id, date_from=date_from, date_to=date_to)
        assert stats["transaction_count"] == len(txns), (
            "transaction_count in stats must match the number of transaction rows returned"
        )

    def test_stats_count_matches_transactions_length_all_time(self, controlled_user_id):
        stats = get_summary_stats(controlled_user_id)
        txns  = get_recent_transactions(controlled_user_id)
        assert stats["transaction_count"] == len(txns), (
            "All-time transaction_count must match the all-time transaction list length"
        )

    def test_category_breakdown_only_includes_filtered_categories(self, controlled_user_id):
        """
        Categories outside the date range must not appear in the breakdown.
        Range 2026-05-07..2026-05-13 covers Bills, Health, Entertainment only.
        """
        date_from = "2026-05-07"
        date_to   = "2026-05-13"
        cats = get_category_breakdown(controlled_user_id, date_from, date_to)
        cat_names = [c["name"] for c in cats]
        assert "Bills" in cat_names
        assert "Health" in cat_names
        assert "Entertainment" in cat_names
        # Transport (2026-05-05) and Shopping (2026-05-17) are outside range
        assert "Transport" not in cat_names, (
            "Transport (2026-05-05) must not appear in the 2026-05-07..2026-05-13 breakdown"
        )
        assert "Shopping" not in cat_names, (
            "Shopping (2026-05-17) must not appear in the 2026-05-07..2026-05-13 breakdown"
        )


# ------------------------------------------------------------------ #
# Query layer — get_summary_stats with date filter                   #
# ------------------------------------------------------------------ #

class TestGetSummaryStatsWithDateFilter:

    def test_filtered_total_bills_health_entertainment_shopping(self, controlled_user_id):
        """2026-05-07 to 2026-05-17: ₹2200 + ₹800 + ₹350 + ₹1500 = ₹4,850."""
        stats = get_summary_stats(controlled_user_id, "2026-05-07", "2026-05-17")
        assert stats["total_spent"] == "₹4,850.00", (
            "Filtered total for 2026-05-07..2026-05-17 must be ₹4,850.00"
        )

    def test_filtered_transaction_count(self, controlled_user_id):
        stats = get_summary_stats(controlled_user_id, "2026-05-07", "2026-05-17")
        assert stats["transaction_count"] == 4, (
            "4 expenses fall in the 2026-05-07..2026-05-17 range"
        )

    def test_filtered_top_category(self, controlled_user_id):
        """In the 2026-05-07..2026-05-17 range, Bills (₹2200) is the top category."""
        stats = get_summary_stats(controlled_user_id, "2026-05-07", "2026-05-17")
        assert stats["top_category"] == "Bills"

    def test_empty_date_range_returns_zero_total(self, controlled_user_id):
        stats = get_summary_stats(controlled_user_id, "2026-04-01", "2026-04-30")
        assert stats["total_spent"] == "₹0.00"
        assert stats["transaction_count"] == 0
        assert stats["top_category"] == "—"

    def test_no_date_filter_returns_all_time_total(self, controlled_user_id):
        stats = get_summary_stats(controlled_user_id)
        assert stats["total_spent"] == "₹6,110.00"
        assert stats["transaction_count"] == 8

    def test_single_day_filter(self, controlled_user_id):
        """2026-05-02 only: ₹450.00, 1 transaction, top category Food."""
        stats = get_summary_stats(controlled_user_id, "2026-05-02", "2026-05-02")
        assert stats["total_spent"] == "₹450.00"
        assert stats["transaction_count"] == 1
        assert stats["top_category"] == "Food"


# ------------------------------------------------------------------ #
# Query layer — get_recent_transactions with date filter             #
# ------------------------------------------------------------------ #

class TestGetRecentTransactionsWithDateFilter:

    def test_filtered_transactions_count(self, controlled_user_id):
        txns = get_recent_transactions(
            controlled_user_id, date_from="2026-05-07", date_to="2026-05-17"
        )
        assert len(txns) == 4, (
            "4 transactions fall in the 2026-05-07..2026-05-17 range"
        )

    def test_filtered_transactions_ordered_newest_first(self, controlled_user_id):
        txns = get_recent_transactions(
            controlled_user_id, date_from="2026-05-07", date_to="2026-05-17"
        )
        assert txns[0]["date"] == "17 May 2026", (
            "Transactions within a filtered range must still be ordered newest-first"
        )

    def test_filtered_transactions_exclude_out_of_range(self, controlled_user_id):
        txns = get_recent_transactions(
            controlled_user_id, date_from="2026-05-07", date_to="2026-05-17"
        )
        descriptions = [t["description"] for t in txns]
        assert "Lunch at office canteen" not in descriptions, (
            "2026-05-02 expense must be excluded from the filtered result"
        )
        assert "Gift for colleague" not in descriptions, (
            "2026-05-24 expense must be excluded from the filtered result"
        )

    def test_filtered_transactions_include_boundary_dates(self, controlled_user_id):
        txns = get_recent_transactions(
            controlled_user_id, date_from="2026-05-07", date_to="2026-05-17"
        )
        descriptions = [t["description"] for t in txns]
        assert "Electricity bill May" in descriptions, (
            "Expense on the 'from' boundary (2026-05-07) must be included"
        )
        assert "New headphones" in descriptions, (
            "Expense on the 'to' boundary (2026-05-17) must be included"
        )

    def test_empty_date_range_returns_empty_list(self, controlled_user_id):
        txns = get_recent_transactions(
            controlled_user_id, date_from="2026-04-01", date_to="2026-04-30"
        )
        assert txns == [], (
            "An empty date range must return an empty list, not raise an exception"
        )

    def test_no_date_filter_returns_all_transactions(self, controlled_user_id):
        txns = get_recent_transactions(controlled_user_id)
        assert len(txns) == 8

    def test_filtered_amounts_have_rupee_prefix(self, controlled_user_id):
        txns = get_recent_transactions(
            controlled_user_id, date_from="2026-05-07", date_to="2026-05-17"
        )
        for t in txns:
            assert t["amount"].startswith("₹"), (
                "Every filtered transaction amount must start with the ₹ symbol"
            )


# ------------------------------------------------------------------ #
# Query layer — get_category_breakdown with date filter              #
# ------------------------------------------------------------------ #

class TestGetCategoryBreakdownWithDateFilter:

    def test_filtered_breakdown_category_count(self, controlled_user_id):
        """2026-05-07..2026-05-17: Bills, Health, Entertainment, Shopping = 4 categories."""
        cats = get_category_breakdown(controlled_user_id, "2026-05-07", "2026-05-17")
        assert len(cats) == 4, (
            "4 distinct categories exist in the 2026-05-07..2026-05-17 range"
        )

    def test_filtered_breakdown_ordered_by_amount_descending(self, controlled_user_id):
        """Bills (₹2200) must be first in the filtered breakdown."""
        cats = get_category_breakdown(controlled_user_id, "2026-05-07", "2026-05-17")
        assert cats[0]["name"] == "Bills", (
            "Bills (₹2200) must be the top category in the filtered breakdown"
        )

    def test_filtered_breakdown_percents_sum_to_100(self, controlled_user_id):
        cats = get_category_breakdown(controlled_user_id, "2026-05-07", "2026-05-17")
        total_percent = sum(c["percent"] for c in cats)
        assert total_percent == 100, (
            "Category percents must sum to 100 for any filtered date range"
        )

    def test_filtered_breakdown_amounts_have_rupee_prefix(self, controlled_user_id):
        cats = get_category_breakdown(controlled_user_id, "2026-05-07", "2026-05-17")
        for c in cats:
            assert c["amount"].startswith("₹"), (
                "Every category amount must start with ₹"
            )

    def test_empty_date_range_returns_empty_list(self, controlled_user_id):
        cats = get_category_breakdown(controlled_user_id, "2026-04-01", "2026-04-30")
        assert cats == [], (
            "An empty date range must return an empty list for category breakdown"
        )

    def test_no_date_filter_returns_all_categories(self, controlled_user_id):
        cats = get_category_breakdown(controlled_user_id)
        assert len(cats) == 7, (
            "All 7 categories must be returned when no date filter is applied"
        )

    def test_single_day_range_single_category(self, controlled_user_id):
        """2026-05-02 only has one expense (Food), so breakdown must have 1 category."""
        cats = get_category_breakdown(controlled_user_id, "2026-05-02", "2026-05-02")
        assert len(cats) == 1
        assert cats[0]["name"] == "Food"
        assert cats[0]["percent"] == 100, (
            "A single-category breakdown must have 100% for that category"
        )

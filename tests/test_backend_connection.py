import pytest
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


# ------------------------------------------------------------------ #
# get_user_by_id                                                       #
# ------------------------------------------------------------------ #

def test_get_user_by_id_returns_correct_fields(controlled_user_id):
    user = get_user_by_id(controlled_user_id)
    assert user is not None
    assert user["name"] == "Demo User"
    assert user["email"] == "test-controlled@spendly.com"
    assert user["initials"] == "DU"
    assert "member_since" in user


def test_get_user_by_id_nonexistent_returns_none():
    assert get_user_by_id(99999) is None


# ------------------------------------------------------------------ #
# get_summary_stats                                                    #
# ------------------------------------------------------------------ #

def test_get_summary_stats_correct_total(controlled_user_id):
    stats = get_summary_stats(controlled_user_id)
    assert stats["total_spent"] == "₹6,110.00"


def test_get_summary_stats_correct_count(controlled_user_id):
    stats = get_summary_stats(controlled_user_id)
    assert stats["transaction_count"] == 8


def test_get_summary_stats_correct_top_category(controlled_user_id):
    stats = get_summary_stats(controlled_user_id)
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_empty_user(empty_user_id):
    stats = get_summary_stats(empty_user_id)
    assert stats["total_spent"] == "₹0.00"
    assert stats["transaction_count"] == 0
    assert stats["top_category"] == "—"


# ------------------------------------------------------------------ #
# get_recent_transactions                                              #
# ------------------------------------------------------------------ #

def test_get_recent_transactions_returns_8_rows(controlled_user_id):
    txns = get_recent_transactions(controlled_user_id)
    assert len(txns) == 8


def test_get_recent_transactions_newest_first(controlled_user_id):
    txns = get_recent_transactions(controlled_user_id)
    assert txns[0]["date"] == "24 May 2026"


def test_get_recent_transactions_has_required_fields(controlled_user_id):
    txns = get_recent_transactions(controlled_user_id)
    for t in txns:
        assert "date" in t
        assert "description" in t
        assert "category" in t
        assert "amount" in t
        assert t["amount"].startswith("₹")


def test_get_recent_transactions_empty_user(empty_user_id):
    assert get_recent_transactions(empty_user_id) == []


# ------------------------------------------------------------------ #
# get_category_breakdown                                               #
# ------------------------------------------------------------------ #

def test_get_category_breakdown_returns_7_categories(controlled_user_id):
    cats = get_category_breakdown(controlled_user_id)
    assert len(cats) == 7


def test_get_category_breakdown_percents_sum_to_100(controlled_user_id):
    cats = get_category_breakdown(controlled_user_id)
    assert sum(c["percent"] for c in cats) == 100


def test_get_category_breakdown_ordered_by_amount(controlled_user_id):
    cats = get_category_breakdown(controlled_user_id)
    assert cats[0]["name"] == "Bills"


def test_get_category_breakdown_has_required_fields(controlled_user_id):
    cats = get_category_breakdown(controlled_user_id)
    for c in cats:
        assert "name" in c
        assert "amount" in c
        assert "percent" in c
        assert isinstance(c["percent"], int)
        assert c["amount"].startswith("₹")


def test_get_category_breakdown_empty_user(empty_user_id):
    assert get_category_breakdown(empty_user_id) == []


# ------------------------------------------------------------------ #
# GET /profile route                                                   #
# ------------------------------------------------------------------ #

def test_profile_unauthenticated_redirects(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated_returns_200(client, seed_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    response = client.get("/profile")
    assert response.status_code == 200


def test_profile_shows_real_user_name(client, seed_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    response = client.get("/profile")
    assert b"Demo User" in response.data


def test_profile_shows_rupee_symbol(client, seed_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    response = client.get("/profile")
    assert "₹".encode() in response.data

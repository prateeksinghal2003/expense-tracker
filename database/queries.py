from database.db import get_db
from datetime import datetime


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    words = row["name"].split()
    initials = "".join(w[0].upper() for w in words)[:2]
    member_since = datetime.strptime(row["created_at"][:19], "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
    return {
        "name":         row["name"],
        "email":        row["email"],
        "initials":     initials,
        "member_since": member_since,
    }


def get_summary_stats(user_id):
    conn = get_db()
    agg = conn.execute(
        "SELECT SUM(amount), COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    top = conn.execute(
        "SELECT category FROM expenses WHERE user_id = ? "
        "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    total = agg[0] or 0.0
    return {
        "total_spent":       f"₹{total:,.2f}",
        "transaction_count": agg[1] or 0,
        "top_category":      top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    rows = conn.execute(
        "SELECT date, description, category, amount "
        "FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [
        {
            "date":        datetime.strptime(r["date"], "%Y-%m-%d").strftime("%d %b %Y"),
            "description": r["description"],
            "category":    r["category"],
            "amount":      f"₹{r['amount']:,.2f}",
        }
        for r in rows
    ]


def get_category_breakdown(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT category, SUM(amount) as total "
        "FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    if not rows:
        return []
    grand = sum(r["total"] for r in rows)
    result = [
        {
            "name":    r["category"],
            "amount":  f"₹{r['total']:,.2f}",
            "percent": round(r["total"] / grand * 100),
        }
        for r in rows
    ]
    diff = 100 - sum(c["percent"] for c in result)
    result[0]["percent"] += diff
    return result

from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = "spendly-dev-secret"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("profile"))
        return render_template("register.html")

    name             = request.form.get("name", "").strip()
    email            = request.form.get("email", "").strip()
    password         = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or not email:
        return render_template("register.html", error="Name and email are required.")
    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")
    if password != confirm_password:
        return render_template("register.html", error="Passwords do not match.")

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return render_template("register.html", error="An account with that email already exists.")

    password_hash = generate_password_hash(password)
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    conn.commit()
    user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    session["user_id"]   = user_id
    session["user_name"] = name
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("profile"))
        return render_template("login.html")

    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="Email and password are required.")

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"]   = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "initials": "DU",
        "member_since": "January 2026",
    }
    stats = {
        "total_spent": "₹6,110.00",
        "transaction_count": 8,
        "top_category": "Bills",
    }
    transactions = [
        {"date": "24 May 2026", "description": "Gift for colleague",     "category": "Other",         "amount": "₹600.00"},
        {"date": "20 May 2026", "description": "Cab to airport",         "category": "Transport",     "amount": "₹90.00"},
        {"date": "17 May 2026", "description": "New headphones",         "category": "Shopping",      "amount": "₹1,500.00"},
        {"date": "13 May 2026", "description": "Movie tickets",          "category": "Entertainment", "amount": "₹350.00"},
        {"date": "10 May 2026", "description": "Pharmacy — vitamins",    "category": "Health",        "amount": "₹800.00"},
        {"date": "07 May 2026", "description": "Electricity bill May",   "category": "Bills",         "amount": "₹2,200.00"},
        {"date": "05 May 2026", "description": "Auto-rickshaw to metro", "category": "Transport",     "amount": "₹120.00"},
        {"date": "02 May 2026", "description": "Lunch at canteen",       "category": "Food",          "amount": "₹450.00"},
    ]
    categories = [
        {"name": "Bills",         "amount": "₹2,200.00", "percent": 36},
        {"name": "Shopping",      "amount": "₹1,500.00", "percent": 25},
        {"name": "Health",        "amount": "₹800.00",   "percent": 13},
        {"name": "Other",         "amount": "₹600.00",   "percent": 10},
        {"name": "Entertainment", "amount": "₹350.00",   "percent": 6},
        {"name": "Food",          "amount": "₹450.00",   "percent": 7},
        {"name": "Transport",     "amount": "₹210.00",   "percent": 3},
    ]
    return render_template(
        "profile.html",
        user=user, stats=stats,
        transactions=transactions, categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


if __name__ == "__main__":
    app.run(debug=True, port=5001)

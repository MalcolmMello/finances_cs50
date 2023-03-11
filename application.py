import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    id = session["user_id"]
    wallet = db.execute("SELECT * FROM wallet JOIN users ON users.id = wallet.user_id WHERE user_id = ?", id)
    if len(wallet) == 0:
        wallet = db.execute("SELECT cash FROM users WHERE id = ?", id)
        total = wallet[0]["cash"]
        return render_template("index.html", wallet=wallet, total=total)

    total = wallet[0]["cash"]

    for i in range(len(wallet)):
        total = total + wallet[i]["price"] * wallet[i]["length"]

    return render_template("index.html", wallet=wallet, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("You must type a symbol")

        elif not request.form.get("length"):
            return apology("You must type the length")

        quote = lookup(request.form.get("symbol"))

        if quote != None:
            id = session["user_id"]
            user_cash = db.execute("SELECT cash FROM users WHERE id = (?)", id)
            if(user_cash[0]["cash"] - (float(quote["price"]) * float(request.form.get("length"))) >= 0):
                db.execute("UPDATE users SET cash = (?) WHERE id = (?)", user_cash[0]["cash"] - (float(quote["price"]) * float(request.form.get("length"))), id)
                db.execute("INSERT INTO wallet (symbol, name, price, length, user_id) VALUES (?, ?, ?, ?, ?)", quote["symbol"], quote["name"], float(quote["price"]), int(request.form.get("length")), id)
                db.execute("INSERT INTO transactions (symbol, shares, price, user_id) VALUES (?, ?, ?, ?)", quote["symbol"], int(request.form.get("length")), float(quote["price"]), id)
                return index()
            else:
                return apology("You don't have enough founds")
        else:
            return apology("Quote doesn't exist")
    elif request.method == "GET":
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    id = session["user_id"]

    history = db.execute("SELECT * FROM transactions WHERE user_id = ?", id)

    if len(history) == 0:
        return apology("You didn't make any transactions")

    return render_template("history.html", transactions=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("You must type a symbol")
        quote = lookup(request.form.get("symbol"))
        if quote != None:

            print(quote)
            return render_template("quote.html", quote=quote)
        else:
            return apology("Quote doesn't exist")
    elif request.method == "GET":
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password") or not request.form.get("confirm_password"):
            return apology("must provide password", 403)

        # Ensure passwords match each other
        if request.form.get("password") != request.form.get("confirm_password"):
            return apology("passwords must match each other", 403)

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(rows) >= 1:
            return apology("User already exists", 403)

        hash_password = generate_password_hash(request.form.get("password"))

        new_user = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get("username"), hash_password)

        session["user_id"] = new_user

        return redirect("/")

    elif request.method == "GET":
        return render_template("signup.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    id = session["user_id"]

    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("You must inform the symbol")

        if not request.form.get("shares"):
            return apology("You must inform shares length")

        quote = lookup(request.form.get("symbol"))

        if quote != None:

            user_quote = db.execute("SELECT id, symbol, length FROM wallet WHERE symbol = ? AND user_id = ?", request.form.get("symbol"), id)

            if user_quote[0]["length"] == 0:
                db.execute("DELETE FROM wallet WHERE id = ?", user_quote[0]["id"])
                return apology("You don't have this quote")

            if user_quote[0]["length"] - int(request.form.get("shares")) < 0:
                return apology("You can't sell more quotes than you have")

            db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", int(request.form.get("shares")) * quote["price"], id)

            if user_quote[0]["length"] - int(request.form.get("shares")) == 0:
                db.execute("DELETE FROM wallet WHERE id = ?", user_quote[0]["id"])
            else:
                db.execute("UPDATE wallet SET length = length - ? WHERE user_id = ? AND id = ?", int(request.form.get("shares")), id, user_quote[0]["id"])

            db.execute("INSERT INTO transactions (symbol, shares, price, user_id) VALUES (?, ?, ?, ?)", quote["symbol"], -int(request.form.get("shares")), float(quote["price"]), id)

            return index()
        else:
            return apology("That quote doesn't exists")


    elif request.method == "GET":
        wallet = db.execute("SELECT symbol FROM wallet WHERE user_id = ?", id)
        if len(wallet) == 0:
            return apology("You don't have quotes yet")
        return render_template("sell.html", wallet=wallet)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

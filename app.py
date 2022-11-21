import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response



@app.route("/")
@app.route("/portal")
def portal():
        return render_template("portal.html")
@login_required
def index():
    """Show portfolio of stocks"""
    if session["user_id"]:

        data = db.execute(
            "SELECT symbol, price,current_share, name, (price * current_share) FROM cart WHERE id_users =?", session["user_id"])
    # user_symbols = db.execute("SELECT DISTINCT symbol FROM purchase WHERE id_users =? ", session["user_id"])
        # user_shares= db.execute("SELECT symbol, price, shares,(shares*price), FROM cart WHERE id = ?" , session["user_id"] )

    # for i in user_symbols:
        # sum = db.execute("SELECT SUM(shares) FROM purchase WHERE id_users=? AND symbol="?"" , session["user_id"] , i["symbol"])

        cash_dict = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]
        total_dict = db.execute("SELECT SUM(price * current_share) FROM cart WHERE id_users = ?", session["user_id"])[0]
        cash = round(cash_dict["cash"])
        if total_dict["SUM(price * current_share)"] == None:
            total = cash
        else:
            total = cash + total_dict["SUM(price * current_share)"]
        return render_template("index.html", data=data, cash=cash, total=round(total))
    # return render_template("quoted.html")
    else:
        return redirect("login")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # get symbol and shares from user
        symbol = request.form.get("symbol")
        shares = (request.form.get("shares"))
        # get a dict which has all tje desired information
        name = lookup(symbol)
        # select the cash value
        cash_list = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        cash_dict = cash_list[0]
        cash = cash_dict["cash"]

        # check user inputs
        if not symbol:
            return apology("Please enter the symbol", 400)
        if not shares:
            return apology("please enter the shares", 400)
        if name == None:
            return apology("pleasr enter a vaild symbol", 400)
        if not (shares.isnumeric()):
            return apology("please enter a positive intger", 400)
        if name["price"] * int(shares) > cash:
            return apology("this share exceed the cash that you have", 400)
        # time
        now = datetime.now()

        # insert the values of a purchase

        db.execute("INSERT INTO purchase (symbol , name , price , shares ,date , id_users) VALUES (? , ? ,? , ? ,? , ?)",
                   symbol, name["name"], name["price"], shares, now, session["user_id"])
        # update the share value
        #current_share= (db.execute("SELECT current_share FROM cart WHERE id_users =? AND symbol = ?" ,session["user_id"] , symbol ))[0]
        #share_update= current_share["current_share"] + shares
        #db.execute("UPDATE cart SET current_share=? WHERE id_users = ? AND symbol =?" , share_update , session["user_id"] , symbol)
        current_symbols_dict = db.execute("SELECT symbol FROM cart WHERE id_users=?", session["user_id"])
        current_symbols = []
        for i in current_symbols_dict:
            current_symbols.append(i["symbol"])
        current_shares_dict = (db.execute("SELECT SUM(shares) FROM purchase WHERE id_users=? AND symbol=?",
                                          session["user_id"], symbol))[0]
        current_shares = current_shares_dict["SUM(shares)"]

        if symbol in current_symbols:
            db.execute("UPDATE cart SET  current_share = ? WHERE id_users=? AND symbol=?",
                       current_shares, session["user_id"],  symbol)
        else:
            db.execute("INSERT INTO cart (symbol ,current_share ,id_users, name , price) VALUES(?,?,?,?,?)",
                       symbol, shares, session["user_id"], name["name"], name["price"])
        # update cash value
        cash_update = cash - (name["price"] * int(shares))
        db.execute("UPDATE users SET cash =? WHERE id = ?", cash_update, session["user_id"])

        return redirect("/")

    else:

        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    data = db.execute("SELECT symbol , shares , price , date FROM purchase WHERE id_users=?", session["user_id"])
    return render_template("history.html", data=data)


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
        symbol = request.form.get("symbol")
        if symbol == None:
            return apology("sympol is not correct", 400)

        elif lookup(symbol) == None:
            return apology("sympol is not found", 400)

        else:
            quote = lookup(symbol)
            return render_template("quoted.html", quote=quote)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Forget any user_id
    session.clear()
    # User reached route via POST (as by submitting a form via POST)
    usernames = list(db.execute("SELECT username FROM users"))
    if request.method == "POST":

        if not request.form.get("username"):

            return apology("must provide username", 400)

        # Ensure password was submitted
        if not request.form.get("password"):
            return apology("must provide password", 400)

        if not request.form.get("confirmation"):
            return apology("must provide verify password", 400)

        if request.form.get("password") != request.form.get("confirmation"):
            return apology("must provide same password", 400)
        for i in usernames:

            if request.form.get("username") == i["username"]:
                return apology("user name is already exist", 400)

        username = request.form.get("username")
        password = generate_password_hash(request.form.get("password"))
        db.execute("INSERT INTO users (username , hash) VALUES (? ,?)", username, password)
        session["user_id"] = (db.execute("SELECT id FROM users   WHERE username= ?", username))[0]["id"]
       # return render_template("test.html" , m = session["user_id"])
        db.execute("INSERT INTO cart (id_users, symbol, current_share) VALUES (?,?,?)", session["user_id"], " ", 0)
        # return render_template("test.html" , d = usernames)
        return redirect("/")

    else:
        return render_template("register.html")

    # return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    cash_list = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
    cash_dict = cash_list[0]
    cash = cash_dict["cash"]
    current_symbol_dict = (db.execute("SELECT DISTINCT symbol FROM purchase WHERE id_users=?", session["user_id"]))
    current_symbol = []
    for i in current_symbol_dict:
        current_symbol.append(i["symbol"])
    if request.method == "POST":

        symbol = request.form.get("symbol")
        name = lookup(symbol)
        share = int(request.form.get("shares"))

        current_shares_dict = (db.execute("SELECT SUM(shares) FROM purchase WHERE id_users=? AND symbol=?",
                                          session["user_id"], symbol))[0]
        shares = current_shares_dict["SUM(shares)"]
       # return render_template("test.html" , s = current_symbol , a = current_shares)
        if not current_symbol:
            return apology("please rnter avalid symbol", 400)

        if symbol not in current_symbol:

            return apology("please rnter avalid symbol", 400)

        if shares == 0 or share > shares:
            return apology("sorry you dont have this amount", 400)
        now = datetime.now()
        db.execute("INSERT INTO purchase (symbol , name , price , shares ,date , id_users) VALUES (? , ? ,? , ? ,? , ?)",
                   symbol, name["name"], name["price"], -share, now, session["user_id"])
        current_share_dict = (db.execute("SELECT SUM(shares) FROM purchase WHERE id_users=? AND symbol=?",
                                         session["user_id"], symbol))[0]
        shares = current_share_dict["SUM(shares)"]

        db.execute("UPDATE cart SET current_share= ? WHERE id_users=? AND symbol = ?", shares, session["user_id"], symbol)
       # share_update= current_shares["current_share"] - shares
       # db.execute("UPDATE purchase SET current_share=? WHERE id_users = ? AND symbol =?" , share_update , session["user_id"] , symbol)
        # current_symbols= db.execute("SELECT symbol FROM cart WHERE id_users=?" , session["user_id"] )
        # if symbol in current_symbols["symbol"]:
        # db.execute("UPDATE cart SET  current_share = ? WHERE id_users=? AND symbol=?" , current_shares-shares ,session["user_id"] ,  symbol )
        # else:
        # db.execute("INSERT INTO cart (symbol ,current_share ,id_users, name , price" ,symbol, current_shares-shares ,session["user_id"] ,name["name"] ,name["price"] )

        cash_update = cash + (name["price"] * share)
        db.execute("UPDATE users SET cash =? WHERE id = ?", cash_update, session["user_id"])
        return redirect("/")

    else:
        return render_template("sell.html", symbols=current_symbol)


@app.route("/change", methods=["GET","POST"])
@login_required
def change():
    if request.method == "POST":
        password =  generate_password_hash(request.form.get("password"))
        pass_old = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])[0]["hash"]
        new = request.form.get("new")
        conf = request.form.get("conf")
        updated =  generate_password_hash(new)
        check = check_password_hash(pass_old, request.form.get("password"))
        #return render_template("test.html" , a = password , x = x)
        if not (check):
            return apology("enter password", 403)
        if new != conf:
            return apology("enter same passwords" , 405)
        db.execute("UPDATE users SET hash =? WHERE id = ?", updated , session["user_id"])
        return redirect("/")
    else:
        return render_template("change.html")


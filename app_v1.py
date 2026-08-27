from flask import Flask, request, redirect, render_template_string
import sqlite3

app = Flask(__name__)
DB = "coffee.db"

MENU = [
    ("☕ Ethiopian Coffee", 40),
    ("🥛 Macchiato", 50),
    ("🍵 Tea", 30),
    ("☕ Espresso", 45),
    ("🥛 Cappuccino", 60),
    ("🥛 Latte", 65)
]

def db():
    return sqlite3.connect(DB)

def setup():
    con = db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT,
            item TEXT,
            quantity INTEGER,
            total REAL
        )
    """)
    con.commit()
    con.close()

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>My Coffee House</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body {
    font-family: Arial;
    background: #f5f1eb;
    margin: 0;
    padding: 20px;
}
h1 {
    text-align: center;
    color: #5c3a21;
}
.card {
    background: white;
    padding: 18px;
    margin: 12px 0;
    border-radius: 15px;
    box-shadow: 0 3px 10px #ddd;
}
button {
    background: #6f4e37;
    color: white;
    border: 0;
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 16px;
}
input {
    padding: 12px;
    width: 90%;
    margin: 10px 0;
    border: 1px solid #ccc;
    border-radius: 8px;
}
.price {
    font-weight: bold;
}
a {
    color: #6f4e37;
}
</style>
</head>

<body>

<h1>☕ My Coffee House</h1>

{% if page == "menu" %}

<h2>Menu</h2>

{% for i, item in enumerate(menu) %}

<div class="card">
<h3>{{ item[0] }}</h3>
<p class="price">{{ item[1] }} ETB</p>

<form action="/order" method="POST">
<input type="hidden" name="item" value="{{ item[0] }}">
<input type="hidden" name="price" value="{{ item[1] }}">
<button type="submit">Add to Order 🛒</button>
</form>
</div>

{% endfor %}

{% elif page == "order" %}

<h2>Customer Information</h2>

<form action="/confirm" method="POST">

<input
name="customer"
placeholder="Customer Name"
required>

<input
name="item"
value="{{ item }}"
readonly>

<input
name="price"
value="{{ price }}"
readonly>

<button type="submit">
Confirm Order ✅
</button>

</form>

<a href="/">← Back to Menu</a>

{% elif page == "success" %}

<h1>✅ Order Confirmed!</h1>

<h2>Thank you, {{ customer }} ☕</h2>

<p>Your {{ item }} order has been received.</p>

<a href="/">Order Another ☕</a>

{% endif %}

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(
        HTML,
        page="menu",
        menu=MENU,
        enumerate=enumerate
    )

@app.route("/order", methods=["POST"])
def order():
    return render_template_string(
        HTML,
        page="order",
        item=request.form["item"],
        price=request.form["price"]
    )

@app.route("/confirm", methods=["POST"])
def confirm():

    customer = request.form["customer"]
    item = request.form["item"]
    price = float(request.form["price"])

    con = db()

    con.execute("""
        INSERT INTO orders
        (customer, item, quantity, total)
        VALUES (?, ?, ?, ?)
    """, (customer, item, 1, price))

    con.commit()
    con.close()

    return render_template_string(
        HTML,
        page="success",
        customer=customer,
        item=item
    )

if __name__ == "__main__":
    setup()
    app.run(host="0.0.0.0", port=5000, debug=True)

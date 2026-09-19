from flask import Flask, request, redirect, render_template_string, session
import os

app = Flask(__name__)
app.secret_key = "coffee-house-secret-key"

MENU = [
    {"id": 1, "name": "Ethiopian Coffee", "price": 40},
    {"id": 2, "name": "Macchiato", "price": 50},
    {"id": 3, "name": "Tea", "price": 30},
    {"id": 4, "name": "Espresso", "price": 45},
    {"id": 5, "name": "Cappuccino", "price": 60},
]

orders = []
order_number = 1

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>My Coffee House</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f5f1eb;
            margin: 0;
            padding: 15px;
        }

        .container {
            max-width: 600px;
            margin: auto;
        }

        h1 {
            text-align: center;
            color: #6f4e37;
        }

        .card {
            background: white;
            padding: 18px;
            margin: 12px 0;
            border-radius: 15px;
            box-shadow: 0 2px 8px #ddd;
        }

        button {
            background: #6f4e37;
            color: white;
            border: none;
            padding: 11px 18px;
            border-radius: 8px;
            cursor: pointer;
        }

        input, select {
            padding: 11px;
            margin: 5px 0;
            width: 100%;
            box-sizing: border-box;
            border: 1px solid #ccc;
            border-radius: 7px;
        }

        .cart {
            background: #fff3df;
            padding: 18px;
            border-radius: 15px;
            margin-top: 20px;
        }

        .total {
            font-size: 20px;
            font-weight: bold;
            color: #6f4e37;
        }

        a {
            color: #6f4e37;
            text-decoration: none;
            font-weight: bold;
        }
    </style>
</head>

<body>
<div class="container">

<h1>☕ My Coffee House</h1>

{% if page == "menu" %}

<div class="card">
    <h2>Customer Information</h2>

    <form method="POST" action="/customer">
        <input
            type="text"
            name="customer"
            placeholder="Customer name"
            required>

        <input
            type="number"
            name="table"
            placeholder="Table number"
            min="1"
            required>

        <button type="submit">
            Start Order
        </button>
    </form>
</div>

{% if customer %}

<div class="card">
    <h2>☕ Menu</h2>

    {% for item in menu %}

    <div class="card">
        <h3>{{ item.name }}</h3>
        <p>{{ item.price }} ETB</p>

        <form method="POST" action="/add">
            <input
                type="hidden"
                name="id"
                value="{{ item.id }}">

            <input
                type="number"
                name="quantity"
                value="1"
                min="1"
                max="20">

            <button type="submit">
                🛒 Add to Cart
            </button>
        </form>
    </div>

    {% endfor %}
</div>

{% if cart %}

<div class="cart">
    <h2>🛒 Your Cart</h2>

    {% for item in cart %}
        <p>
            {{ item.name }}
            × {{ item.quantity }}
            = {{ item.total }} ETB
        </p>
    {% endfor %}

    <hr>

    <p class="total">
        Total: {{ total }} ETB
    </p>

    <form method="POST" action="/place-order">
        <button type="submit">
            ✅ PLACE ORDER
        </button>
    </form>
</div>

{% endif %}

{% endif %}

{% elif page == "success" %}

<div class="card">
    <h2>✅ Order Sent!</h2>

    <p>Order #: <strong>{{ order.id }}</strong></p>
    <p>Customer: <strong>{{ order.customer }}</strong></p>
    <p>Table: <strong>{{ order.table }}</strong></p>
    <p>Total: <strong>{{ order.total }} ETB</strong></p>

    <hr>

    {% for item in order["items"] %}
        <p>
            {{ item.name }} × {{ item.quantity }}
        </p>
    {% endfor %}

    <h3>👨‍🍳 Your order has been sent to the kitchen.</h3>

    <a href="/">
        ← New Order
    </a>
</div>

{% elif page == "kitchen" %}

<h2>👨‍🍳 Kitchen Dashboard</h2>

{% if orders %}

{% for order in orders %}

<div class="card">

    <h3>Order #{{ order.id }}</h3>

    <p>
        👤 {{ order.customer }}
    </p>

    <p>
        🪑 Table {{ order.table }}
    </p>

    {% for item in order["items"] %}
        <p>
            ☕ {{ item.name }}
            × {{ item.quantity }}
        </p>
    {% endfor %}

    <p class="total">
        {{ order.total }} ETB
    </p>

    <p>
        Status: <strong>{{ order.status }}</strong>
    </p>

</div>

{% endfor %}

{% else %}

<div class="card">
    <h3>No orders yet ☕</h3>
</div>

{% endif %}

<a href="/">← Customer Menu</a>

{% endif %}

</div>
</body>
</html>
"""


@app.route("/")
def home():

    customer = session.get("customer")
    table = session.get("table")
    cart = session.get("cart", [])

    total = sum(item["total"] for item in cart)

    return render_template_string(
        HTML,
        page="menu",
        menu=MENU,
        customer=customer,
        table=table,
        cart=cart,
        total=total
    )


@app.route("/customer", methods=["POST"])
def customer():

    session["customer"] = request.form["customer"]
    session["table"] = request.form["table"]
    session["cart"] = []

    return redirect("/")


@app.route("/add", methods=["POST"])
def add():

    item_id = int(request.form["id"])
    quantity = int(request.form["quantity"])

    selected = next(
        item for item in MENU
        if item["id"] == item_id
    )

    cart = session.get("cart", [])

    found = False

    for item in cart:

        if item["id"] == item_id:
            item["quantity"] += quantity
            item["total"] = (
                item["quantity"] * item["price"]
            )
            found = True
            break

    if not found:

        cart.append({
            "id": selected["id"],
            "name": selected["name"],
            "price": selected["price"],
            "quantity": quantity,
            "total": selected["price"] * quantity
        })

    session["cart"] = cart

    return redirect("/")


@app.route("/place-order", methods=["POST"])
def place_order():

    global order_number

    cart = session.get("cart", [])

    if not cart:
        return redirect("/")

    total = sum(item["total"] for item in cart)

    new_order = {
        "id": order_number,
        "customer": session.get("customer", "Customer"),
        "table": session.get("table", "N/A"),
        "items": cart,
        "total": total,
        "status": "NEW"
    }

    orders.append(new_order)

    order_number += 1

    session["cart"] = []

    return render_template_string(
        HTML,
        page="success",
        order=new_order
    )


@app.route("/kitchen")
def kitchen():

    return render_template_string(
        HTML,
        page="kitchen",
        orders=orders
    )


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )

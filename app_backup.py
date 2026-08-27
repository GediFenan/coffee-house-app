from flask import Flask, request, redirect, render_template_string

app = Flask(__name__)

orders = []

menu = [
    {"name": "Ethiopian Coffee", "price": 40},
    {"name": "Macchiato", "price": 50},
    {"name": "Tea", "price": 30},
    {"name": "Espresso", "price": 45},
    {"name": "Cappuccino", "price": 60}
]

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Coffee House</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

    <style>
        body {
            font-family: Arial;
            background: #f5f1eb;
            padding: 20px;
        }

        h1 {
            text-align: center;
            color: #6f4e37;
        }

        .item {
            background: white;
            padding: 20px;
            margin: 15px 0;
            border-radius: 15px;
        }

        button {
            background: #6f4e37;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
        }

        input {
            padding: 12px;
            margin: 5px;
            width: 90%;
        }
    </style>
</head>

<body>

<h1>☕ My Coffee House</h1>

{% if page == "menu" %}

<h2>Menu</h2>

{% for item in menu %}

<div class="item">

    <h3>{{ item.name }}</h3>

    <p>{{ item.price }} ETB</p>

    <form method="POST" action="/order">

        <input
            type="hidden"
            name="item"
            value="{{ item.name }}">

        <input
            type="hidden"
            name="price"
            value="{{ item.price }}">

        <input
            type="text"
            name="customer"
            placeholder="Your name"
            required>

        <input
            type="number"
            name="quantity"
            value="1"
            min="1"
            max="20">

        <button type="submit">
            🛒 Order
        </button>

    </form>

</div>

{% endfor %}

{% elif page == "success" %}

<h1>✅ Order Sent!</h1>

<h2>Thank you {{ customer }}!</h2>

<p>
{{ quantity }} × {{ item }}
</p>

<p>
Total: {{ total }} ETB
</p>

<a href="/">
    ← Order Again
</a>

{% elif page == "kitchen" %}

<h1>👨‍🍳 Kitchen</h1>

{% if orders %}

{% for order in orders %}

<div class="item">

    <h3>Order #{{ loop.index }}</h3>

    <p>Customer: {{ order.customer }}</p>

    <p>
        {{ order.quantity }} ×
        {{ order.item }}
    </p>

    <p>
        Total: {{ order.total }} ETB
    </p>

</div>

{% endfor %}

{% else %}

<h2>No orders yet ☕</h2>

{% endif %}

<a href="/">
    ← Customer Menu
</a>

{% endif %}

</body>
</html>
"""


@app.route("/")
def home():

    return render_template_string(
        HTML,
        page="menu",
        menu=menu
    )


@app.route("/order", methods=["POST"])
def order():

    customer = request.form["customer"]
    item = request.form["item"]

    price = float(request.form["price"])

    quantity = int(request.form["quantity"])

    total = price * quantity

    orders.append({
        "customer": customer,
        "item": item,
        "quantity": quantity,
        "total": total
    })

    return render_template_string(
        HTML,
        page="success",
        customer=customer,
        item=item,
        quantity=quantity,
        total=total
    )


@app.route("/kitchen")
def kitchen():

    return render_template_string(
        HTML,
        page="kitchen",
        orders=orders
    )


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )

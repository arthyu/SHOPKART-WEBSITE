from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import requests

app = Flask(__name__)
app.secret_key = "shopkart-frontend-secret"

API_BASE = "http://localhost:8000"

def api_get(path, token=None, params=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = requests.get(f"{API_BASE}{path}", headers=headers, params=params)
        return r.json(), r.status_code
    except:
        return {"detail": "Server unreachable"}, 500

def api_post(path, data, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = requests.post(f"{API_BASE}{path}", json=data, headers=headers)
        return r.json(), r.status_code
    except:
        return {"detail": "Server unreachable"}, 500

def api_put(path, data, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = requests.put(f"{API_BASE}{path}", json=data, headers=headers)
        return r.json(), r.status_code
    except:
        return {"detail": "Server unreachable"}, 500

def api_delete(path, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = requests.delete(f"{API_BASE}{path}", headers=headers)
        return r.json(), r.status_code
    except:
        return {"detail": "Server unreachable"}, 500

# ── Auth ──────────────────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = {"name": request.form["name"], "email": request.form["email"], "password": request.form["password"]}
        res, code = api_post("/register", data)
        if code == 200:
            session["pending_email"] = data["email"]
            flash("OTP sent to your email!", "success")
            return redirect(url_for("verify_otp"))
        flash(res.get("detail", "Registration failed"), "error")
    return render_template("register.html")

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        data = {"email": session.get("pending_email"), "otp": request.form["otp"]}
        res, code = api_post("/verify-otp", data)
        if code == 200:
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        flash(res.get("detail", "OTP verification failed"), "error")
    return render_template("verify_otp.html", email=session.get("pending_email", ""))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = {"email": request.form["email"], "password": request.form["password"]}
        res, code = api_post("/login", data)
        if code == 200:
            session["token"] = res["token"]
            session["user_name"] = res["name"]
            session["user_role"] = res["role"]
            session["user_id"] = res["user_id"]
            flash(f"Welcome back, {res['name']}!", "success")
            return redirect(url_for("admin_dashboard") if res["role"] == "admin" else url_for("index"))
        flash(res.get("detail", "Login failed"), "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))

# ── Public Pages ──────────────────────────────────────────────────

@app.route("/")
def index():
    token = session.get("token")
    categories, _ = api_get("/categories")
    search = request.args.get("search", "")
    category_id = request.args.get("category_id", "")
    min_price = request.args.get("min_price", "")
    max_price = request.args.get("max_price", "")

    params = {}
    if search:      params["search"] = search
    if category_id: params["category_id"] = category_id
    if min_price:   params["min_price"] = min_price
    if max_price:   params["max_price"] = max_price

    products, _ = api_get("/products", params=params)
    if not isinstance(products, list): products = []
    if not isinstance(categories, list): categories = []

    cart_count = 0
    if token:
        cart, _ = api_get("/cart", token=token)
        cart_count = cart.get("count", 0) if isinstance(cart, dict) else 0

    return render_template("index.html", products=products, categories=categories,
                           search=search, category_id=category_id,
                           min_price=min_price, max_price=max_price, cart_count=cart_count)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    token = session.get("token")
    product, code = api_get(f"/products/{product_id}")
    if code != 200:
        flash("Product not found.", "error")
        return redirect(url_for("index"))
    reviews, _ = api_get(f"/reviews/{product_id}")
    if not isinstance(reviews, list): reviews = []

    cart_count = 0
    if token:
        cart, _ = api_get("/cart", token=token)
        cart_count = cart.get("count", 0) if isinstance(cart, dict) else 0

    return render_template("product_detail.html", product=product, reviews=reviews, cart_count=cart_count)

# ── Cart ──────────────────────────────────────────────────────────

@app.route("/cart")
def cart():
    token = session.get("token")
    if not token:
        flash("Please login to view your cart.", "error")
        return redirect(url_for("login"))
    cart, _ = api_get("/cart", token=token)
    if not isinstance(cart, dict): cart = {"items": [], "total": 0, "count": 0}
    return render_template("cart.html", cart=cart)

@app.route("/cart/add", methods=["POST"])
def add_to_cart():
    token = session.get("token")
    if not token:
        flash("Please login to add items to cart.", "error")
        return redirect(url_for("login"))
    data = {"product_id": int(request.form["product_id"]), "quantity": int(request.form.get("quantity", 1))}
    res, code = api_post("/cart", data, token=token)
    if code == 200:
        flash("Added to cart!", "success")
    else:
        flash(res.get("detail", "Could not add to cart"), "error")
    return redirect(request.referrer or url_for("index"))

@app.route("/cart/update/<int:cart_id>", methods=["POST"])
def update_cart(cart_id):
    token = session.get("token")
    data = {"quantity": int(request.form["quantity"])}
    api_put(f"/cart/{cart_id}", data, token=token)
    return redirect(url_for("cart"))

@app.route("/cart/remove/<int:cart_id>")
def remove_from_cart(cart_id):
    token = session.get("token")
    api_delete(f"/cart/{cart_id}", token=token)
    flash("Item removed.", "success")
    return redirect(url_for("cart"))

# ── Orders ────────────────────────────────────────────────────────

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    token = session.get("token")
    if not token:
        flash("Please login to checkout.", "error")
        return redirect(url_for("login"))

    cart, _ = api_get("/cart", token=token)
    if not isinstance(cart, dict) or not cart.get("items"):
        flash("Your cart is empty.", "error")
        return redirect(url_for("cart"))

    me, _ = api_get("/me", token=token)

    if request.method == "POST":
        data = {"address": request.form["address"]}
        res, code = api_post("/orders", data, token=token)
        if code == 200:
            flash(f"Order #{res['order_id']} placed successfully!", "success")
            return redirect(url_for("orders"))
        flash(res.get("detail", "Order failed"), "error")

    return render_template("checkout.html", cart=cart, me=me)

@app.route("/orders")
def orders():
    token = session.get("token")
    if not token:
        return redirect(url_for("login"))
    orders, _ = api_get("/orders", token=token)
    if not isinstance(orders, list): orders = []
    return render_template("orders.html", orders=orders)

@app.route("/orders/<int:order_id>")
def order_detail(order_id):
    token = session.get("token")
    if not token:
        return redirect(url_for("login"))
    order, code = api_get(f"/orders/{order_id}", token=token)
    if code != 200:
        flash("Order not found.", "error")
        return redirect(url_for("orders"))
    return render_template("order_detail.html", order=order)

# ── Profile ───────────────────────────────────────────────────────

@app.route("/profile", methods=["GET", "POST"])
def profile():
    token = session.get("token")
    if not token:
        return redirect(url_for("login"))
    me, _ = api_get("/me", token=token)
    if request.method == "POST":
        data = {}
        if request.form.get("name"):     data["name"] = request.form["name"]
        if request.form.get("phone"):    data["phone"] = request.form["phone"]
        if request.form.get("address"):  data["address"] = request.form["address"]
        if request.form.get("password"): data["password"] = request.form["password"]
        res, code = api_put("/me", data, token=token)
        if code == 200:
            session["user_name"] = data.get("name", session["user_name"])
            flash("Profile updated!", "success")
        else:
            flash(res.get("detail", "Update failed"), "error")
        return redirect(url_for("profile"))
    return render_template("profile.html", me=me)

# ── Reviews ───────────────────────────────────────────────────────

@app.route("/reviews/add", methods=["POST"])
def add_review():
    token = session.get("token")
    if not token:
        flash("Please login to review.", "error")
        return redirect(url_for("login"))
    data = {
        "product_id": int(request.form["product_id"]),
        "rating":     int(request.form["rating"]),
        "comment":    request.form.get("comment", "")
    }
    res, code = api_post("/reviews", data, token=token)
    if code == 200:
        flash("Review submitted!", "success")
    else:
        flash(res.get("detail", "Could not submit review"), "error")
    return redirect(url_for("product_detail", product_id=data["product_id"]))

@app.route("/reviews/delete/<int:review_id>/<int:product_id>")
def delete_review(review_id, product_id):
    token = session.get("token")
    api_delete(f"/reviews/{review_id}", token=token)
    flash("Review deleted.", "success")
    return redirect(url_for("product_detail", product_id=product_id))

# ── Admin ─────────────────────────────────────────────────────────

@app.route("/admin")
def admin_dashboard():
    token = session.get("token")
    if session.get("user_role") != "admin":
        flash("Admins only.", "error")
        return redirect(url_for("index"))
    orders, _ = api_get("/admin/orders", token=token)
    users, _  = api_get("/users", token=token)
    products, _ = api_get("/products")
    if not isinstance(orders, list): orders = []
    if not isinstance(users, list): users = []
    if not isinstance(products, list): products = []
    return render_template("admin/dashboard.html", orders=orders, users=users, products=products)

@app.route("/admin/products", methods=["GET", "POST"])
def admin_products():
    token = session.get("token")
    if session.get("user_role") != "admin":
        return redirect(url_for("index"))
    categories, _ = api_get("/categories")
    if not isinstance(categories, list): categories = []
    if request.method == "POST":
        data = {
            "name":           request.form["name"],
            "description":    request.form.get("description"),
            "price":          float(request.form["price"]),
            "discount_price": float(request.form["discount_price"]) if request.form.get("discount_price") else None,
            "stock":          int(request.form["stock"]),
            "image":          request.form.get("image"),
            "category_id":    int(request.form["category_id"]) if request.form.get("category_id") else None,
        }
        res, code = api_post("/products", data, token=token)
        flash("Product added!" if code == 200 else res.get("detail", "Failed"), "success" if code == 200 else "error")
        return redirect(url_for("admin_products"))
    products, _ = api_get("/products")
    if not isinstance(products, list): products = []
    return render_template("admin/products.html", products=products, categories=categories)

@app.route("/admin/products/delete/<int:product_id>")
def admin_delete_product(product_id):
    token = session.get("token")
    if session.get("user_role") != "admin": return redirect(url_for("index"))
    api_delete(f"/products/{product_id}", token=token)
    flash("Product deleted.", "success")
    return redirect(url_for("admin_products"))

@app.route("/admin/categories", methods=["GET", "POST"])
def admin_categories():
    token = session.get("token")
    if session.get("user_role") != "admin": return redirect(url_for("index"))
    if request.method == "POST":
        data = {"name": request.form["name"], "description": request.form.get("description")}
        res, code = api_post("/categories", data, token=token)
        flash("Category added!" if code == 200 else res.get("detail", "Failed"), "success" if code == 200 else "error")
        return redirect(url_for("admin_categories"))
    categories, _ = api_get("/categories")
    if not isinstance(categories, list): categories = []
    return render_template("admin/categories.html", categories=categories)

@app.route("/admin/categories/delete/<int:category_id>")
def admin_delete_category(category_id):
    token = session.get("token")
    if session.get("user_role") != "admin": return redirect(url_for("index"))
    api_delete(f"/categories/{category_id}", token=token)
    flash("Category deleted.", "success")
    return redirect(url_for("admin_categories"))

@app.route("/admin/orders/update/<int:order_id>", methods=["POST"])
def admin_update_order(order_id):
    token = session.get("token")
    if session.get("user_role") != "admin": return redirect(url_for("index"))
    data = {"status": request.form["status"]}
    api_put(f"/orders/{order_id}/status", data, token=token)
    flash("Order status updated.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/users/delete/<int:user_id>")
def admin_delete_user(user_id):
    token = session.get("token")
    if session.get("user_role") != "admin": return redirect(url_for("index"))
    api_delete(f"/users/{user_id}", token=token)
    flash("User deleted.", "success")
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
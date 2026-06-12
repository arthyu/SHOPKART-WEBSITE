from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from jose import jwt, JWTError
from datetime import datetime, timedelta
import hashlib
import hmac
import random
from dotenv import load_dotenv
import os 

load_dotenv()
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
# ─── DATABASE ─────────────────────────────
DATABASE_URL = "mysql+pymysql://root:1234@localhost:3306/shopdb"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ─── JWT ──────────────────────────────────
SECRET_KEY = "your-super-secret-jwt-key"
ALGORITHM  = "HS256"

def create_token(user_id: int, email: str, role: str = "user") -> str:
    payload = {
        "sub":   str(user_id),
        "email": email,
        "role":  role,
        "exp":   datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return current_user

# ─── PASSWORD HASHING ─────────────────────
SECRET = "your-secret-key-here"

def hash_password(password: str) -> str:
    return hmac.new(SECRET.encode(), password.encode(), hashlib.sha256).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed

# ═══════════════════════════════════════════
#  MODELS
# ═══════════════════════════════════════════

class User(Base):
    __tablename__ = "users"
    user_id   = Column(Integer, primary_key=True, index=True)
    name      = Column(String(100))
    email     = Column(String(100), unique=True)
    password  = Column(String(255))
    phone     = Column(String(20), nullable=True)
    address   = Column(Text, nullable=True)
    verified  = Column(Integer, default=0)
    role      = Column(String(20), default="user")   # user / admin
    created_at = Column(DateTime, default=datetime.utcnow)
    cart      = relationship("Cart", back_populates="user")
    orders    = relationship("Order", back_populates="user")
    reviews   = relationship("Review", back_populates="user")


class OTPStore(Base):
    __tablename__ = "otps"
    id    = Column(Integer, primary_key=True)
    email = Column(String(100))
    otp   = Column(String(10))


class Category(Base):
    __tablename__ = "categories"
    category_id = Column(Integer, primary_key=True)
    name        = Column(String(100), unique=True)
    description = Column(String(255), nullable=True)
    products    = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    product_id     = Column(Integer, primary_key=True)
    name           = Column(String(200))
    description    = Column(Text, nullable=True)
    price          = Column(Float)
    discount_price = Column(Float, nullable=True)
    stock          = Column(Integer, default=0)
    image          = Column(String(255), nullable=True)
    category_id    = Column(Integer, ForeignKey("categories.category_id"))
    created_at     = Column(DateTime, default=datetime.utcnow)
    category       = relationship("Category", back_populates="products")
    cart_items     = relationship("Cart", back_populates="product")
    order_items    = relationship("OrderItem", back_populates="product")
    reviews        = relationship("Review", back_populates="product")


class Cart(Base):
    __tablename__ = "cart"
    cart_id    = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.user_id"))
    product_id = Column(Integer, ForeignKey("products.product_id"))
    quantity   = Column(Integer, default=1)
    user       = relationship("User", back_populates="cart")
    product    = relationship("Product", back_populates="cart_items")


class Order(Base):
    __tablename__ = "orders"
    order_id     = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.user_id"))
    total_amount = Column(Float)
    status       = Column(String(50), default="pending")
    address      = Column(Text)
    created_at   = Column(DateTime, default=datetime.utcnow)
    user         = relationship("User", back_populates="orders")
    items        = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    item_id    = Column(Integer, primary_key=True)
    order_id   = Column(Integer, ForeignKey("orders.order_id"))
    product_id = Column(Integer, ForeignKey("products.product_id"))
    quantity   = Column(Integer)
    price      = Column(Float)
    order      = relationship("Order", back_populates="items")
    product    = relationship("Product", back_populates="order_items")


class Review(Base):
    __tablename__ = "reviews"
    review_id  = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.user_id"))
    product_id = Column(Integer, ForeignKey("products.product_id"))
    rating     = Column(Integer)
    comment    = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user       = relationship("User", back_populates="reviews")
    product    = relationship("Product", back_populates="reviews")


Base.metadata.create_all(bind=engine)

# ─── EMAIL CONFIG ─────────────────────────
conf = ConnectionConfig(
    MAIL_USERNAME   = MAIL_USERNAME,    # ← your gmail
    MAIL_PASSWORD   = MAIL_PASSWORD,        # ← gmail app password
    MAIL_FROM       = MAIL_USERNAME,     # ← your gmail
    MAIL_PORT       = 587,
    MAIL_SERVER     = "smtp.gmail.com",
    MAIL_STARTTLS   = True,
    MAIL_SSL_TLS    = False,
    USE_CREDENTIALS = True
)

# ─── APP ──────────────────────────────────
app = FastAPI(title="Flipkart Clone API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════
#  AUTH ROUTES
# ═══════════════════════════════════════════

@app.post("/register")
async def register(data: dict):
    db       = SessionLocal()
    name     = data.get("name")
    email    = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        raise HTTPException(status_code=400, detail="All fields required")

    existing = db.query(User).filter(User.email == email).first()
    if existing and existing.verified == 1:
        raise HTTPException(status_code=400, detail="Email already registered")

    otp = str(random.randint(100000, 999999))

    if existing:
        existing.name     = name
        existing.password = hash_password(password)
        existing.verified = 0
        db.commit()
    else:
        db.add(User(name=name, email=email, password=hash_password(password), verified=0))
        db.commit()

    old = db.query(OTPStore).filter(OTPStore.email == email).first()
    if old:
        db.delete(old)
        db.commit()

    db.add(OTPStore(email=email, otp=otp))
    db.commit()

    await FastMail(conf).send_message(MessageSchema(
        subject    = "Your OTP — ShopBase",
        recipients = [email],
        body       = f"<h2>Hi {name}!</h2><h1 style='letter-spacing:8px;color:#2563eb;'>{otp}</h1><p>Enter this OTP to verify your email.</p>",
        subtype    = "html"
    ))
    return {"message": "OTP sent to your email"}


@app.post("/verify-otp")
def verify_otp(data: dict):
    db    = SessionLocal()
    email = data.get("email")
    otp   = data.get("otp")

    if not email or not otp:
        raise HTTPException(status_code=400, detail="Email and OTP required")

    stored = db.query(OTPStore).filter(OTPStore.email == email).first()
    if not stored:
        raise HTTPException(status_code=404, detail="OTP not found")
    if stored.otp != str(otp):
        raise HTTPException(status_code=401, detail="Incorrect OTP")

    user          = db.query(User).filter(User.email == email).first()
    user.verified = 1
    db.commit()
    db.delete(stored)
    db.commit()

    return {"message": "Registration successful!", "user_id": user.user_id, "name": user.name}


@app.post("/login")
def login(data: dict):
    db       = SessionLocal()
    email    = data.get("email")
    password = data.get("password")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.verified == 0:
        raise HTTPException(status_code=401, detail="Email not verified")
    if not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Incorrect password")

    token = create_token(user.user_id, user.email, user.role)
    return {
        "message": "Login successful",
        "token":   token,
        "user_id": user.user_id,
        "name":    user.name,
        "email":   user.email,
        "role":    user.role
    }


# ═══════════════════════════════════════════
#  USER ROUTES
# ═══════════════════════════════════════════

@app.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    db   = SessionLocal()
    user = db.query(User).filter(User.user_id == int(current_user["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user.user_id, "name": user.name, "email": user.email, "phone": user.phone, "address": user.address, "role": user.role}


@app.put("/me")
def update_me(data: dict, current_user: dict = Depends(get_current_user)):
    db   = SessionLocal()
    user = db.query(User).filter(User.user_id == int(current_user["sub"])).first()
    if data.get("name"):    user.name    = data["name"]
    if data.get("phone"):   user.phone   = data["phone"]
    if data.get("address"): user.address = data["address"]
    if data.get("password"): user.password = hash_password(data["password"])
    db.commit()
    return {"message": "Profile updated"}


@app.get("/users")
def get_users(current_user: dict = Depends(get_admin_user)):
    db = SessionLocal()
    return [{"user_id": u.user_id, "name": u.name, "email": u.email, "role": u.role, "verified": u.verified} for u in db.query(User).all()]


@app.delete("/users/{user_id}")
def delete_user(user_id: int, current_user: dict = Depends(get_admin_user)):
    db   = SessionLocal()
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


# ═══════════════════════════════════════════
#  CATEGORY ROUTES
# ═══════════════════════════════════════════

@app.get("/categories")
def get_categories():
    db = SessionLocal()
    return [{"category_id": c.category_id, "name": c.name, "description": c.description} for c in db.query(Category).all()]


@app.post("/categories")
def create_category(data: dict, current_user: dict = Depends(get_admin_user)):
    db   = SessionLocal()
    name = data.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    if db.query(Category).filter(Category.name == name).first():
        raise HTTPException(status_code=400, detail="Category already exists")
    cat = Category(name=name, description=data.get("description"))
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"category_id": cat.category_id, "name": cat.name}


@app.put("/categories/{category_id}")
def update_category(category_id: int, data: dict, current_user: dict = Depends(get_admin_user)):
    db  = SessionLocal()
    cat = db.query(Category).filter(Category.category_id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    if data.get("name"):        cat.name        = data["name"]
    if data.get("description"): cat.description = data["description"]
    db.commit()
    return {"message": "Category updated"}


@app.delete("/categories/{category_id}")
def delete_category(category_id: int, current_user: dict = Depends(get_admin_user)):
    db  = SessionLocal()
    cat = db.query(Category).filter(Category.category_id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(cat)
    db.commit()
    return {"message": "Category deleted"}


# ═══════════════════════════════════════════
#  PRODUCT ROUTES
# ═══════════════════════════════════════════

@app.get("/products")
def get_products(category_id: int = None, search: str = None, min_price: float = None, max_price: float = None):
    db    = SessionLocal()
    query = db.query(Product)
    if category_id: query = query.filter(Product.category_id == category_id)
    if search:      query = query.filter(Product.name.ilike(f"%{search}%"))
    if min_price:   query = query.filter(Product.price >= min_price)
    if max_price:   query = query.filter(Product.price <= max_price)
    products = query.all()
    return [
        {
            "product_id":     p.product_id,
            "name":           p.name,
            "description":    p.description,
            "price":          p.price,
            "discount_price": p.discount_price,
            "stock":          p.stock,
            "image":          p.image,
            "category_id":    p.category_id,
            "category_name":  p.category.name if p.category else None
        }
        for p in products
    ]


@app.get("/products/{product_id}")
def get_product(product_id: int):
    db      = SessionLocal()
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    reviews = db.query(Review).filter(Review.product_id == product_id).all()
    avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0
    return {
        "product_id":     product.product_id,
        "name":           product.name,
        "description":    product.description,
        "price":          product.price,
        "discount_price": product.discount_price,
        "stock":          product.stock,
        "image":          product.image,
        "category_name":  product.category.name if product.category else None,
        "avg_rating":     avg_rating,
        "total_reviews":  len(reviews)
    }


@app.post("/products")
def create_product(data: dict, current_user: dict = Depends(get_admin_user)):
    db = SessionLocal()
    if not data.get("name") or not data.get("price"):
        raise HTTPException(status_code=400, detail="Name and price required")
    product = Product(
        name           = data["name"],
        description    = data.get("description"),
        price          = data["price"],
        discount_price = data.get("discount_price"),
        stock          = data.get("stock", 0),
        image          = data.get("image"),
        category_id    = data.get("category_id")
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return {"message": "Product created", "product_id": product.product_id}


@app.put("/products/{product_id}")
def update_product(product_id: int, data: dict, current_user: dict = Depends(get_admin_user)):
    db      = SessionLocal()
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field in ["name", "description", "price", "discount_price", "stock", "image", "category_id"]:
        if data.get(field) is not None:
            setattr(product, field, data[field])
    db.commit()
    return {"message": "Product updated"}


@app.delete("/products/{product_id}")
def delete_product(product_id: int, current_user: dict = Depends(get_admin_user)):
    db      = SessionLocal()
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted"}


# ═══════════════════════════════════════════
#  CART ROUTES
# ═══════════════════════════════════════════

@app.get("/cart")
def get_cart(current_user: dict = Depends(get_current_user)):
    db      = SessionLocal()
    user_id = int(current_user["sub"])
    items   = db.query(Cart).filter(Cart.user_id == user_id).all()
    result  = []
    total   = 0
    for item in items:
        price     = item.product.discount_price or item.product.price
        subtotal  = price * item.quantity
        total    += subtotal
        result.append({
            "cart_id":      item.cart_id,
            "product_id":   item.product_id,
            "product_name": item.product.name,
            "price":        price,
            "quantity":     item.quantity,
            "subtotal":     subtotal,
            "image":        item.product.image
        })
    return {"items": result, "total": total, "count": len(result)}


@app.post("/cart")
def add_to_cart(data: dict, current_user: dict = Depends(get_current_user)):
    db         = SessionLocal()
    user_id    = int(current_user["sub"])
    product_id = data.get("product_id")
    quantity   = data.get("quantity", 1)

    if not product_id:
        raise HTTPException(status_code=400, detail="Product ID required")

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock < quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    existing = db.query(Cart).filter(Cart.user_id == user_id, Cart.product_id == product_id).first()
    if existing:
        existing.quantity += quantity
    else:
        db.add(Cart(user_id=user_id, product_id=product_id, quantity=quantity))
    db.commit()
    return {"message": "Added to cart"}


@app.put("/cart/{cart_id}")
def update_cart(cart_id: int, data: dict, current_user: dict = Depends(get_current_user)):
    db   = SessionLocal()
    item = db.query(Cart).filter(Cart.cart_id == cart_id, Cart.user_id == int(current_user["sub"])).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if data.get("quantity", 0) <= 0:
        db.delete(item)
    else:
        item.quantity = data["quantity"]
    db.commit()
    return {"message": "Cart updated"}


@app.delete("/cart/{cart_id}")
def remove_from_cart(cart_id: int, current_user: dict = Depends(get_current_user)):
    db   = SessionLocal()
    item = db.query(Cart).filter(Cart.cart_id == cart_id, Cart.user_id == int(current_user["sub"])).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()
    return {"message": "Removed from cart"}


@app.delete("/cart")
def clear_cart(current_user: dict = Depends(get_current_user)):
    db      = SessionLocal()
    user_id = int(current_user["sub"])
    db.query(Cart).filter(Cart.user_id == user_id).delete()
    db.commit()
    return {"message": "Cart cleared"}


# ═══════════════════════════════════════════
#  ORDER ROUTES
# ═══════════════════════════════════════════

@app.post("/orders")
def place_order(data: dict, current_user: dict = Depends(get_current_user)):
    db      = SessionLocal()
    user_id = int(current_user["sub"])
    address = data.get("address")

    if not address:
        raise HTTPException(status_code=400, detail="Delivery address required")

    cart_items = db.query(Cart).filter(Cart.user_id == user_id).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total = sum((item.product.discount_price or item.product.price) * item.quantity for item in cart_items)

    order = Order(user_id=user_id, total_amount=total, address=address, status="pending")
    db.add(order)
    db.commit()
    db.refresh(order)

    for item in cart_items:
        price = item.product.discount_price or item.product.price
        db.add(OrderItem(order_id=order.order_id, product_id=item.product_id, quantity=item.quantity, price=price))
        item.product.stock -= item.quantity

    db.query(Cart).filter(Cart.user_id == user_id).delete()
    db.commit()

    return {"message": "Order placed successfully", "order_id": order.order_id, "total": total, "status": "pending"}


@app.get("/orders")
def get_my_orders(current_user: dict = Depends(get_current_user)):
    db      = SessionLocal()
    user_id = int(current_user["sub"])
    orders  = db.query(Order).filter(Order.user_id == user_id).all()
    return [
        {
            "order_id":     o.order_id,
            "total_amount": o.total_amount,
            "status":       o.status,
            "address":      o.address,
            "created_at":   str(o.created_at),
            "items": [
                {
                    "product_name": i.product.name,
                    "quantity":     i.quantity,
                    "price":        i.price
                }
                for i in o.items
            ]
        }
        for o in orders
    ]


@app.get("/orders/{order_id}")
def get_order(order_id: int, current_user: dict = Depends(get_current_user)):
    db    = SessionLocal()
    order = db.query(Order).filter(Order.order_id == order_id, Order.user_id == int(current_user["sub"])).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order_id":     order.order_id,
        "total_amount": order.total_amount,
        "status":       order.status,
        "address":      order.address,
        "created_at":   str(order.created_at),
        "items": [{"product_name": i.product.name, "quantity": i.quantity, "price": i.price} for i in order.items]
    }


@app.put("/orders/{order_id}/status")
def update_order_status(order_id: int, data: dict, current_user: dict = Depends(get_admin_user)):
    db     = SessionLocal()
    order  = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    valid_statuses = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
    if data.get("status") not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}")
    order.status = data["status"]
    db.commit()
    return {"message": f"Order status updated to {order.status}"}


@app.get("/admin/orders")
def get_all_orders(current_user: dict = Depends(get_admin_user)):
    db     = SessionLocal()
    orders = db.query(Order).all()
    return [
        {
            "order_id":     o.order_id,
            "user_name":    o.user.name,
            "total_amount": o.total_amount,
            "status":       o.status,
            "created_at":   str(o.created_at)
        }
        for o in orders
    ]


# ═══════════════════════════════════════════
#  REVIEW ROUTES
# ═══════════════════════════════════════════

@app.get("/reviews/{product_id}")
def get_reviews(product_id: int):
    db      = SessionLocal()
    reviews = db.query(Review).filter(Review.product_id == product_id).all()
    return [
        {
            "review_id":  r.review_id,
            "user_name":  r.user.name,
            "rating":     r.rating,
            "comment":    r.comment,
            "created_at": str(r.created_at)
        }
        for r in reviews
    ]


@app.post("/reviews")
def add_review(data: dict, current_user: dict = Depends(get_current_user)):
    db         = SessionLocal()
    user_id    = int(current_user["sub"])
    product_id = data.get("product_id")
    rating     = data.get("rating")

    if not product_id or not rating:
        raise HTTPException(status_code=400, detail="Product ID and rating required")
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    existing = db.query(Review).filter(Review.user_id == user_id, Review.product_id == product_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already reviewed this product")

    db.add(Review(user_id=user_id, product_id=product_id, rating=rating, comment=data.get("comment")))
    db.commit()
    return {"message": "Review added"}


@app.delete("/reviews/{review_id}")
def delete_review(review_id: int, current_user: dict = Depends(get_current_user)):
    db     = SessionLocal()
    review = db.query(Review).filter(Review.review_id == review_id, Review.user_id == int(current_user["sub"])).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(review)
    db.commit()
    return {"message": "Review deleted"}
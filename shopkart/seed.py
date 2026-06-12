import requests

BASE = "http://localhost:8000"

# ── 1. Create admin user ──────────────────────────────────────────
print("Creating admin user...")
r = requests.post(f"{BASE}/register", json={
    "name": "Admin",
    "email": "admin@shopkart.com",
    "password": "admin123"
})
print(" →", r.json())

# You'll need to verify OTP manually, OR we seed via direct DB insert below.
# Let's use direct SQLAlchemy instead so we skip OTP.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import hmac, hashlib, sys, os
sys.path.insert(0, os.path.dirname(__file__))

DATABASE_URL = "mysql+pymysql://root:1234@localhost:3306/shopdb"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

SECRET = "your-secret-key-here"

def hash_password(password):
    return hmac.new(SECRET.encode(), password.encode(), hashlib.sha256).hexdigest()

# ── Import models from your backend ──────────────────────────────
from shopkartt  import User, Category, Product, Base

Base.metadata.create_all(bind=engine)

# ── 2. Create admin user directly ────────────────────────────────
print("\nSeeding admin user...")
existing = db.query(User).filter(User.email == "admin@shopkart.com").first()
if existing:
    existing.verified = 1
    existing.role = "admin"
    existing.password = hash_password("admin123")
    db.commit()
    print(" → Updated existing admin user")
else:
    admin = User(
        name="Admin",
        email="admin@shopkart.com",
        password=hash_password("admin123"),
        verified=1,
        role="admin"
    )
    db.add(admin)
    db.commit()
    print(" → Admin created")

# ── 3. Create categories ──────────────────────────────────────────
print("\nSeeding categories...")
categories_data = [
    {"name": "Electronics",  "description": "Phones, laptops, gadgets and accessories"},
    {"name": "Fashion",      "description": "Clothing, footwear and accessories"},
    {"name": "Home & Kitchen","description": "Appliances, furniture and kitchenware"},
    {"name": "Books",        "description": "Bestsellers, textbooks and more"},
    {"name": "Sports",       "description": "Fitness equipment and sportswear"},
    {"name": "Beauty",       "description": "Skincare, makeup and personal care"},
]

cat_map = {}
for c in categories_data:
    existing = db.query(Category).filter(Category.name == c["name"]).first()
    if existing:
        cat_map[c["name"]] = existing.category_id
        print(f" → {c['name']} already exists")
    else:
        cat = Category(name=c["name"], description=c["description"])
        db.add(cat)
        db.commit()
        db.refresh(cat)
        cat_map[c["name"]] = cat.category_id
        print(f" → {c['name']} created (id={cat.category_id})")

# ── 4. Create products ────────────────────────────────────────────
print("\nSeeding products...")
products_data = [
    # Electronics
    {
        "name": "iPhone 15 Pro",
        "description": "Apple iPhone 15 Pro with A17 Pro chip, 48MP camera, titanium design.",
        "price": 134900, "discount_price": 124999, "stock": 25,
        "image": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=500",
        "category": "Electronics"
    },
    {
        "name": "Samsung Galaxy S24",
        "description": "Samsung flagship with Snapdragon 8 Gen 3, 200MP camera.",
        "price": 79999, "discount_price": 72999, "stock": 30,
        "image": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=500",
        "category": "Electronics"
    },
    {
        "name": "Sony WH-1000XM5 Headphones",
        "description": "Industry-leading noise cancelling wireless headphones.",
        "price": 29990, "discount_price": 24990, "stock": 50,
        "image": "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?w=500",
        "category": "Electronics"
    },
    {
        "name": "MacBook Air M2",
        "description": "Apple MacBook Air with M2 chip, 8GB RAM, 256GB SSD.",
        "price": 114900, "discount_price": 109900, "stock": 15,
        "image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=500",
        "category": "Electronics"
    },
    {
        "name": "boAt Rockerz 450",
        "description": "Wireless Bluetooth headphone with 15 hours battery backup.",
        "price": 1999, "discount_price": 1499, "stock": 100,
        "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500",
        "category": "Electronics"
    },
    # Fashion
    {
        "name": "Nike Air Max 270",
        "description": "Nike Air Max 270 running shoes with max air cushioning.",
        "price": 12995, "discount_price": 9999, "stock": 40,
        "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500",
        "category": "Fashion"
    },
    {
        "name": "Levi's 511 Slim Jeans",
        "description": "Classic slim fit jeans in stretch denim, versatile and comfortable.",
        "price": 3999, "discount_price": 2999, "stock": 60,
        "image": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500",
        "category": "Fashion"
    },
    {
        "name": "Men's Formal Shirt",
        "description": "Premium cotton formal shirt, wrinkle-resistant, slim fit.",
        "price": 1299, "discount_price": None, "stock": 80,
        "image": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=500",
        "category": "Fashion"
    },
    {
        "name": "Women's Kurta Set",
        "description": "Elegant cotton kurta with palazzo pants, perfect for casual and festive wear.",
        "price": 1899, "discount_price": 1499, "stock": 45,
        "image": "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=500",
        "category": "Fashion"
    },
    # Home & Kitchen
    {
        "name": "Instant Pot Duo 7-in-1",
        "description": "Electric pressure cooker, slow cooker, rice cooker, steamer and more.",
        "price": 8999, "discount_price": 6999, "stock": 20,
        "image": "https://images.unsplash.com/photo-1585515320310-259814833e62?w=500",
        "category": "Home & Kitchen"
    },
    {
        "name": "Philips Air Fryer",
        "description": "Digital air fryer with rapid air technology, 4.1L capacity.",
        "price": 9995, "discount_price": 7995, "stock": 18,
        "image": "https://images.unsplash.com/photo-1648146009897-7b060f010d95?w=500",
        "category": "Home & Kitchen"
    },
    {
        "name": "Wooden Dinner Set (6 pieces)",
        "description": "Handcrafted acacia wood dinner plates, eco-friendly and durable.",
        "price": 2499, "discount_price": None, "stock": 35,
        "image": "https://images.unsplash.com/photo-1603199506016-b9a594b593c0?w=500",
        "category": "Home & Kitchen"
    },
    # Books
    {
        "name": "Atomic Habits",
        "description": "By James Clear. Tiny changes, remarkable results — the #1 bestseller.",
        "price": 799, "discount_price": 499, "stock": 200,
        "image": "https://images.unsplash.com/photo-1589829085413-56de8ae18c73?w=500",
        "category": "Books"
    },
    {
        "name": "Rich Dad Poor Dad",
        "description": "By Robert Kiyosaki. What the rich teach their kids about money.",
        "price": 499, "discount_price": 349, "stock": 150,
        "image": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=500",
        "category": "Books"
    },
    {
        "name": "Python Crash Course",
        "description": "A hands-on, project-based introduction to programming by Eric Matthes.",
        "price": 999, "discount_price": 749, "stock": 75,
        "image": "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=500",
        "category": "Books"
    },
    # Sports
    {
        "name": "Yoga Mat Premium",
        "description": "Non-slip 6mm thick yoga mat with carrying strap, eco-friendly TPE.",
        "price": 1499, "discount_price": 999, "stock": 90,
        "image": "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=500",
        "category": "Sports"
    },
    {
        "name": "Adjustable Dumbbell Set",
        "description": "5–25kg adjustable dumbbells, space-saving home gym essential.",
        "price": 4999, "discount_price": 3999, "stock": 22,
        "image": "https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?w=500",
        "category": "Sports"
    },
    {
        "name": "Nivia Football",
        "description": "Official size 5 football, durable PU material, suitable for all surfaces.",
        "price": 899, "discount_price": None, "stock": 60,
        "image": "https://images.unsplash.com/photo-1614632537197-38a17061c2bd?w=500",
        "category": "Sports"
    },
    # Beauty
    {
        "name": "Lakme 9to5 Primer",
        "description": "Long-wear matte primer that controls oil and keeps makeup intact all day.",
        "price": 599, "discount_price": 449, "stock": 120,
        "image": "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=500",
        "category": "Beauty"
    },
    {
        "name": "Mamaearth Vitamin C Serum",
        "description": "Brightening face serum with Vitamin C and turmeric for glowing skin.",
        "price": 699, "discount_price": 524, "stock": 85,
        "image": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=500",
        "category": "Beauty"
    },
]

for p in products_data:
    existing = db.query(Product).filter(Product.name == p["name"]).first()
    if existing:
        print(f" → {p['name']} already exists, skipping")
        continue
    product = Product(
        name           = p["name"],
        description    = p["description"],
        price          = p["price"],
        discount_price = p["discount_price"],
        stock          = p["stock"],
        image          = p["image"],
        category_id    = cat_map[p["category"]]
    )
    db.add(product)
    db.commit()
    print(f" → {p['name']} added")

print("\n✅ Seeding complete!")
print("\n👤 Admin login:")
print("   Email   : admin@shopkart.com")
print("   Password: admin123")
print("\n🌐 Open http://localhost:5000")

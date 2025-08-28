import os, sqlite3, json, time
from pathlib import Path

DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/app.db")
DB_PATH = Path(DB_URL.split("///", 1)[1]).resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY,
  tg_user_id INTEGER UNIQUE NOT NULL,
  full_name TEXT,
  phone TEXT,
  email TEXT,
  referral_code TEXT,
  created_at INTEGER
);
CREATE TABLE IF NOT EXISTS agreements(
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  policy_version TEXT NOT NULL,
  agreed_at INTEGER NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS products(
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  price_cents INTEGER NOT NULL,
  description TEXT
);
CREATE TABLE IF NOT EXISTS product_images(
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL,
  url TEXT NOT NULL,
  FOREIGN KEY(product_id) REFERENCES products(id)
);
CREATE TABLE IF NOT EXISTS carts(
  id INTEGER PRIMARY KEY,
  user_id INTEGER UNIQUE NOT NULL,
  updated_at INTEGER,
  FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS cart_items(
  id INTEGER PRIMARY KEY,
  cart_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  qty INTEGER NOT NULL,
  UNIQUE(cart_id, product_id),
  FOREIGN KEY(cart_id) REFERENCES carts(id),
  FOREIGN KEY(product_id) REFERENCES products(id)
);
CREATE TABLE IF NOT EXISTS orders(
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  number TEXT UNIQUE NOT NULL,
  status TEXT NOT NULL,
  address TEXT,
  delivery_method TEXT,
  total_cents INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS order_items(
  id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  price_cents INTEGER NOT NULL,
  qty INTEGER NOT NULL,
  FOREIGN KEY(order_id) REFERENCES orders(id),
  FOREIGN KEY(product_id) REFERENCES products(id)
);
"""

SEED = [
  {"title": "Rumus Protein 750g", "price_cents": 199900, "description": "Сывороточный протеин 750 г", "images": ["/static/img/p1.jpg"]},
  {"title": "Rumus BCAA 300g", "price_cents": 149900, "description": "BCAA 2:1:1 300 г", "images": ["/static/img/p2.jpg"]},
  {"title": "Rumus Creatine 300g", "price_cents": 129900, "description": "Креатин моногидрат 300 г", "images": ["/static/img/p3.jpg"]},
]

def connect():
  conn = sqlite3.connect(DB_PATH, check_same_thread=False)
  conn.row_factory = sqlite3.Row
  return conn

def init_db():
  conn = connect()
  with conn:
    for stmt in SCHEMA_SQL.split(";"):
      s = stmt.strip()
      if s:
        conn.execute(s)
    # seed products if empty
    c = conn.execute("SELECT COUNT(*) as n FROM products").fetchone()["n"]
    if c == 0:
      for p in SEED:
        cur = conn.execute("INSERT INTO products(title,price_cents,description) VALUES(?,?,?)",
                           (p["title"], p["price_cents"], p.get("description")))
        pid = cur.lastrowid
        for u in p.get("images", []):
          conn.execute("INSERT INTO product_images(product_id,url) VALUES(?,?)",(pid,u))
  conn.close()

def now(): return int(time.time())

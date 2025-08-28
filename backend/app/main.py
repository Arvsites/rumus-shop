import os, httpx, random, string
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from pydantic import BaseModel
from .db import init_db, connect, now

app = FastAPI(title="Rumus Backend (MVP)")
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

init_db()

@app.get("/")
async def root():
    return RedirectResponse("/health", status_code=307)

@app.get("/health")
async def health():
    return {"status": "ok"}

# ==== Models ====
class RegisterIn(BaseModel):
    tg_user_id: int
    full_name: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    referral_code: Optional[str] = ""
    agreed: bool = False
    policy_version: str = "v1"

class ProductOut(BaseModel):
    id: int
    title: str
    price_cents: int
    description: Optional[str] = ""
    images: List[str] = []

class CartItemIn(BaseModel):
    product_id: int
    qty: int

class OrderCreateIn(BaseModel):
    tg_user_id: int
    address: str
    delivery_method: str = "pickup"  # or courier

# ==== Helpers ====
def ensure_user(conn, r: RegisterIn):
    u = conn.execute("SELECT * FROM users WHERE tg_user_id=?", (r.tg_user_id,)).fetchone()
    if u is None:
        conn.execute("""INSERT INTO users(tg_user_id,full_name,phone,email,referral_code,created_at)
                        VALUES(?,?,?,?,?,?)""",
                     (r.tg_user_id, r.full_name, r.phone, r.email, r.referral_code, now()))
        uid = conn.execute("SELECT id FROM users WHERE tg_user_id=?", (r.tg_user_id,)).fetchone()["id"]
        if r.agreed:
            conn.execute("INSERT INTO agreements(user_id,policy_version,agreed_at) VALUES(?,?,?)",
                         (uid, r.policy_version, now()))
        conn.execute("INSERT OR IGNORE INTO carts(user_id,updated_at) VALUES(?,?)", (uid, now()))
        return uid
    else:
        uid = u["id"]
        conn.execute("""UPDATE users SET full_name=?, phone=?, email=?, referral_code=? WHERE id=?""",
                     (r.full_name, r.phone, r.email, r.referral_code, uid))
        if r.agreed:
            conn.execute("INSERT INTO agreements(user_id,policy_version,agreed_at) VALUES(?,?,?)",
                         (uid, r.policy_version, now()))
        return uid

def get_user_id(conn, tg_user_id:int)->int:
    row = conn.execute("SELECT id FROM users WHERE tg_user_id=?", (tg_user_id,)).fetchone()
    if not row: raise HTTPException(404, "User not found")
    return row["id"]

def order_number()->str:
    return "R" + "".join(random.choices(string.digits, k=8))

async def notify_chat(chat_id:int, text:str):
    async with httpx.AsyncClient(timeout=15) as cli:
        await cli.post(f"{TG_API}/sendMessage", data={"chat_id": chat_id, "text": text})

# ==== Auth/Registration ====
@app.post("/api/register")
async def register(body: RegisterIn):
    conn = connect()
    with conn:
        uid = ensure_user(conn, body)
    return {"ok": True, "user_id": uid}

# ==== Catalog ====
@app.get("/api/products", response_model=List[ProductOut])
async def products():
    conn = connect()
    rows = conn.execute("SELECT * FROM products").fetchall()
    out = []
    for r in rows:
        imgs = [i["url"] for i in conn.execute("SELECT url FROM product_images WHERE product_id=?", (r["id"],)).fetchall()]
        out.append(ProductOut(id=r["id"], title=r["title"], price_cents=r["price_cents"], description=r["description"], images=imgs))
    conn.close()
    return out

@app.get("/api/products/{pid}", response_model=ProductOut)
async def product(pid:int):
    conn = connect()
    r = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    if not r: raise HTTPException(404, "Not found")
    imgs = [i["url"] for i in conn.execute("SELECT url FROM product_images WHERE product_id=?", (pid,)).fetchall()]
    conn.close()
    return ProductOut(id=r["id"], title=r["title"], price_cents=r["price_cents"], description=r["description"], images=imgs)

# ==== Cart ====
@app.get("/api/cart/{tg_user_id}")
async def get_cart(tg_user_id:int):
    conn = connect()
    uid = get_user_id(conn, tg_user_id)
    cart = conn.execute("SELECT id FROM carts WHERE user_id=?", (uid,)).fetchone()
    if not cart:
        conn.execute("INSERT INTO carts(user_id,updated_at) VALUES(?,?)",(uid,now()))
        cart_id = conn.execute("SELECT id FROM carts WHERE user_id=?", (uid,)).fetchone()["id"]
    else:
        cart_id = cart["id"]
    items = conn.execute("""SELECT ci.id, ci.qty, p.id as product_id, p.title, p.price_cents
                            FROM cart_items ci
                            JOIN products p ON p.id = ci.product_id
                            WHERE ci.cart_id=?""", (cart_id,)).fetchall()
    total = sum(r["qty"]*r["price_cents"] for r in items)
    conn.close()
    return {"items":[{"id":r["id"],"product_id":r["product_id"],"title":r["title"],"price_cents":r["price_cents"],"qty":r["qty"]} for r in items],
            "total_cents": total}

@app.post("/api/cart/{tg_user_id}/items")
async def add_item(tg_user_id:int, body: CartItemIn):
    conn = connect()
    with conn:
        uid = get_user_id(conn, tg_user_id)
        cart_id = conn.execute("SELECT id FROM carts WHERE user_id=?", (uid,)).fetchone()["id"]
        prev = conn.execute("SELECT id, qty FROM cart_items WHERE cart_id=? AND product_id=?", (cart_id, body.product_id)).fetchone()
        if prev:
            conn.execute("UPDATE cart_items SET qty=? WHERE id=?", (max(1, body.qty), prev["id"]))
        else:
            conn.execute("INSERT INTO cart_items(cart_id,product_id,qty) VALUES(?,?,?)", (cart_id, body.product_id, max(1, body.qty)))
        conn.execute("UPDATE carts SET updated_at=? WHERE id=?", (now(), cart_id))
    return {"ok": True}

@app.patch("/api/cart/items/{item_id}")
async def patch_item(item_id:int, body: CartItemIn):
    conn = connect()
    with conn:
        conn.execute("UPDATE cart_items SET qty=? WHERE id=?", (max(1, body.qty), item_id))
    return {"ok": True}

@app.delete("/api/cart/items/{item_id}")
async def del_item(item_id:int):
    conn = connect()
    with conn:
        conn.execute("DELETE FROM cart_items WHERE id=?", (item_id,))
    return {"ok": True}

# ==== Orders & History ====
@app.post("/api/orders")
async def create_order(body: OrderCreateIn):
    conn = connect()
    with conn:
        uid = get_user_id(conn, body.tg_user_id)
        cart_id = conn.execute("SELECT id FROM carts WHERE user_id=?", (uid,)).fetchone()["id"]
        items = conn.execute("""SELECT p.id as product_id, p.title, p.price_cents, ci.qty
                                FROM cart_items ci JOIN products p ON p.id=ci.product_id
                                WHERE ci.cart_id=?""",(cart_id,)).fetchall()
        if not items:
            raise HTTPException(400, "Cart empty")
        total = sum(i["price_cents"]*i["qty"] for i in items)
        number = order_number()
        conn.execute("""INSERT INTO orders(user_id,number,status,address,delivery_method,total_cents,created_at)
                        VALUES(?,?,?,?,?,?,?)""", (uid, number, "awaiting_payment", body.address, body.delivery_method, total, now()))
        oid = conn.execute("SELECT id FROM orders WHERE number=?", (number,)).fetchone()["id"]
        for i in items:
            conn.execute("""INSERT INTO order_items(order_id,product_id,title,price_cents,qty)
                            VALUES(?,?,?,?,?)""", (oid, i["product_id"], i["title"], i["price_cents"], i["qty"]))
        conn.execute("DELETE FROM cart_items WHERE cart_id=?", (cart_id,))
    # notify in chat
    try:
        await notify_chat(body.tg_user_id, f"✅ Заказ {number} создан. Статус: Ожидает оплаты.")
    except Exception:
        pass
    return {"ok": True, "order_number": number}

@app.get("/api/orders/{tg_user_id}")
async def list_orders(tg_user_id:int):
    conn = connect()
    uid = get_user_id(conn, tg_user_id)
    orders = conn.execute("""SELECT id, number, status, total_cents, created_at FROM orders 
                             WHERE user_id=? ORDER BY id DESC""",(uid,)).fetchall()
    out=[]
    for o in orders:
        items = conn.execute("""SELECT title, price_cents, qty FROM order_items WHERE order_id=?""",(o["id"],)).fetchall()
        out.append({"number":o["number"], "status":o["status"], "total_cents":o["total_cents"], "created_at":o["created_at"],
                    "items":[{"title":i["title"],"price_cents":i["price_cents"],"qty":i["qty"]} for i in items]})
    conn.close()
    return out

# === Existing endpoints kept for MiniApp data bridge ===
class InlineAnswerIn(BaseModel):
    query_id: str
    data: dict

class DirectMessageIn(BaseModel):
    chat_id: int
    text: str

@app.post("/api/inline_answer")
async def inline_answer(body: InlineAnswerIn):
    async with httpx.AsyncClient(timeout=15) as cli:
        r = await cli.post(
            f"{TG_API}/answerWebAppQuery",
            data={
                "web_app_query_id": body.query_id,
                "result": {
                    "type": "article","id": "miniapp-result","title": "MiniApp response",
                    "input_message_content": {"message_text": f"📦 {body.data}"},
                },
            },
        )
    if r.status_code != 200:
        raise HTTPException(502, r.text)
    return JSONResponse(r.json())

@app.post("/api/send_message")
async def send_message(body: DirectMessageIn):
    async with httpx.AsyncClient(timeout=15) as cli:
        r = await cli.post(f"{TG_API}/sendMessage", data={"chat_id": body.chat_id, "text": body.text})
    if r.status_code != 200:
        raise HTTPException(502, r.text)
    return JSONResponse(r.json())

import logging
import os
from psycopg2 import pool, extras

# ----------------- НАСТРОЙКИ -----------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL не задана. Проверь переменные окружения.")

connection_pool = pool.SimpleConnectionPool(
    1,
    20,
    DATABASE_URL
)

def get_connection():
    return connection_pool.getconn()

def release_connection(conn):
    connection_pool.putconn(conn)


# ----------------- СОЗДАНИЕ ТАБЛИЦ -----------------

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sellers (
        id SERIAL PRIMARY KEY,
        tg_id BIGINT UNIQUE,
        shop_name TEXT UNIQUE,
        is_active INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS buyers (
        id SERIAL PRIMARY KEY,
        tg_id BIGINT UNIQUE,
        shop_name TEXT,
        address TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id SERIAL PRIMARY KEY,
        seller_id INTEGER REFERENCES sellers(id) ON DELETE CASCADE,
        name TEXT,
        UNIQUE(seller_id, name)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        seller_id INTEGER REFERENCES sellers(id) ON DELETE CASCADE,
        category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
        name TEXT,
        amount TEXT,
        price NUMERIC,
        stock INTEGER,
        image TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        buyer_tg BIGINT,
        seller_id INTEGER REFERENCES sellers(id) ON DELETE CASCADE,
        address TEXT,
        total_amount NUMERIC,
        status TEXT DEFAULT 'new',
        created_at TIMESTAMP DEFAULT NOW()
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(id),
        product_name TEXT,
        price NUMERIC,
        quantity INTEGER,
        total_price NUMERIC,
        amount TEXT
    )
    """)

    conn.commit()
    cur.close()
    release_connection(conn)
    logging.info("✅ Tables created")


def delete_seller_full(tg_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE sellers
            SET is_active = 0
            WHERE tg_id = %s
        """, (tg_id,))

        updated = cur.rowcount

        conn.commit()

        if updated == 0:
            return False

        return True

    except Exception as e:
        conn.rollback()
        logging.error(f"❌ delete_seller_full: {e}")
        return False

    finally:
        cur.close()
        release_connection(conn)


# ----------------- ПРОДАВЦЫ -----------------

def add_seller(tg_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO sellers (tg_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (tg_id,)
        )
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"❌ add_seller: {e}")
        return False
    finally:
        cur.close()
        release_connection(conn)


def set_shop_name(tg_id, shop_name):
    conn = get_connection()
    cur = conn.cursor()

    try:
        name = shop_name.strip().capitalize()

        cur.execute(
            "UPDATE sellers SET shop_name=%s WHERE tg_id=%s",
            (name, tg_id)
        )

        conn.commit()

    except Exception as e:
        logging.error(f"❌ set_shop_name: {e}")

    finally:
        cur.close()
        release_connection(conn)


def get_seller(tg_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("SELECT * FROM sellers WHERE tg_id=%s", (tg_id,))
    result = cur.fetchone()

    cur.close()
    release_connection(conn)
    return result


def get_all_buyers():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    try:
        cur.execute("""
            SELECT tg_id, shop_name, address
            FROM buyers
        """)
        return cur.fetchall()
    finally:
        cur.close()
        release_connection(conn)


def get_all_sellers():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    try:
        cur.execute("SELECT * FROM sellers")
        result = cur.fetchall()
        return result

    finally:
        cur.close()
        release_connection(conn)


def get_seller_by_id(seller_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("SELECT * FROM sellers WHERE id=%s", (seller_id,))
    result = cur.fetchone()

    cur.close()
    release_connection(conn)
    return result


def activate_seller(tg_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("UPDATE sellers SET is_active=1 WHERE tg_id=%s", (tg_id,))
    conn.commit()

    cur.close()
    release_connection(conn)


def deactivate_seller(tg_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("UPDATE sellers SET is_active=0 WHERE tg_id=%s", (tg_id,))
    conn.commit()

    cur.close()
    release_connection(conn)


def get_all_shops():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("SELECT id, shop_name FROM sellers WHERE is_active=1")
    result = cur.fetchall()

    cur.close()
    release_connection(conn)
    return result

# ----------------- ПОКУПАТЕЛИ -----------------

def add_buyer(tg_id: int, shop_name: str, address: str):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO buyers (tg_id, shop_name, address)
            VALUES (%s, %s, %s)
            ON CONFLICT (tg_id) DO UPDATE
            SET shop_name = EXCLUDED.shop_name,
                address = EXCLUDED.address
        """, (tg_id, shop_name, address))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"❌ add_buyer: {e}")
        return False
    finally:
        cur.close()
        release_connection(conn)


def get_buyer(tg_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute("SELECT * FROM buyers WHERE tg_id=%s", (tg_id,))
    result = cur.fetchone()
    cur.close()
    release_connection(conn)
    return result


def get_buyer_orders(buyer_tg: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    try:
        cur.execute("""
            SELECT 
                o.id AS order_id,
                o.address,
                o.status,
                o.total_amount,
                o.created_at,
                o.seller_id,
                oi.product_id,
                oi.product_name,
                oi.price,
                oi.quantity,
                oi.total_price
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            WHERE o.buyer_tg = %s
            ORDER BY o.id DESC
        """, (buyer_tg,))
        return cur.fetchall()
    finally:
        cur.close()
        release_connection(conn)


def update_buyer_name(tg_id, new_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE buyers SET shop_name=%s WHERE tg_id=%s",
        (new_name, tg_id)
    )
    conn.commit()
    cur.close()
    release_connection(conn)


def update_buyer_address(tg_id, new_address):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE buyers SET address=%s WHERE tg_id=%s",
        (new_address, tg_id)
    )
    conn.commit()
    cur.close()
    release_connection(conn)


# ----------------- КАТЕГОРИИ -----------------

def add_category(seller_id, name):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO categories (seller_id, name)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """, (seller_id, name.strip()))

    conn.commit()
    cur.close()
    release_connection(conn)


def get_categories(seller_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("""
        SELECT id, name
        FROM categories
        WHERE seller_id=%s
    """, (seller_id,))

    result = cur.fetchall()

    cur.close()
    release_connection(conn)
    return result


def delete_category(cat_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "DELETE FROM products WHERE category_id=%s",
            (cat_id,)
        )

        cur.execute(
            "DELETE FROM categories WHERE id=%s",
            (cat_id,)
        )

        conn.commit()

    except Exception as e:
        logging.error(f"❌ delete_category: {e}")

    finally:
        cur.close()
        release_connection(conn)


# ----------------- ТОВАРЫ -----------------

def add_product_full(seller_id, category_id, name, amount, price, stock, image):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO products
        (seller_id, category_id, name, amount, price, stock, image)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (seller_id, category_id, name, amount, price, stock, image))

    conn.commit()
    cur.close()
    release_connection(conn)


def get_products_full_by_seller(seller_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("""
        SELECT id, name, amount, price, stock, image, category_id
        FROM products
        WHERE seller_id=%s
        ORDER BY id DESC
    """, (seller_id,))

    result = cur.fetchall()

    cur.close()
    release_connection(conn)
    return result


def get_product(product_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("SELECT * FROM products WHERE id=%s", (product_id,))
    result = cur.fetchone()

    cur.close()
    release_connection(conn)
    return result


def get_product_by_name_and_seller(name, seller_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute(
        "SELECT * FROM products WHERE name=%s AND seller_id=%s",
        (name, seller_id)
    )

    result = cur.fetchone()

    cur.close()
    release_connection(conn)

    return result


def delete_product_by_id(product_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "DELETE FROM products WHERE id=%s",
            (product_id,)
        )

        conn.commit()

    except Exception as e:
        logging.error(f"❌ delete_product: {e}")

    finally:
        cur.close()
        release_connection(conn)


def update_product_field(pid: int, field: str, value):

    allowed = ["name", "amount", "price", "stock", "image"]

    if field not in allowed:
        return False

    conn = get_connection()
    cur = conn.cursor()

    try:
        query = f"UPDATE products SET {field}=%s WHERE id=%s"
        cur.execute(query, (value, pid))

        conn.commit()
        return True

    except Exception as e:
        logging.error(f"❌ update_product_field: {e}")
        return False

    finally:
        cur.close()
        release_connection(conn)


def search_products_by_name(shop_id, query):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute("""
        SELECT *
        FROM products
        WHERE seller_id=%s
        AND name ILIKE %s
    """, (shop_id, f"%{query}%"))

    result = cur.fetchall()

    cur.close()
    release_connection(conn)
    return result


# ----------------- ЗАКАЗЫ -----------------

def create_order_full(buyer_tg, seller_id, cart, address):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    try:
        total_sum = 0
        products_data = {} 

        product_ids = [item["product_id"] for item in cart]
        cur.execute(
            "SELECT id, name, price, amount FROM products WHERE id = ANY(%s)",
            (product_ids,)
        )
        for p in cur.fetchall():
            products_data[p["id"]] = p

        for item in cart:
            product = products_data.get(item["product_id"])
            if not product:
                continue
            total_sum += float(product["price"]) * float(item["amount"])

        cur.execute("""
            INSERT INTO orders (buyer_tg, seller_id, address, total_amount)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (buyer_tg, seller_id, address, total_sum))
        order_id = cur.fetchone()["id"]

        for item in cart:
            product = products_data.get(item["product_id"])
            if not product:
                continue

            quantity = float(item["amount"])
            price = float(product["price"])
            total_price = quantity * price
            amount = product["amount"]

            cur.execute("""
                INSERT INTO order_items
                (order_id, product_id, product_name, price, quantity, total_price, amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                order_id,
                product["id"],
                product["name"],
                price,
                quantity,
                total_price,
                amount
            ))

        conn.commit()
        return order_id

    except Exception as e:
        conn.rollback()
        logging.error(f"❌ create_order_full: {e}")
        return None

    finally:
        cur.close()
        release_connection(conn)


def accept_order_atomic(order_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    try:
        cur.execute("SELECT * FROM orders WHERE id=%s FOR UPDATE", (order_id,))
        order = cur.fetchone()

        if not order or order["status"] != "new":
            return None

        cur.execute("SELECT * FROM order_items WHERE order_id=%s", (order_id,))
        items = cur.fetchall()

        for item in items:
            cur.execute("SELECT stock FROM products WHERE id=%s FOR UPDATE", (item["product_id"],))
            stock = cur.fetchone()["stock"]
            if stock < item["quantity"]:
                conn.rollback()
                return "not_enough_stock"

        for item in items:
            cur.execute("UPDATE products SET stock = stock - %s WHERE id=%s", (item["quantity"], item["product_id"]))

        cur.execute("UPDATE orders SET status='принятый' WHERE id=%s", (order_id,))

        cur.execute("SELECT shop_name, address FROM buyers WHERE tg_id=%s", (order["buyer_tg"],))
        buyer = cur.fetchone()

        cur.execute("SELECT shop_name FROM sellers WHERE id=%s", (order["seller_id"],))
        seller = cur.fetchone()

        conn.commit()

        return {
            **order,    
            "buyer_shop": buyer["shop_name"] if buyer else str(order["buyer_tg"]),
            "buyer_address": buyer["address"] if buyer else order["address"],
            "seller_shop": seller["shop_name"] if seller else str(order["seller_id"]),
            "items": items
        }

    except Exception as e:
        conn.rollback()
        logging.error(f"❌ accept_order_atomic: {e}")
        return None

    finally:
        cur.close()
        release_connection(conn)


def get_seller_orders(seller_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    try:
        cur.execute("""
            SELECT 
                o.id AS order_id,
                o.address,
                o.status,
                o.total_amount,
                oi.product_id,
                oi.product_name,
                oi.price,
                oi.quantity,
                oi.total_price
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            WHERE o.seller_id = %s
            ORDER BY o.id DESC
        """, (seller_id,))
        result = cur.fetchall()
        return result

    finally:
        cur.close()
        release_connection(conn)


def get_order_items(order_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    cur.execute(
        "SELECT * FROM order_items WHERE order_id=%s",
        (order_id,)
    )

    result = cur.fetchall()

    cur.close()
    release_connection(conn)
    return result
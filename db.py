import sqlite3
import threading
import logging


# ----------------- НАСТРОЙКИ -----------------

DB_NAME = "shop.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# ----------------- БЛОКИРОВКА -----------------

lock = threading.Lock()


# ----------------- ПОДКЛЮЧЕНИЕ -----------------

def get_connection():
    conn = sqlite3.connect(
        DB_NAME,
        check_same_thread=False,
        timeout=30
    )

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    return conn


conn = get_connection()
cursor = conn.cursor()


# ----------------- СОЗДАНИЕ ТАБЛИЦ -----------------

def create_tables():
    try:
        with lock:

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sellers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE,
                shop_name TEXT UNIQUE,
                is_active INTEGER DEFAULT 0
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                name TEXT,
                amount TEXT,
                price REAL,
                stock INTEGER,
                FOREIGN KEY (seller_id) REFERENCES sellers(id)
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buyer_tg INTEGER,
                seller_id INTEGER,
                product_id INTEGER,
                amount TEXT,
                address TEXT,
                status TEXT,
                FOREIGN KEY (seller_id) REFERENCES sellers(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """)

            conn.commit()

            logging.info("✅ Tables created")

    except Exception as e:
        logging.error(f"❌ create_tables error: {e}")


# ----------------- ПРОДАВЦЫ -----------------

def add_seller(tg_id):
    try:
        with lock:

            cursor.execute("""
                INSERT INTO sellers (tg_id, shop_name, is_active)
                VALUES (?, NULL, 0)
            """, (tg_id,))

            conn.commit()

            return True

    except sqlite3.IntegrityError:
        return False

    except Exception as e:
        logging.error(f"❌ add_seller: {e}")
        return False


def set_shop_name(tg_id, shop_name):
    try:
        with lock:

            name = shop_name.strip().capitalize()

            cursor.execute("""
                UPDATE sellers
                SET shop_name=?
                WHERE tg_id=?
            """, (name, tg_id))

            conn.commit()

    except Exception as e:
        logging.error(f"❌ set_shop_name: {e}")


def get_seller(tg_id):
    try:
        return cursor.execute("""
            SELECT * FROM sellers
            WHERE tg_id=?
        """, (tg_id,)).fetchone()

    except Exception as e:
        logging.error(f"❌ get_seller: {e}")
        return None


def get_all_sellers():
    cursor.execute("SELECT * FROM sellers")
    return cursor.fetchall()


def get_all_buyers():
    cursor.execute("SELECT DISTINCT buyer_id FROM orders")
    return cursor.fetchall()


def get_seller_by_id(seller_id):
    try:
        return cursor.execute("""
            SELECT * FROM sellers
            WHERE id=?
        """, (seller_id,)).fetchone()

    except Exception as e:
        logging.error(f"❌ get_seller_by_id: {e}")
        return None


def get_seller_by_tg(tg_id):
    try:
        return cursor.execute("""
            SELECT * FROM sellers
            WHERE tg_id=?
        """, (tg_id,)).fetchone()

    except Exception as e:
        logging.error(f"❌ get_seller_by_tg: {e}")
        return None


def activate_seller(tg_id):
    try:
        with lock:

            cursor.execute("""
                UPDATE sellers
                SET is_active=1
                WHERE tg_id=?
            """, (tg_id,))

            conn.commit()

    except Exception as e:
        logging.error(f"❌ activate_seller: {e}")


def deactivate_seller(tg_id):
    try:
        with lock:

            cursor.execute("""
                UPDATE sellers
                SET is_active=0
                WHERE tg_id=?
            """, (tg_id,))

            conn.commit()

    except Exception as e:
        logging.error(f"❌ deactivate_seller: {e}")


def get_all_shops():
    try:
        return cursor.execute("""
            SELECT id, shop_name
            FROM sellers
            WHERE is_active=1
        """).fetchall()

    except Exception as e:
        logging.error(f"❌ get_all_shops: {e}")
        return []


# ----------------- ТОВАРЫ -----------------

def add_product(seller_id, name, amount, price, stock):
    try:
        with lock:

            cursor.execute("""
                INSERT INTO products
                (seller_id, name, amount, price, stock)
                VALUES (?, ?, ?, ?, ?)
            """, (seller_id, name, amount, price, stock))

            conn.commit()

            return True

    except Exception as e:
        logging.error(f"❌ add_product: {e}")
        return False


def get_products(seller_id):
    try:
        return cursor.execute("""
            SELECT id, name, amount, price, stock
            FROM products
            WHERE seller_id=?
        """, (seller_id,)).fetchall()

    except Exception as e:
        logging.error(f"❌ get_products: {e}")
        return []

def get_products_by_shop(shop_id):
    try:
        return cursor.execute("""
            SELECT id, name, amount, price
            FROM products
            WHERE seller_id=? AND stock > 0
        """, (shop_id,)).fetchall()

    except Exception as e:
        logging.error(f"❌ get_products_by_shop: {e}")
        return []


def get_product(product_id):
    try:
        return cursor.execute("""
            SELECT *
            FROM products
            WHERE id=?
        """, (product_id,)).fetchone()

    except Exception as e:
        logging.error(f"❌ get_product: {e}")
        return None


def delete_product_by_id(product_id):
    try:
        with lock:

            cursor.execute("""
                DELETE FROM products
                WHERE id=?
            """, (product_id,))

            conn.commit()

    except Exception as e:
        logging.error(f"❌ delete_product: {e}")


def get_product_by_name_and_seller(name, seller_id):
    return cursor.execute(
        "SELECT * FROM products WHERE name=? AND seller_id=?",
        (name, seller_id)
    ).fetchone()

def update_product_field(pid: int, field: str, value):

    allowed = ["name", "amount", "price", "stock"]

    if field not in allowed:
        return False

    cursor.execute(
        f"UPDATE products SET {field}=? WHERE id=?",
        (value, pid)
    )

    conn.commit()

    return True


def decrease_stock(product_id, amount):
    try:
        with lock:

            cursor.execute("""
                UPDATE products
                SET stock = stock - ?
                WHERE id=? AND stock >= ?
            """, (amount, product_id, amount))

            conn.commit()

            return cursor.rowcount > 0

    except Exception as e:
        logging.error(f"❌ decrease_stock: {e}")
        return False


# ----------------- ЗАКАЗЫ -----------------

def create_order(buyer_tg, seller_id, product_id, amount, address):
    try:
        with lock:

            cursor.execute("""
                INSERT INTO orders
                (buyer_tg, seller_id, product_id, amount, address, status)
                VALUES (?, ?, ?, ?, ?, 'new')
            """, (buyer_tg, seller_id, product_id, amount, address))

            conn.commit()

            return cursor.lastrowid

    except Exception as e:
        logging.error(f"❌ create_order: {e}")
        return None


def get_order(order_id):
    try:
        return cursor.execute("""
            SELECT *
            FROM orders
            WHERE id=?
        """, (order_id,)).fetchone()

    except Exception as e:
        logging.error(f"❌ get_order: {e}")
        return None


def update_order_status(order_id, status):
    try:
        with lock:

            cursor.execute("""
                UPDATE orders
                SET status=?
                WHERE id=?
            """, (status, order_id))

            conn.commit()

    except Exception as e:
        logging.error(f"❌ update_order_status: {e}")


def get_buyer_by_order(order_id):
    try:
        return cursor.execute("""
            SELECT buyer_tg
            FROM orders
            WHERE id=?
        """, (order_id,)).fetchone()

    except Exception as e:
        logging.error(f"❌ get_buyer_by_order: {e}")
        return None


def get_seller_orders(seller_id):
    try:
        return cursor.execute("""
            SELECT o.id, p.name, o.amount, o.status
            FROM orders o
            JOIN products p ON o.product_id = p.id
            WHERE o.seller_id=?
            ORDER BY o.id DESC
        """, (seller_id,)).fetchall()

    except Exception as e:
        logging.error(f"❌ get_seller_orders: {e}")
        return []


def get_seller_tg_by_product(product_id):
    try:
        return cursor.execute("""
            SELECT s.tg_id
            FROM sellers s
            JOIN products p ON p.seller_id = s.id
            WHERE p.id=?
        """, (product_id,)).fetchone()

    except Exception as e:
        logging.error(f"❌ get_seller_tg_by_product: {e}")
        return None


def search_products_by_name(shop_id: int, query: str):

    q = f"%{query}%"

    logging.info(f"[DB] Search: seller_id={shop_id}, query={q}")

    cursor.execute(
        "SELECT * FROM products WHERE seller_id=? AND name LIKE ? COLLATE NOCASE",
        (shop_id, q)
    )

    result = cursor.fetchall()

    logging.info(f"[DB] Result count = {len(result)}")

    return result


# ----------------- ЗАКРЫТИЕ -----------------

def close_db():
    try:
        conn.close()
        logging.info("✅ DB closed")

    except Exception as e:
        logging.error(f"❌ close_db: {e}")

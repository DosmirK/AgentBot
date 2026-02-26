import logging
from psycopg2 import pool, extras

# ----------------- НАСТРОЙКИ -----------------

DB_CONFIG = {
    "dbname": "shop",
    "user": "postgres",
    "password": "dos002016",
    "host": "localhost",
    "port": "5432"
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

connection_pool = pool.SimpleConnectionPool(1, 20, **DB_CONFIG)


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
        seller_id INTEGER REFERENCES sellers(id),
        product_id INTEGER REFERENCES products(id),
        amount TEXT,
        address TEXT,
        status TEXT
    )
    """)

    conn.commit()
    cur.close()
    release_connection(conn)
    logging.info("✅ Tables created")


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
        cur.execute("SELECT DISTINCT buyer_tg FROM orders")
        result = cur.fetchall()
        return result

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


def decrease_stock(product_id, amount):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE products SET stock = stock - %s WHERE id = %s",
        (amount, product_id)
    )
    conn.commit()

    cursor.execute(
        "SELECT stock, seller_id, name FROM products WHERE id = %s",
        (product_id,)
    )

    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "stock": int(result[0]),
            "seller_id": result[1],
            "name": result[2]
        }

    return None


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

def create_order(buyer_tg, seller_id, product_id, amount, address):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO orders
        (buyer_tg, seller_id, product_id, amount, address, status)
        VALUES (%s, %s, %s, %s, %s, 'new')
        RETURNING id
    """, (buyer_tg, seller_id, product_id, amount, address))

    order_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    release_connection(conn)

    return order_id


def get_order(order_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    try:
        cur.execute(
            "SELECT * FROM orders WHERE id=%s",
            (order_id,)
        )

        result = cur.fetchone()
        return result

    except Exception as e:
        logging.error(f"❌ get_order: {e}")
        return None

    finally:
        cur.close()
        release_connection(conn)


def get_seller_orders(seller_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    try:
        cur.execute("""
            SELECT o.id, p.name, o.amount, o.status
            FROM orders o
            JOIN products p ON o.product_id = p.id
            WHERE o.seller_id=%s
            ORDER BY o.id DESC
        """, (seller_id,))

        result = cur.fetchall()
        return result

    except Exception as e:
        logging.error(f"❌ get_seller_orders: {e}")
        return []

    finally:
        cur.close()
        release_connection(conn)


def get_buyer_by_order(order_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)

    try:
        cur.execute(
            "SELECT buyer_tg FROM orders WHERE id=%s",
            (order_id,)
        )

        result = cur.fetchone()
        return result

    except Exception as e:
        logging.error(f"❌ get_buyer_by_order: {e}")
        return None

    finally:
        cur.close()
        release_connection(conn)


def update_order_status(order_id, status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE orders SET status=%s WHERE id=%s",
        (status, order_id)
    )

    conn.commit()
    cur.close()
    release_connection(conn)
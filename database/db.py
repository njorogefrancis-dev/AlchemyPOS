import sqlite3, os, hashlib, hmac, secrets
from datetime import datetime
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alchemypos.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 310000)
    return f"pbkdf2:sha256:{salt}:{key.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        parts = stored_hash.split(":")
        if len(parts) != 4: return False
        _, algo, salt, stored_key = parts
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 310000)
        return hmac.compare_digest(key.hex(), stored_key)
    except: return False

def get_setting(key, default=""):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key, value):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
    conn.commit(); conn.close()

def log_action(user_id, username, action, details=""):
    try:
        conn = get_connection()
        conn.execute("INSERT INTO audit_logs(user_id,username,action,details) VALUES(?,?,?,?)",
                     (user_id, username, action, details))
        conn.commit(); conn.close()
    except: pass

def generate_receipt_number():
    now = datetime.now()
    token = secrets.token_hex(3).upper()
    return f"RCP-{now.strftime('%Y%m%d')}-{token}"

def is_first_run():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return count == 0

def get_categories():
    conn = get_connection()
    rows = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_payment_methods():
    conn = get_connection()
    rows = conn.execute("SELECT name, label FROM payment_methods WHERE is_active=1 ORDER BY sort_order").fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]

def init_database():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','cashier','inventory_manager')),
        full_name TEXT,
        is_active INTEGER DEFAULT 1,
        failed_attempts INTEGER DEFAULT 0,
        locked_until TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        last_login TEXT,
        security_question TEXT,
        security_answer_hash TEXT,
        security_question2 TEXT,
        security_answer2_hash TEXT,
        security_question3 TEXT,
        security_answer3_hash TEXT
    )""")
    # Migrate: add new columns if they don't exist yet
    for col, typ in [("security_question2","TEXT"),("security_answer2_hash","TEXT"),
                     ("security_question3","TEXT"),("security_answer3_hash","TEXT")]:
        try: c.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
        except: pass  # column already exists

    # Migrate: expand role CHECK to include inventory_manager
    # SQLite can't ALTER CHECK constraints, so we check if migration needed
    tbl_sql = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
    if tbl_sql and "inventory_manager" not in tbl_sql[0]:
        # Recreate users table with new constraint, preserving all data
        c.execute("PRAGMA foreign_keys=OFF")
        c.execute("""CREATE TABLE IF NOT EXISTS users_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','cashier','inventory_manager')),
            full_name TEXT, is_active INTEGER DEFAULT 1,
            failed_attempts INTEGER DEFAULT 0, locked_until TEXT,
            created_at TEXT DEFAULT (datetime('now')), last_login TEXT,
            security_question TEXT, security_answer_hash TEXT,
            security_question2 TEXT, security_answer2_hash TEXT,
            security_question3 TEXT, security_answer3_hash TEXT
        )""")
        c.execute("""INSERT OR IGNORE INTO users_new SELECT
            id, username, password_hash, role, full_name, is_active,
            failed_attempts, locked_until, created_at, last_login,
            security_question, security_answer_hash,
            security_question2, security_answer2_hash,
            security_question3, security_answer3_hash
            FROM users""")
        c.execute("DROP TABLE users")
        c.execute("ALTER TABLE users_new RENAME TO users")
        c.execute("PRAGMA foreign_keys=ON")

    c.execute("""CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS payment_methods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        label TEXT NOT NULL,
        description TEXT,
        is_active INTEGER DEFAULT 1,
        sort_order INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode TEXT UNIQUE,
        name TEXT NOT NULL,
        category TEXT DEFAULT 'General',
        price REAL NOT NULL,
        cost REAL DEFAULT 0,
        unit TEXT DEFAULT 'pcs',
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL REFERENCES products(id) UNIQUE,
        quantity REAL DEFAULT 0,
        low_stock_threshold REAL DEFAULT 5,
        last_updated TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_number TEXT UNIQUE NOT NULL,
        cashier_id INTEGER REFERENCES users(id),
        subtotal REAL NOT NULL,
        discount REAL DEFAULT 0,
        tax REAL DEFAULT 0,
        total REAL NOT NULL,
        payment_method TEXT DEFAULT 'cash',
        amount_tendered REAL DEFAULT 0,
        change_given REAL DEFAULT 0,
        status TEXT DEFAULT 'completed',
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL REFERENCES sales(id),
        product_id INTEGER REFERENCES products(id),
        product_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit_price REAL NOT NULL,
        subtotal REAL NOT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        path TEXT NOT NULL,
        size_bytes INTEGER,
        created_by INTEGER REFERENCES users(id),
        created_at TEXT DEFAULT (datetime('now')),
        notes TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        username TEXT,
        action TEXT NOT NULL,
        details TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")

    c.execute("CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(created_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sale_items_sale ON sale_items(sale_id)")

    # Default settings
    defaults = [
        ("shop_name",           "My Shop"),
        ("shop_address",        "Nairobi, Kenya"),
        ("shop_phone",          "+254 700 000 000"),
        ("shop_email",          ""),
        ("currency_symbol",     "KSh"),
        ("currency_name",       "KES"),
        ("tax_rate",            "0"),
        ("tax_name",            "VAT"),
        ("receipt_footer",      "Asante kwa biashara yako!"),
        ("receipt_header",      ""),
        ("backup_path",         str(Path.home() / "alchemypos_backups")),
        ("auto_backup",         "0"),
        ("theme",               "dark"),
        ("track_stock",         "1"),
        ("warn_out_of_stock",   "1"),
        ("allow_negative_stock","0"),
        ("auto_print_receipt",  "0"),
        ("default_low_stock",   "5"),
        ("default_unit",        "pcs"),
        ("printer_command",     "lp"),
        ("paybill_number",      ""),
        ("till_number",         ""),
        ("send_money_name",     ""),
        ("pochi_number",        ""),
    ]
    for k, v in defaults:
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))

    # Default categories
    default_cats = ["General","Beverages","Food","Snacks","Bakery","Dairy",
                    "Grains","Groceries","Hot Drinks","Condiments","Electronics",
                    "Clothing","Health & Beauty","Stationery","Other"]
    for cat in default_cats:
        c.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", (cat,))

    # Default payment methods (Kenya-focused)
    default_payments = [
        ("cash",       "Cash",          "Physical cash payment",        1, 1),
        ("mpesa",      "M-Pesa",        "M-Pesa mobile money",          1, 2),
        ("paybill",    "Paybill",       "M-Pesa Paybill number",        1, 3),
        ("till",       "Buy Goods Till","M-Pesa Buy Goods Till number", 1, 4),
        ("send_money", "Send Money",    "M-Pesa Send Money",            1, 5),
        ("pochi",      "Pochi la Biashara","Pochi la Biashara",         1, 6),
        ("card",       "Card/Bank",     "Debit or credit card",         1, 7),
        ("credit",     "Credit/Tab",    "Customer credit / tab",        0, 8),
    ]
    for name, label, desc, active, order in default_payments:
        c.execute("""INSERT OR IGNORE INTO payment_methods(name,label,description,is_active,sort_order)
                     VALUES(?,?,?,?,?)""", (name, label, desc, active, order))

    conn.commit(); conn.close()


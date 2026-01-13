import sqlite3
import os

DB_FILE = "data/stock.db"
def create_db():
    # ถ้ามี DB อยู่แล้ว ไม่ต้องทำอะไร
    if os.path.exists(DB_FILE):
        print("DB already exists")
    else:
        os.makedirs("data", exist_ok=True)

        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE stock_doc (
            doc_no TEXT PRIMARY KEY,
            branch_code TEXT,
            branch_name TEXT,
            status TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cur.execute("""
        CREATE TABLE stock_count (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_no TEXT,
            branch_code TEXT,
            location TEXT,
            barcode TEXT,
            item_code TEXT,
            item_name TEXT,
            qty INTEGER,
            uom TEXT
        )
        """)

        conn.commit()
        conn.close()

create_db()

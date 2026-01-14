from flask import Flask, render_template, request, redirect, url_for, session, send_file
from dotenv import load_dotenv
import sqlite3
import pyodbc
import sys
import os
import logging
from datetime import datetime
import pandas as pd
from io import BytesIO
from init_db import create_db

load_dotenv()
app = Flask(__name__)
app.secret_key = "stock_secret"
STATUS = 'Y'
create_db()
DB_FILE = "data/stock.db"

def get_conn_mssql():
    try:
        DRIVER=pyodbc.drivers()[0]
        SERVER = os.getenv("MSSQL_SERVER")
        DATABASE = os.getenv("MSSQL_DATABASE")
        UID = os.getenv("MSSQL_UID")
        PWD = os.getenv("MSSQL_PWD")
        conn_mssql = pyodbc.connect(
            f';DRIVER={DRIVER}'
            f';SERVER={SERVER}'
            f';DATABASE={DATABASE}'
            f';UID={UID}'
            f';PWD={PWD}'
            f';TIMEOUT=5'
            f';ENCRYPT=YES'
            f';TRUSTSERVERCERTIFICATE=YES'
        )
        print("Successfully connected to the MSSQL.")
        print("=========================================")
    except Exception as exc:
        logging.error("Unable to connect to database. Please contact administrator.")
        sys.exit(1)
    cursor = conn_mssql.cursor()
    return cursor

cursor = get_conn_mssql()

def get_branches():
    get_brch = ("""
                    SELECT
                        BrchID, BrchName 
                    FROM EMBrch
                    WHERE BrchAddr3Eng = 'Y'
                    ORDER BY BrchCode
                    """)   
    cursor.execute(get_brch)
    branches = cursor.fetchall()
    return branches

def get_item(barcode):
    barcode = str(barcode).strip()
    get_itemcode =("""
                    SELECT 
                    	a.GoodNameEng1, a.GoodName1, c.GoodUnitCode
                    FROM 
                    	EMGood a
                    	LEFT OUTER JOIN EMGoodMultiUnit b ON b.GoodID = a.GoodID
                    	LEFT OUTER JOIN EMGoodUnit c ON c.GoodUnitID = b.GoodUnitID
                    WHERE
                    	b.SaleUnitFlag = 'Y' AND
                        CAST(a.GoodCode AS VARCHAR(50)) = ?
                   """)
    cursor.execute(get_itemcode, barcode)
    item = cursor.fetchone()
    return item

def create_doc(branch_code, branch_name):
    doc_no = "STK" + datetime.now().strftime("%Y%m%d%H%M%S")
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO stock_doc (doc_no, branch_code, branch_name, status)
        VALUES (?, ?, ?, ?)
    """, (doc_no, branch_code, branch_name, "Y"))
    conn.commit()
    conn.close()
    return doc_no

def get_docs():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT doc_no, branch_name, created_at
        FROM stock_doc
        WHERE status = 'Y'
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def save_count(doc_no, branch_code, location, barcode):
    item = get_item(barcode)
    if not item:
        return "❌ ไม่พบบาร์โค้ด"

    item_code, item_name, uom = item

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        SELECT id FROM stock_count
        WHERE doc_no=? AND barcode=? AND location=?
    """, (doc_no, barcode, location))

    row = cur.fetchone()
    if row:
        cur.execute("""
            UPDATE stock_count
            SET qty = qty + 1
            WHERE id=?
        """, (row[0],))
    else:
        cur.execute("""
            INSERT INTO stock_count
            (doc_no, branch_code, location, barcode,
             item_code, item_name, qty, uom)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """, (doc_no, branch_code, location,
              barcode, item_code, item_name, uom))

    conn.commit()
    conn.close()
    return "✔ บันทึกแล้ว"

def get_counts(doc_no):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT location, barcode, item_code, item_name, qty, uom
        FROM stock_count
        WHERE doc_no=?
        ORDER BY id DESC
    """, (doc_no,))
    rows = cur.fetchall()
    conn.close()
    return rows


@app.route("/", methods=["GET", "POST"])
def index():
    branches = get_branches()
    docs = get_docs()

    if request.method == "POST":
        bc = request.form["branch_code"]
        bn = request.form["branch_name"]
        doc_no = create_doc(bc, bn)

        session["doc_no"] = doc_no
        session["branch_code"] = bc
        session["branch_name"] = bn

        return redirect(f"/count/{doc_no}")

    return render_template(
        "index.html",
        branches=branches,
        docs=docs
    )
    
@app.route("/count/<doc_no>", methods=["GET", "POST"])
def count(doc_no):
    # 🔒 ดึงจาก session แบบปลอดภัย
    branch_code = session.get("branch_code")
    branch_name = session.get("branch_name")

    # ❗ ถ้า session หาย (เช่น restart server)
    if not branch_code or not branch_name:
        # โหลดจาก DB แทน
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            SELECT branch_code, branch_name
            FROM stock_doc
            WHERE doc_no = ? AND status = 'Y'
        """, (doc_no,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return redirect(url_for("index"))

        branch_code, branch_name = row

        # set session ใหม่
        session["doc_no"] = doc_no
        session["branch_code"] = branch_code
        session["branch_name"] = branch_name

    msg = None
    if request.method == "POST":
        barcode = request.form["barcode"]
        location = request.form["location"]
        msg = save_count(
            doc_no,
            branch_code,
            location,
            barcode
        )

    counts = get_counts(doc_no)
    return render_template(
        "count.html",
        doc_no=doc_no,
        branch_name=branch_name,
        counts=counts,
        msg=msg
    )
    
@app.route("/delete/<doc_no>")
def delete(doc_no):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
                UPDATE 
                    stock_doc 
                SET status = 'N' 
                WHERE doc_no = ?""", (doc_no,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/export/<doc_no>")
def export_excel(doc_no):
    conn = sqlite3.connect(DB_FILE)

    df = pd.read_sql_query("""
                            SELECT
                                doc_no AS เอกสาร,
                                branch_code AS สาขา,
                                location AS Location,
                                barcode AS Barcode,
                                item_code AS รหัสสินค้า,
                                item_name AS ชื่อสินค้า,
                                qty AS จำนวน,
                                uom AS หน่วย
                            FROM stock_count
                            WHERE doc_no = ?
                            ORDER BY location, item_code
    """, conn, params=(doc_no,))

    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="StockCount")

    output.seek(0)

    return send_file(
        output,
        download_name=f"stock_count_doc_{doc_no}.xlsx",
        as_attachment=True
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5100, debug=True)
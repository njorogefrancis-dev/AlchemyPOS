from database.db import get_connection, generate_receipt_number, get_setting, log_action
from inventory.inventory import inventory_manager
from datetime import datetime

class SalesManager:
    def process_sale(self, cart_items, payment_method, amount_tendered, discount, cashier_id, cashier_name):
        if not cart_items:
            return False, "Cart is empty.", None

        tax_rate = float(get_setting("tax_rate", "0")) / 100.0
        subtotal = sum(item["qty"] * item["price"] for item in cart_items)
        discount_amt = float(discount or 0)
        taxable = max(0, subtotal - discount_amt)
        tax_amt = round(taxable * tax_rate, 2)
        total = round(taxable + tax_amt, 2)

        try:
            amount_tendered = float(amount_tendered)
        except (ValueError, TypeError):
            amount_tendered = total

        change = round(amount_tendered - total, 2)
        receipt_num = generate_receipt_number()
        sale_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("""INSERT INTO sales(receipt_number,cashier_id,subtotal,discount,tax,total,
                         payment_method,amount_tendered,change_given,created_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?)""",
                      (receipt_num, cashier_id, subtotal, discount_amt, tax_amt, total,
                       payment_method, amount_tendered, change, sale_time))
            sale_id = c.lastrowid

            for item in cart_items:
                c.execute("""INSERT INTO sale_items(sale_id,product_id,product_name,quantity,unit_price,subtotal)
                             VALUES(?,?,?,?,?,?)""",
                          (sale_id, item.get("id"), item["name"], item["qty"],
                           item["price"], round(item["qty"] * item["price"], 2)))
                if item.get("id"):
                    conn.execute("UPDATE inventory SET quantity=MAX(0,quantity-?), last_updated=datetime('now') WHERE product_id=?",
                                 (item["qty"], item["id"]))

            conn.commit()
            log_action(cashier_id, cashier_name, "SALE", f"Receipt {receipt_num}, Total ${total:.2f}")

            sale_data = {
                "sale_id": sale_id,
                "receipt_number": receipt_num,
                "cashier": cashier_name,
                "items": [dict(i) for i in cart_items],  # snapshot — not a reference
                "subtotal": subtotal,
                "discount": discount_amt,
                "tax": tax_amt,
                "total": total,
                "payment_method": payment_method,
                "amount_tendered": amount_tendered,
                "change": change,
                "created_at": sale_time,
            }
            return True, "Sale completed.", sale_data
        except Exception as e:
            conn.rollback()
            return False, str(e), None
        finally:
            conn.close()

    def get_sales_history(self, date_from=None, date_to=None, limit=200):
        conn = get_connection()
        sql = """SELECT s.id, s.receipt_number, u.full_name as cashier,
                        s.subtotal, s.discount, s.tax, s.total,
                        s.payment_method, s.created_at, s.status
                 FROM sales s LEFT JOIN users u ON u.id=s.cashier_id
                 WHERE 1=1"""
        params = []
        if date_from:
            sql += " AND date(s.created_at) >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND date(s.created_at) <= ?"
            params.append(date_to)
        sql += " ORDER BY s.created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_sale_items(self, sale_id):
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM sale_items WHERE sale_id=?", (sale_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_daily_summary(self, date_str=None):
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        conn = get_connection()
        row = conn.execute("""SELECT COUNT(*) as tx_count,
                              COALESCE(SUM(total),0) as revenue,
                              COALESCE(SUM(discount),0) as discounts,
                              COALESCE(SUM(tax),0) as taxes
                              FROM sales WHERE date(created_at)=? AND status='completed'""",
                           (date_str,)).fetchone()
        conn.close()
        return dict(row) if row else {}

sales_manager = SalesManager()

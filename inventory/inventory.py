from database.db import get_connection, log_action, get_categories as db_get_categories
from datetime import datetime

class InventoryManager:

    def search_products(self, query="", category=None, limit=200, in_stock_only=False):
        conn = get_connection()
        sql = """SELECT p.id, p.name, p.barcode, p.category, p.price, p.cost, p.unit,
                        COALESCE(i.quantity,0) AS quantity,
                        COALESCE(i.low_stock_threshold,5) AS low_stock_threshold
                 FROM products p LEFT JOIN inventory i ON i.product_id=p.id
                 WHERE p.is_active=1"""
        params = []
        if in_stock_only:
            sql += " AND COALESCE(i.quantity,0) > 0"
        if query:
            sql += " AND (LOWER(p.name) LIKE LOWER(?) OR p.barcode LIKE ?)"
            params += [f"%{query}%", f"%{query}%"]
        if category:
            sql += " AND LOWER(p.category)=LOWER(?)"
            params.append(category)
        sql += " ORDER BY p.name LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_product_by_id(self, pid):
        conn = get_connection()
        row = conn.execute(
            """SELECT p.*, COALESCE(i.quantity,0) AS quantity,
               COALESCE(i.low_stock_threshold,5) AS low_stock_threshold
               FROM products p LEFT JOIN inventory i ON i.product_id=p.id
               WHERE p.id=?""", (pid,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_categories(self):
        return db_get_categories()

    def add_product(self, name, price, cost, category, unit, barcode, quantity, low_stock, user_id, username):
        name = name.strip() if name else ""
        if not name:
            return False, "Product name is required."
        try:
            price     = float(str(price).replace(",","").strip())
            cost      = float(str(cost).replace(",","").strip())
            quantity  = float(str(quantity).replace(",","").strip())
            low_stock = float(str(low_stock).replace(",","").strip())
        except (ValueError, AttributeError):
            return False, "Price, cost, quantity and low stock must be valid numbers."

        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("""INSERT INTO products(name,price,cost,category,unit,barcode)
                         VALUES(?,?,?,?,?,?)""",
                      (name, price, cost, category or "General", unit or "pcs", barcode.strip() or None))
            pid = c.lastrowid
            c.execute("""INSERT INTO inventory(product_id,quantity,low_stock_threshold)
                         VALUES(?,?,?)""", (pid, quantity, low_stock))
            conn.commit()
            log_action(user_id, username, "ADD_PRODUCT", f"Added: {name}, qty={quantity}")
            return True, "Product added successfully."
        except Exception as e:
            conn.rollback()
            msg = str(e)
            if "UNIQUE" in msg.upper(): return False, "A product with that barcode already exists."
            return False, msg
        finally:
            conn.close()

    def update_product(self, pid, name, price, cost, category, unit, barcode, quantity, low_stock, user_id, username):
        name = name.strip() if name else ""
        if not name:
            return False, "Product name is required."
        try:
            price     = float(str(price).replace(",","").strip())
            cost      = float(str(cost).replace(",","").strip())
            quantity  = float(str(quantity).replace(",","").strip())
            low_stock = float(str(low_stock).replace(",","").strip())
        except (ValueError, AttributeError):
            return False, "Price, cost, quantity and low stock must be valid numbers."

        conn = get_connection()
        try:
            conn.execute("""UPDATE products SET name=?,price=?,cost=?,category=?,unit=?,
                            barcode=?,updated_at=datetime('now') WHERE id=?""",
                         (name, price, cost, category or "General",
                          unit or "pcs", barcode.strip() or None, pid))
            # Upsert inventory row
            existing = conn.execute("SELECT id FROM inventory WHERE product_id=?", (pid,)).fetchone()
            if existing:
                conn.execute("""UPDATE inventory SET quantity=?,low_stock_threshold=?,
                                last_updated=datetime('now') WHERE product_id=?""",
                             (quantity, low_stock, pid))
            else:
                conn.execute("""INSERT INTO inventory(product_id,quantity,low_stock_threshold)
                                VALUES(?,?,?)""", (pid, quantity, low_stock))
            conn.commit()
            log_action(user_id, username, "UPDATE_PRODUCT", f"Updated id={pid}: {name}")
            return True, "Product updated successfully."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def adjust_stock(self, product_id, delta, user_id=None, username=None, reason=""):
        conn = get_connection()
        try:
            existing = conn.execute("SELECT id, quantity FROM inventory WHERE product_id=?", (product_id,)).fetchone()
            if existing:
                new_qty = max(0, existing["quantity"] + delta)
                conn.execute("UPDATE inventory SET quantity=?,last_updated=datetime('now') WHERE product_id=?",
                             (new_qty, product_id))
            else:
                conn.execute("INSERT INTO inventory(product_id,quantity,low_stock_threshold) VALUES(?,?,5)",
                             (product_id, max(0, delta)))
            conn.commit()
            if user_id:
                log_action(user_id, username or "", "STOCK_ADJUST",
                           f"pid={product_id} delta={delta:+.0f} reason={reason or 'N/A'}")
            return True, "Stock updated."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def delete_product(self, pid, user_id, username):
        conn = get_connection()
        conn.execute("UPDATE products SET is_active=0 WHERE id=?", (pid,))
        conn.commit()
        conn.close()
        log_action(user_id, username, "DELETE_PRODUCT", f"Deleted id={pid}")
        return True, "Product removed."

    def get_low_stock(self):
        conn = get_connection()
        rows = conn.execute("""SELECT p.id,p.name,p.category,i.quantity,i.low_stock_threshold
                               FROM products p JOIN inventory i ON i.product_id=p.id
                               WHERE p.is_active=1 AND i.quantity<=i.low_stock_threshold
                               ORDER BY i.quantity ASC""").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_for_export(self):
        conn = get_connection()
        rows = conn.execute("""SELECT p.id,p.name,p.barcode,p.category,p.price,p.cost,p.unit,
                                      COALESCE(i.quantity,0) AS quantity,
                                      COALESCE(i.low_stock_threshold,5) AS low_stock_threshold,
                                      p.created_at, p.updated_at
                               FROM products p LEFT JOIN inventory i ON i.product_id=p.id
                               WHERE p.is_active=1 ORDER BY p.category,p.name""").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def generate_sample_csv(self, path):
        """Write a 50-item sample CSV the user can fill in and import."""
        import csv
        headers = ["name","category","price","cost","unit","barcode","quantity","low_stock_threshold"]
        samples = [
            ["Unga Pembe 2kg",          "Grains",         "200","135","bag",     "6009800340011","50","10"],
            ["Jogoo Maize 1kg",          "Grains",         "100", "65","bag",     "6009800340042","80","15"],
            ["Basmati Rice 1kg",         "Grains",         "250","165","bag",     "6009800340056","60","10"],
            ["Spaghetti 400g",           "Grains",         "100", "65","pack",    "6009800340077","100","15"],
            ["Quaker Oats 500g",         "Grains",         "280","182","box",     "5000116101043","40", "8"],
            ["Brookside Milk 1L",        "Dairy",          "130", "84","packet",  "6009800140028","100","20"],
            ["KCC Butter 250g",          "Dairy",          "350","225","block",   "6009800140035","40", "8"],
            ["Eggs Tray 30",             "Dairy",          "550","360","tray",    "6009800140070","30", "6"],
            ["Fresha Yoghurt 500ml",     "Dairy",          "120", "78","bottle",  "6009800140063","60","10"],
            ["Tuzo Cheese 200g",         "Dairy",          "420","270","pack",    "6009800140049","20", "4"],
            ["Coca-Cola 500ml",          "Beverages",       "80", "52","bottle",  "5449000131836","120","25"],
            ["Fanta Orange 500ml",       "Beverages",       "80", "52","bottle",  "5449000054227","100","20"],
            ["Keringet Water 500ml",     "Beverages",       "50", "28","bottle",  "6009801940021","200","30"],
            ["Delmonte Juice 1L",        "Beverages",      "220","145","pack",    "6009659040014", "40", "8"],
            ["Red Bull 250ml",           "Beverages",      "250","165","can",     "9002490100070", "30", "6"],
            ["Ketepa Tea 100 bags",      "Hot Drinks",     "280","185","box",     "6009659040137", "60","10"],
            ["Nescafe Classic 100g",     "Hot Drinks",     "650","430","jar",     "6009659040151", "25", "5"],
            ["Milo 400g",               "Hot Drinks",     "650","420","tin",     "6009659040168", "30", "6"],
            ["Dormans Coffee 100g",      "Hot Drinks",     "450","295","jar",     "6009659040144", "35", "7"],
            ["Horlicks 500g",            "Hot Drinks",     "750","490","tin",     "6009659040175", "20", "4"],
            ["Elianto Oil 1L",           "Groceries",      "380","248","bottle",  "6009900340011", "80","15"],
            ["Mumias Sugar 1kg",         "Groceries",      "150", "98","bag",     "6009900340042","100","20"],
            ["Blue Band 250g",           "Groceries",      "145", "94","tub",     "6009900340105", "70","12"],
            ["Kakuzi Salt 500g",         "Groceries",       "50", "30","pack",    "6009900340056","150","25"],
            ["Royco Mchuzi 75g",         "Condiments",      "65", "42","sachet",  "6009900340063","150","25"],
            ["Tomato Paste 400g",        "Condiments",     "170","110","tin",     "6009900340091", "80","15"],
            ["Heinz Ketchup 300g",       "Condiments",     "350","228","bottle",  "5000157024626", "40", "8"],
            ["Mandazi 6pcs",             "Bakery",          "60", "35","pack",    "","150","30"],
            ["Supa Loaf Bread 400g",     "Bakery",         "100", "65","loaf",    "6001068400077", "80","15"],
            ["Scones 2pcs",              "Bakery",          "60", "38","pack",    "","120","20"],
            ["Lays Crisps 100g",         "Snacks",          "80", "52","pack",    "6001068400011","100","15"],
            ["Pringles 165g",            "Snacks",         "450","293","can",     "6001068400028", "25", "5"],
            ["Kitkat 4-finger",          "Snacks",         "120", "78","bar",     "5000159461122", "60","10"],
            ["Cadbury Dairy Milk 90g",   "Snacks",         "180","117","bar",     "7622210389961", "50","10"],
            ["Digestive Biscuits 200g",  "Snacks",         "180","117","pack",    "6001068400049", "60","10"],
            ["Panadol 10s",              "Health & Beauty", "60", "38","pack",    "6009600001001", "80","15"],
            ["Dettol 100ml",             "Health & Beauty","250","163","bottle",  "6009600001004", "50","10"],
            ["Geisha Soap 175g",         "Health & Beauty", "80", "52","bar",     "6009600001008","150","25"],
            ["Colgate Toothpaste 75ml",  "Health & Beauty","180","117","tube",    "6009600001014", "80","15"],
            ["Omo Powder 500g",          "Health & Beauty","180","117","pack",    "6009600001010", "70","12"],
            ["Vaseline Lotion 200ml",    "Health & Beauty","350","228","bottle",  "6009600001017", "50","10"],
            ["Always Pads 8s",           "Health & Beauty","100", "65","pack",    "6009600001006","100","20"],
            ["Pampers S 24s",            "Health & Beauty","850","553","pack",    "6009600001020", "25", "5"],
            ["Bic Pen Blue",             "Stationery",      "20", "12","pcs",     "","300","50"],
            ["Exercise Book 96pg",       "Stationery",      "60", "38","pcs",     "","200","30"],
            ["A4 Copy Paper ream",       "Stationery",     "700","455","ream",    "","30", "5"],
            ["Energizer AA 4s",          "Electronics",    "220","143","pack",    "6001006000011", "80","15"],
            ["USB-C Charger",            "Electronics",    "350","210","pcs",     "","40", "8"],
            ["Tomatoes 1kg",             "Food",            "80", "50","kg",      "","100","20"],
            ["Sukuma Wiki bunch",        "Food",            "20", "12","bunch",   "","150","30"],
        ]
        try:
            with open(path,"w",newline="",encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(headers)
                w.writerows(samples)
            return True, f"Sample CSV with {len(samples)} items saved."
        except Exception as e:
            return False, str(e)

    def import_from_csv(self, path, user_id, username):
        """Import products from CSV. Returns (ok, added, skipped, errors)."""
        import csv
        REQUIRED = {"name","price"}
        added = 0; skipped = 0; errors = []

        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    return False, "CSV file is empty or has no headers.", 0, []
                fields_lower = {h.strip().lower(): h for h in reader.fieldnames}
                missing = REQUIRED - set(fields_lower.keys())
                if missing:
                    return False, f"CSV missing required columns: {missing}", 0, []

                def get(row, key, default=""):
                    actual = fields_lower.get(key)
                    return row.get(actual, default).strip() if actual else default

                rows = list(reader)

            for i, row in enumerate(rows, start=2):
                name = get(row,"name")
                if not name: errors.append(f"Row {i}: name is blank"); continue
                # Check duplicate
                conn = get_connection()
                exists = conn.execute(
                    "SELECT id FROM products WHERE name=? AND is_active=1",(name,)
                ).fetchone()
                conn.close()
                if exists:
                    skipped += 1; continue

                ok, msg = self.add_product(
                    name,
                    get(row,"price","0"),
                    get(row,"cost","0"),
                    get(row,"category","General"),
                    get(row,"unit","pcs"),
                    get(row,"barcode",""),
                    get(row,"quantity","0"),
                    get(row,"low_stock_threshold",get(row,"low_stock","5")),
                    user_id, username,
                )
                if ok: added += 1
                elif "barcode already exists" in msg.lower() or "already exist" in msg.lower():
                    skipped += 1
                else:
                    errors.append(f"Row {i} '{name}': {msg}")

            return True, added, skipped, errors
        except Exception as e:
            return False, str(e), 0, []

inventory_manager = InventoryManager()

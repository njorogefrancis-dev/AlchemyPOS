import csv, os
from datetime import datetime, timedelta
from database.db import get_connection, get_setting

class ReportManager:

    def get_sales_report(self, period="today", date_from=None, date_to=None,
                         cashier=None, method=None):
        conn = get_connection()
        now  = datetime.now()

        if date_from and date_to:
            df, dt = date_from, date_to
        elif period == "today":
            df = dt = now.strftime("%Y-%m-%d")
        elif period == "week":
            df = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
            dt = now.strftime("%Y-%m-%d")
        elif period == "month":
            df = now.strftime("%Y-%m-01")
            dt = now.strftime("%Y-%m-%d")
        elif period == "year":
            df = now.strftime("%Y-01-01")
            dt = now.strftime("%Y-%m-%d")
        else:
            df = dt = now.strftime("%Y-%m-%d")

        sql = """SELECT date(s.created_at) AS day,
                        COUNT(*) AS tx_count,
                        COALESCE(SUM(s.total),0) AS revenue,
                        COALESCE(SUM(s.discount),0) AS discounts,
                        COALESCE(SUM(s.tax),0) AS taxes
                 FROM sales s LEFT JOIN users u ON u.id=s.cashier_id
                 WHERE s.status='completed'
                   AND date(s.created_at) BETWEEN ? AND ?"""
        params = [df, dt]
        if cashier:
            sql += " AND u.full_name=?"
            params.append(cashier)
        if method:
            sql += " AND s.payment_method=?"
            params.append(method)
        sql += " GROUP BY day ORDER BY day DESC"
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_sales_detail(self, date_from=None, date_to=None, cashier=None,
                         method=None, search=None, limit=500):
        conn   = get_connection()
        now    = datetime.now()
        df = date_from or now.strftime("%Y-%m-%d")
        dt = date_to   or now.strftime("%Y-%m-%d")

        sql = """SELECT s.id, s.receipt_number, u.full_name AS cashier,
                        s.subtotal, s.discount, s.tax, s.total,
                        s.payment_method, s.amount_tendered, s.change_given,
                        s.status, s.created_at
                 FROM sales s LEFT JOIN users u ON u.id=s.cashier_id
                 WHERE date(s.created_at) BETWEEN ? AND ?"""
        params = [df, dt]
        if cashier and cashier != "All":
            sql += " AND u.full_name=?"; params.append(cashier)
        if method  and method  != "All":
            sql += " AND s.payment_method=?"; params.append(method)
        if search:
            sql += " AND (LOWER(s.receipt_number) LIKE LOWER(?) OR LOWER(u.full_name) LIKE LOWER(?) OR LOWER(s.payment_method) LIKE LOWER(?))"
            params += [f"%{search}%", f"%{search}%", f"%{search}%"]
        sql += " ORDER BY s.created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_top_products(self, period="today", date_from=None, date_to=None, limit=20):
        conn = get_connection()
        now  = datetime.now()
        if date_from and date_to:
            df, dt = date_from, date_to
        elif period == "today":
            df = dt = now.strftime("%Y-%m-%d")
        elif period == "week":
            df = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
            dt = now.strftime("%Y-%m-%d")
        elif period == "month":
            df = now.strftime("%Y-%m-01"); dt = now.strftime("%Y-%m-%d")
        elif period == "year":
            df = now.strftime("%Y-01-01"); dt = now.strftime("%Y-%m-%d")
        else:
            df = dt = now.strftime("%Y-%m-%d")

        rows = conn.execute("""SELECT si.product_name, SUM(si.quantity) AS total_qty,
                                      SUM(si.subtotal) AS total_revenue
                               FROM sale_items si JOIN sales s ON s.id=si.sale_id
                               WHERE s.status='completed' AND date(s.created_at) BETWEEN ? AND ?
                               GROUP BY si.product_name ORDER BY total_revenue DESC LIMIT ?""",
                            (df, dt, limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_cashier_summary(self, date_from=None, date_to=None):
        conn = get_connection()
        now  = datetime.now()
        df = date_from or now.strftime("%Y-%m-%d")
        dt = date_to   or now.strftime("%Y-%m-%d")
        rows = conn.execute("""SELECT u.full_name AS cashier, COUNT(*) AS tx_count,
                                      SUM(s.total) AS revenue,
                                      AVG(s.total) AS avg_sale
                               FROM sales s JOIN users u ON u.id=s.cashier_id
                               WHERE s.status='completed' AND date(s.created_at) BETWEEN ? AND ?
                               GROUP BY u.full_name ORDER BY revenue DESC""",
                            (df, dt)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_payment_split(self, date_from=None, date_to=None, method=None):
        conn = get_connection()
        now  = datetime.now()
        df = date_from or now.strftime("%Y-%m-%d")
        dt = date_to   or now.strftime("%Y-%m-%d")
        sql = """SELECT payment_method, COUNT(*) AS count,
                        SUM(total) AS total
                 FROM sales WHERE status='completed'
                 AND date(created_at) BETWEEN ? AND ?"""
        params = [df, dt]
        if method and method != "All":
            sql += " AND payment_method=?"; params.append(method)
        sql += " GROUP BY payment_method ORDER BY total DESC"
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_profit(self, date_from=None, date_to=None, cashier=None, method=None):
        """Profit = sum(sale_items.subtotal - cost*qty) respecting filters."""
        conn = get_connection()
        now  = datetime.now()
        df = date_from or now.strftime("%Y-%m-%d")
        dt = date_to   or now.strftime("%Y-%m-%d")
        sql = """SELECT
                    SUM(si.subtotal) AS revenue,
                    SUM(si.quantity * COALESCE(p.cost, 0)) AS total_cost
                 FROM sale_items si
                 JOIN sales s ON s.id = si.sale_id
                 LEFT JOIN products p ON p.id = si.product_id
                 LEFT JOIN users u ON u.id = s.cashier_id
                 WHERE s.status='completed'
                   AND date(s.created_at) BETWEEN ? AND ?"""
        params = [df, dt]
        if cashier and cashier != "All":
            sql += " AND u.full_name=?"; params.append(cashier)
        if method and method != "All":
            sql += " AND s.payment_method=?"; params.append(method)
        row = conn.execute(sql, params).fetchone()
        conn.close()
        if not row or row["revenue"] is None: return 0.0
        return round(float(row["revenue"]) - float(row["total_cost"] or 0), 2)

    def get_audit_logs(self, limit=300):
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_cashier_list(self):
        conn = get_connection()
        rows = conn.execute(
            "SELECT DISTINCT u.full_name FROM sales s JOIN users u ON u.id=s.cashier_id ORDER BY u.full_name"
        ).fetchall()
        conn.close()
        return ["All"] + [r[0] for r in rows if r[0]]

    # ── Exports ───────────────────────────────────────────────────────────────
    def export_sales_csv(self, path, rows=None):
        try:
            if rows is None:
                rows = self.get_sales_detail(
                    date_from="2000-01-01",
                    date_to=datetime.now().strftime("%Y-%m-%d"))
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "receipt_number","created_at","cashier","payment_method",
                    "subtotal","discount","tax","total","amount_tendered","change_given","status"])
                w.writeheader()
                w.writerows(rows)
            return True, f"Exported {len(rows)} rows to CSV."
        except Exception as e:
            return False, str(e)

    def export_sales_xml(self, path, rows=None):
        try:
            from xml.etree.ElementTree import Element, SubElement, ElementTree, indent
            if rows is None:
                rows = self.get_sales_detail(
                    date_from="2000-01-01",
                    date_to=datetime.now().strftime("%Y-%m-%d"))
            root = Element("sales")
            root.set("exported", datetime.now().isoformat())
            root.set("count", str(len(rows)))
            for r in rows:
                s = SubElement(root, "sale")
                for k, v in r.items():
                    SubElement(s, k).text = str(v) if v is not None else ""
            try: indent(root, space="  ")
            except: pass
            ElementTree(root).write(path, encoding="unicode", xml_declaration=True)
            return True, f"Exported {len(rows)} rows to XML."
        except Exception as e:
            return False, str(e)

    def export_sales_pdf(self, path, rows=None, date_from=None, date_to=None):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                            Paragraph, Spacer)
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT

            if rows is None:
                rows = self.get_sales_detail(
                    date_from=date_from or "2000-01-01",
                    date_to=date_to or datetime.now().strftime("%Y-%m-%d"))

            sym   = get_setting("currency_symbol","KSh")
            shop  = get_setting("shop_name","AlchemyPOS")
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("title", fontSize=16, fontName="Helvetica-Bold",
                                         alignment=TA_CENTER, spaceAfter=6)
            sub_style   = ParagraphStyle("sub",   fontSize=9,  fontName="Helvetica",
                                         alignment=TA_CENTER, spaceAfter=12, textColor=colors.grey)
            hdr_style   = ParagraphStyle("hdr",   fontSize=9,  fontName="Helvetica-Bold",
                                         textColor=colors.HexColor("#F0883E"))

            doc   = SimpleDocTemplate(path, pagesize=A4,
                                      leftMargin=15*mm, rightMargin=15*mm,
                                      topMargin=20*mm, bottomMargin=15*mm)
            story = []
            story.append(Paragraph(shop, title_style))
            story.append(Paragraph("Sales Report", sub_style))
            if date_from and date_to:
                story.append(Paragraph(f"Period: {date_from}  to  {date_to}", sub_style))
            story.append(Spacer(1, 6))

            # Summary row
            total_rev = sum(float(r.get("total",0)) for r in rows)
            total_disc = sum(float(r.get("discount",0)) for r in rows)
            summary_data = [
                ["Total Transactions", "Total Revenue", "Total Discounts"],
                [str(len(rows)), f"{sym} {total_rev:,.2f}", f"{sym} {total_disc:,.2f}"],
            ]
            st = Table(summary_data, colWidths=[60*mm, 60*mm, 60*mm])
            st.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0D1117")),
                ("TEXTCOLOR",  (0,0), (-1,0), colors.HexColor("#F0883E")),
                ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",   (0,0), (-1,-1), 9),
                ("ALIGN",      (0,0), (-1,-1), "CENTER"),
                ("ROWBACKGROUNDS", (0,1), (-1,-1),
                 [colors.HexColor("#1C2128"), colors.HexColor("#21262D")]),
                ("TEXTCOLOR",  (0,1), (-1,-1), colors.white),
                ("GRID",       (0,0), (-1,-1), 0.3, colors.HexColor("#30363D")),
                ("TOPPADDING", (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ]))
            story.append(st)
            story.append(Spacer(1, 10))

            # Detail table
            headers = ["Receipt #", "Date & Time", "Cashier", "Method",
                       "Subtotal", "Disc", "Tax", "Total"]
            col_w   = [32*mm, 32*mm, 30*mm, 22*mm, 22*mm, 16*mm, 14*mm, 22*mm]
            data    = [headers]
            for r in rows:
                data.append([
                    r.get("receipt_number",""),
                    (r.get("created_at","") or "")[:16],
                    r.get("cashier","")   or "",
                    (r.get("payment_method","") or "").upper(),
                    f"{sym}{float(r.get('subtotal',0)):,.2f}",
                    f"{sym}{float(r.get('discount',0)):,.2f}",
                    f"{sym}{float(r.get('tax',0)):,.2f}",
                    f"{sym}{float(r.get('total',0)):,.2f}",
                ])
            dt_tbl = Table(data, colWidths=col_w, repeatRows=1)
            dt_tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#0D1117")),
                ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
                ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",      (0,0), (-1,-1), 8),
                ("ALIGN",         (4,0), (-1,-1), "RIGHT"),
                ("ROWBACKGROUNDS",(0,1), (-1,-1),
                 [colors.HexColor("#1C2128"), colors.HexColor("#21262D")]),
                ("TEXTCOLOR",     (0,1), (-1,-1), colors.HexColor("#E6EDF3")),
                ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#30363D")),
                ("TOPPADDING",    (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ]))
            story.append(dt_tbl)
            doc.build(story)
            return True, f"PDF exported: {len(rows)} rows."
        except Exception as e:
            return False, str(e)

    def export_inventory_csv(self, path):
        try:
            from inventory.inventory import inventory_manager
            rows = inventory_manager.get_all_for_export()
            with open(path, "w", newline="", encoding="utf-8") as f:
                if not rows: return False, "No products to export."
                w = csv.DictWriter(f, fieldnames=rows[0].keys())
                w.writeheader(); w.writerows(rows)
            return True, f"Exported {len(rows)} products."
        except Exception as e:
            return False, str(e)

    def export_inventory_xml(self, path):
        try:
            from xml.etree.ElementTree import Element, SubElement, ElementTree, indent
            from inventory.inventory import inventory_manager
            rows = inventory_manager.get_all_for_export()
            root = Element("inventory")
            root.set("exported", datetime.now().isoformat())
            for r in rows:
                p = SubElement(root, "product")
                for k, v in r.items():
                    SubElement(p, k).text = str(v) if v is not None else ""
            try: indent(root, space="  ")
            except: pass
            ElementTree(root).write(path, encoding="unicode", xml_declaration=True)
            return True, f"Exported {len(rows)} products."
        except Exception as e:
            return False, str(e)

    def export_inventory_pdf(self, path):
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.enums import TA_CENTER
            from inventory.inventory import inventory_manager

            sym   = get_setting("currency_symbol","KSh")
            shop  = get_setting("shop_name","AlchemyPOS")
            rows  = inventory_manager.get_all_for_export()
            doc   = SimpleDocTemplate(path, pagesize=landscape(A4),
                                      leftMargin=12*mm, rightMargin=12*mm,
                                      topMargin=15*mm, bottomMargin=12*mm)
            title_sty = ParagraphStyle("t", fontSize=14, fontName="Helvetica-Bold",
                                        alignment=TA_CENTER, spaceAfter=4)
            sub_sty   = ParagraphStyle("s", fontSize=9, fontName="Helvetica",
                                        alignment=TA_CENTER, spaceAfter=10,
                                        textColor=colors.grey)
            story = [Paragraph(shop, title_sty),
                     Paragraph("Inventory Report — " + datetime.now().strftime("%Y-%m-%d %H:%M"), sub_sty)]

            headers = ["Name","Category","Price","Cost","Stock","Min","Unit"]
            col_w   = [55*mm,30*mm,22*mm,22*mm,20*mm,18*mm,15*mm]
            data    = [headers]
            for r in rows:
                data.append([
                    r["name"], r.get("category",""),
                    f"{sym}{r['price']:.2f}", f"{sym}{r['cost']:.2f}",
                    f"{r['quantity']:.0f}", f"{r['low_stock_threshold']:.0f}",
                    r.get("unit","pcs"),
                ])
            tbl = Table(data, colWidths=col_w, repeatRows=1)
            tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#0D1117")),
                ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
                ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",      (0,0), (-1,-1), 8),
                ("ROWBACKGROUNDS",(0,1), (-1,-1),
                 [colors.HexColor("#1C2128"), colors.HexColor("#21262D")]),
                ("TEXTCOLOR",     (0,1), (-1,-1), colors.HexColor("#E6EDF3")),
                ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#30363D")),
                ("TOPPADDING",    (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ]))
            story.append(tbl)
            doc.build(story)
            return True, f"PDF exported: {len(rows)} products."
        except Exception as e:
            return False, str(e)

report_manager = ReportManager()

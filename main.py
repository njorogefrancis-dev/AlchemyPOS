#!/usr/bin/env python3
"""AlchemyPOS — Professional Point of Sale System"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import datetime, timedelta

from database.db import (init_database, get_setting, set_setting,
                          is_first_run, get_categories, get_payment_methods,
                          log_action, get_connection)
from authentication.auth import auth
from inventory.inventory import inventory_manager
from sales.sales import sales_manager
from reporting.reports import report_manager
from backup_manager.backup import backup_manager

# ══════════════════════ THEMES ═══════════════════════════════════════════════
THEMES = {
    "dark": {
        "BG":     "#0D1117", "SIDEBAR": "#161B22", "CARD":   "#1C2128",
        "CARD2":  "#21262D", "BORDER":  "#30363D", "ACCENT": "#F0883E",
        "BLUE":   "#58A6FF", "GREEN":   "#3FB950", "RED":    "#F85149",
        "YELLOW": "#D29922", "TEXT":    "#E6EDF3", "TEXT2":  "#8B949E",
        "TEXT3":  "#6E7681", "HOVER":   "#262C36", "SEL":    "#1F3A5F",
        "IN_BG":  "#0D1117",
    },
    "light": {
        "BG":     "#F6F8FA", "SIDEBAR": "#FFFFFF", "CARD":   "#FFFFFF",
        "CARD2":  "#F0F2F5", "BORDER":  "#D0D7DE", "ACCENT": "#E36209",
        "BLUE":   "#0969DA", "GREEN":   "#1A7F37", "RED":    "#CF222E",
        "YELLOW": "#9A6700", "TEXT":    "#1F2328", "TEXT2":  "#656D76",
        "TEXT3":  "#848D97", "HOVER":   "#EAF0F6", "SEL":    "#DDF4FF",
        "IN_BG":  "#FFFFFF",
    },
}
T = THEMES["dark"].copy()   # active theme dict, mutated on theme switch

def apply_theme(name):
    global T
    T.update(THEMES.get(name, THEMES["dark"]))
    set_setting("theme", name)

def F(sz, bold=False):
    return ("Courier New", sz, "bold" if bold else "normal")

PALS = {}
def _make_pals():
    PALS.update({
        "primary": (T["ACCENT"], "#000"),
        "blue":    (T["BLUE"],   "#000"),
        "green":   (T["GREEN"],  "#000"),
        "red":     (T["RED"],    "#fff"),
        "ghost":   (T["CARD2"],  T["TEXT2"]),
        "dark":    (T["BORDER"], T["TEXT"]),
        "yellow":  (T["YELLOW"],"#000"),
        "sidebar": (T["SIDEBAR"],T["TEXT2"]),
    })

def btn(parent, text, cmd, style="primary", pad=(12,7), **kw):
    _make_pals()
    bg, fg = PALS.get(style, PALS["ghost"])
    b = tk.Button(parent, text=text, command=cmd,
                  bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                  font=F(10,True), relief="flat", cursor="hand2",
                  padx=pad[0], pady=pad[1], bd=0, highlightthickness=0, **kw)
    return b

def lbl(parent, text="", sz=10, bold=False, color=None, **kw):
    bg = kw.pop("bg", None) or _parent_bg(parent)
    fg = color or T["TEXT"]
    return tk.Label(parent, text=text, font=F(sz, bold),
                    fg=fg, bg=bg, **kw)

def _parent_bg(parent):
    try: return parent.cget("bg")
    except: return T["BG"]

def entry(parent, var, show=None, width=None, big=False, **kw):
    cfg = dict(textvariable=var, font=F(13 if big else 10),
               bg=T["IN_BG"], fg=T["TEXT"], insertbackground=T["TEXT"],
               relief="flat", highlightbackground=T["BORDER"], highlightthickness=1)
    if show:  cfg["show"]  = show
    if width: cfg["width"] = width
    cfg.update(kw)
    return tk.Entry(parent, **cfg)

def combo(parent, var, values, width=18):
    s = ttk.Style(); s.theme_use("default")
    s.configure("C.TCombobox",
                fieldbackground=T["IN_BG"], background=T["IN_BG"],
                foreground=T["TEXT"], selectbackground=T["SEL"],
                selectforeground=T["TEXT"], arrowcolor=T["TEXT2"])
    cb = ttk.Combobox(parent, textvariable=var, values=values,
                      width=width, style="C.TCombobox", state="readonly",
                      font=F(10))
    return cb

def hsep(parent, pad=8):
    tk.Frame(parent, bg=T["BORDER"], height=1).pack(fill="x", padx=pad, pady=4)

def vsep(parent):
    tk.Frame(parent, bg=T["BORDER"], width=1).pack(fill="y", padx=4, pady=4, side="left")

def _watermark(parent, bg=None):
    """Place a faded developer watermark at the bottom of a window/frame."""
    bg = bg or T.get("BG","#0D1117")
    # Pick a colour that's just slightly brighter than the background
    fg = T.get("TEXT3","#484F58")
    tk.Label(parent,
             text="Developer: njorogefrancis  |  njorogefrancis.dev@gmail.com  |  0115634345",
             font=("Courier New", 7), fg=fg, bg=bg,
             anchor="center").pack(side="bottom", fill="x", pady=(1,2), padx=4)

def scrolled_frame(parent, bg=None):
    """Returns (outer_frame, inner_frame) — inner_frame is the scrollable content area."""
    bg = bg or T["BG"]
    outer = tk.Frame(parent, bg=bg)
    can   = tk.Canvas(outer, bg=bg, highlightthickness=0)
    sb    = ttk.Scrollbar(outer, orient="vertical", command=can.yview)
    can.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    can.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(can, bg=bg)
    win   = can.create_window((0,0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda e: can.configure(scrollregion=can.bbox("all")))
    can.bind("<Configure>",   lambda e: can.itemconfig(win, width=e.width))
    def _on_mw(e):  can.yview_scroll(int(-1*(e.delta/120)), "units")
    def _on_up(e):  can.yview_scroll(-1, "units")
    def _on_dn(e):  can.yview_scroll( 1, "units")
    def _bind_scroll(e):
        can.bind_all("<MouseWheel>", _on_mw)
        can.bind_all("<Button-4>",   _on_up)
        can.bind_all("<Button-5>",   _on_dn)
    def _unbind_scroll(e):
        can.unbind_all("<MouseWheel>")
        can.unbind_all("<Button-4>")
        can.unbind_all("<Button-5>")
    can.bind("<Enter>", _bind_scroll)
    can.bind("<Leave>", _unbind_scroll)
    inner.bind("<Enter>", _bind_scroll)
    inner.bind("<Leave>", _unbind_scroll)
    # Store handlers so propagate_scroll() can attach them to dynamic children
    inner._sf_bind   = _bind_scroll
    inner._sf_unbind = _unbind_scroll
    return outer, inner


def propagate_scroll(widget):
    """Attach the parent scrolled_frame's scroll handlers to every descendant.
    Call after populating an inner frame so hovering over any child widget
    also activates scrolling."""
    bind_fn   = getattr(widget, "_sf_bind",   None)
    unbind_fn = getattr(widget, "_sf_unbind", None)
    if bind_fn is None:
        return
    def _attach(w):
        try:
            w.bind("<Enter>", bind_fn)
            w.bind("<Leave>", unbind_fn)
        except Exception:
            pass
        for child in w.winfo_children():
            _attach(child)
    _attach(widget)

def scroll_canvas_to_content(canvas, content_frame):
    """Helper to enable scroll propagation on a canvas. Call after populating content."""
    def _pos_scroll(e):
        if not canvas.winfo_ismapped(): return
        canvas.yview_scroll(int(-1*(e.delta/120)),"units")
    def _pos_up(e):
        if canvas.winfo_ismapped(): canvas.yview_scroll(-1,"units")
    def _pos_dn(e):
        if canvas.winfo_ismapped(): canvas.yview_scroll(1,"units")
    canvas.bind("<MouseWheel>", _pos_scroll)
    canvas.bind("<Button-4>",   _pos_up)
    canvas.bind("<Button-5>",   _pos_dn)
    content_frame.bind("<MouseWheel>", _pos_scroll)
    content_frame.bind("<Button-4>",   _pos_up)
    content_frame.bind("<Button-5>",   _pos_dn)
    # Propagate to all descendants
    def _attach_to_children(w):
        try:
            w.bind("<MouseWheel>", _pos_scroll)
            w.bind("<Button-4>",   _pos_up)
            w.bind("<Button-5>",   _pos_dn)
        except Exception:
            pass
        for child in w.winfo_children():
            _attach_to_children(child)
    _attach_to_children(content_frame)


def apply_tv(name):
    s = ttk.Style(); s.theme_use("default")
    s.configure(f"{name}.Treeview",
                background=T["CARD"], foreground=T["TEXT"],
                fieldbackground=T["CARD"], rowheight=30, font=F(9), borderwidth=0)
    s.configure(f"{name}.Treeview.Heading",
                background=T["CARD2"], foreground=T["TEXT3"],
                font=F(9,True), relief="flat")
    s.map(f"{name}.Treeview",
          background=[("selected", T["SEL"])],
          foreground=[("selected", T["TEXT"])])

SECURITY_QUESTIONS = [
    "What is the name of your first pet?",
    "What city were you born in?",
    "What is your mother's maiden name?",
    "What was the name of your first school?",
    "What is your favourite food?",
    "What is the name of your childhood best friend?",
    "What was your childhood nickname?",
    "What is your oldest sibling's middle name?",
    "In what city did your parents meet?",
    "What was the make of your first car?",
    "What is the name of the street you grew up on?",
    "What was the name of your primary school teacher?",
    "What is the name of your favourite childhood sports team?",
    "What was the first concert you attended?",
    "What is the name of the hospital where you were born?",
]

# 3 security questions per account
NUM_SEC_QUESTIONS = 3

# ═══════════════════════════ APP ═════════════════════════════════════════════
class AlchemyPOS(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AlchemyPOS")
        self.geometry("1440x880")
        self.minsize(1100, 700)
        init_database()
        theme = get_setting("theme","dark")
        apply_theme(theme)
        self.configure(bg=T["BG"])
        self._nav_btns = {}
        if is_first_run():
            self._show_setup()
        else:
            self._show_login()
        self.mainloop()

    def _clear(self):
        for w in self.winfo_children(): w.destroy()

    def _clear_content(self):
        for w in self._content.winfo_children(): w.destroy()

    # ─── FIRST-RUN SETUP ─────────────────────────────────────────────────────
    def _show_setup(self):
        self._clear()
        self.title("AlchemyPOS — Initial Setup")
        self.configure(bg=T["BG"])

        # Full-window scrollable container
        sf_outer, sf_inner = scrolled_frame(self, bg=T["BG"])
        sf_outer.pack(fill="both", expand=True)

        outer = tk.Frame(sf_inner, bg=T["BG"])
        outer.pack(expand=True, anchor="center", pady=20)

        lbl(outer, "⬡", 52, True, T["ACCENT"], bg=T["BG"]).pack()
        lbl(outer, "WELCOME TO ALCHEMYPOS", 20, True, bg=T["BG"]).pack()
        lbl(outer, "Create your administrator account to get started.",
            9, color=T["TEXT3"], bg=T["BG"]).pack(pady=(4,20))

        card = tk.Frame(outer, bg=T["CARD"], padx=44, pady=36,
                        highlightbackground=T["BORDER"], highlightthickness=1)
        card.pack()

        lbl(card, "ADMIN ACCOUNT SETUP", 12, True, bg=T["CARD"]).pack(anchor="w", pady=(0,16))

        fields = {}
        for label_txt, key, show in [
            ("Full Name",        "full_name", None),
            ("Username",         "username",  None),
            ("Password",         "password",  "●"),
            ("Confirm Password", "confirm",   "●"),
        ]:
            lbl(card, label_txt, 8, color=T["TEXT3"], bg=T["CARD"]).pack(anchor="w")
            v = tk.StringVar()
            e = entry(card, v, show=show)
            e.pack(fill="x", ipady=9, pady=(3,10))
            fields[key] = v

        lbl(card, "Security Questions (choose 3)", 9, True, T["ACCENT"], bg=T["CARD"]).pack(anchor="w", pady=(8,2))
        sq_vars = []; sa_vars = []
        for qi in range(NUM_SEC_QUESTIONS):
            remaining = [q for q in SECURITY_QUESTIONS if not any(v.get()==q for v in sq_vars)]
            sqv = tk.StringVar(value=SECURITY_QUESTIONS[qi*5 % len(SECURITY_QUESTIONS)])
            sav = tk.StringVar()
            lbl(card, f"Question {qi+1}", 8, color=T["TEXT3"], bg=T["CARD"]).pack(anchor="w")
            combo(card, sqv, SECURITY_QUESTIONS, width=38).pack(fill="x", pady=(2,3))
            lbl(card, f"Answer {qi+1}", 8, color=T["TEXT3"], bg=T["CARD"]).pack(anchor="w")
            entry(card, sav).pack(fill="x", ipady=7, pady=(2,8))
            sq_vars.append(sqv); sa_vars.append(sav)

        ev = tk.StringVar()
        lbl(card, "", 9, color=T["RED"], bg=T["CARD"], textvariable=ev).pack(pady=(0,8))

        def create():
            fn = fields["full_name"].get().strip()
            un = fields["username"].get().strip()
            pw = fields["password"].get()
            cp = fields["confirm"].get()
            if not fn: ev.set("Full name is required."); return
            if len(un) < 3: ev.set("Username must be at least 3 characters."); return
            if len(pw) < 6: ev.set("Password must be at least 6 characters."); return
            if pw != cp: ev.set("Passwords do not match."); return
            for i, (sqv, sav) in enumerate(zip(sq_vars, sa_vars), 1):
                if not sav.get().strip(): ev.set(f"Answer {i} is required."); return
            ok, msg = auth.add_user(un, pw, "admin", fn)
            if not ok: ev.set(msg); return
            conn = get_connection()
            row = conn.execute("SELECT id FROM users WHERE username=?", (un,)).fetchone()
            conn.close()
            if row:
                qs = [v.get() for v in sq_vars]; ans = [v.get().strip() for v in sa_vars]
                auth.set_security_questions(row[0], qs, ans)
            messagebox.showinfo("Setup Complete",
                                f"Admin account '{un}' created!\nPlease log in to continue.")
            self._show_login()

        btn(card, "CREATE ACCOUNT & CONTINUE →", create, "primary", (0,0)).pack(
            fill="x", ipady=10)

    # ─── LOGIN ───────────────────────────────────────────────────────────────
    def _show_login(self):
        self._clear()
        self.title("AlchemyPOS — Login")
        self.configure(bg=T["BG"])
        outer = tk.Frame(self, bg=T["BG"])
        outer.place(relx=.5, rely=.5, anchor="center")

        lbl(outer, "⬡", 52, True, T["ACCENT"], bg=T["BG"]).pack()
        lbl(outer, "ALCHEMYPOS", 26, True, bg=T["BG"]).pack()
        lbl(outer, "Point of Sale System", 9, color=T["TEXT3"], bg=T["BG"]).pack(pady=(2,22))

        card = tk.Frame(outer, bg=T["CARD"], padx=44, pady=36,
                        highlightbackground=T["BORDER"], highlightthickness=1)
        card.pack()
        lbl(card, "SIGN IN", 13, True, bg=T["CARD"]).pack(anchor="w", pady=(0,18))

        self._uv = tk.StringVar(); self._pv = tk.StringVar(); self._ev = tk.StringVar()
        for txt, var, show in [("USERNAME", self._uv, None), ("PASSWORD", self._pv, "●")]:
            lbl(card, txt, 8, color=T["TEXT3"], bg=T["CARD"]).pack(anchor="w")
            e = entry(card, var, show=show)
            e.pack(fill="x", ipady=9, pady=(3,12))
            if txt == "USERNAME": ue = e

        lbl(card, "", 9, color=T["RED"], bg=T["CARD"], textvariable=self._ev).pack(pady=(0,8))
        btn(card, "SIGN IN  →", self._do_login, "primary", (0,0)).pack(fill="x", ipady=10)
        _watermark(card)

        fp = tk.Button(card, text="Forgot password?", command=self._forgot_password,
                       bg=T["CARD"], fg=T["BLUE"], font=F(9), relief="flat",
                       cursor="hand2", bd=0, highlightthickness=0)
        fp.pack(pady=(10,0))
        ue.focus_set()
        self.bind("<Return>", lambda _: self._do_login())

    def _do_login(self):
        ok, msg = auth.login(self._uv.get().strip(), self._pv.get())
        if ok:
            self.unbind("<Return>")
            self._build_shell()
        else:
            self._ev.set(msg); self._pv.set("")

    def _forgot_password(self):
        un = self._uv.get().strip()
        if not un:
            un = simpledialog.askstring("Forgot Password", "Enter your username:", parent=self)
        if not un: return
        qs = auth.get_security_questions(un)
        if not qs:
            messagebox.showerror("Not Found",
                                 "Username not found or no security questions set.", parent=self)
            return
        win = tk.Toplevel(self); win.title("Reset Password")
        win.configure(bg=T["BG"]); win.geometry("460x520")
        win.transient(self); win.resizable(False, False); win.after(50, lambda: win.grab_set() if win.winfo_exists() else None)
        _watermark(win)

        outer, inner = scrolled_frame(win, bg=T["BG"])
        outer.pack(fill="both", expand=True)
        win.after(120, lambda: propagate_scroll(inner))

        lbl(inner, "RESET PASSWORD", 14, True, T["ACCENT"], bg=T["BG"]).pack(pady=(24,4))
        lbl(inner, f"Account:  {un}", 9, color=T["TEXT3"], bg=T["BG"]).pack(pady=(0,8))
        lbl(inner, "Answer all security questions to verify your identity.",
            9, color=T["TEXT3"], bg=T["BG"]).pack(pady=(0,14))

        frm = tk.Frame(inner, bg=T["BG"]); frm.pack(fill="x", padx=36)
        av_vars = []
        for i, q in enumerate(qs, 1):
            lbl(frm, f"Question {i}:", 8, True, T["TEXT3"], bg=T["BG"]).pack(anchor="w")
            lbl(frm, q, 10, False, bg=T["BG"], wraplength=360,
                justify="left").pack(anchor="w", pady=(2,4))
            lbl(frm, f"Answer {i}:", 8, color=T["TEXT3"], bg=T["BG"]).pack(anchor="w")
            av = tk.StringVar()
            entry(frm, av).pack(fill="x", ipady=7, pady=(2,10))
            av_vars.append(av)

        lbl(frm, "New Password:", 9, color=T["TEXT3"], bg=T["BG"]).pack(anchor="w", pady=(4,1))
        pv = tk.StringVar()
        entry(frm, pv, show="●").pack(fill="x", ipady=7, pady=(2,10))

        ev = tk.StringVar()
        lbl(frm, "", 9, color=T["RED"], bg=T["BG"], textvariable=ev).pack(pady=3)

        def do_reset():
            answers = [v.get() for v in av_vars]
            if not auth.verify_security_answers(un, answers):
                ev.set("One or more answers are incorrect. Try again."); return
            ok, msg = auth.reset_own_password(un, pv.get())
            if ok:
                win.destroy()
                messagebox.showinfo("Success", "Password reset! Please log in.", parent=self)
            else:
                ev.set(msg)

        btn(frm, "RESET PASSWORD", do_reset, "primary", (0,0)).pack(fill="x", ipady=9, pady=(4,4))
        btn(frm, "Cancel", win.destroy, "ghost").pack(fill="x")

    # ─── SHELL ───────────────────────────────────────────────────────────────
    def _build_shell(self):
        self._clear()
        self.configure(bg=T["BG"])
        self.title(f"AlchemyPOS  —  {auth.current_user['full_name']}  [{auth.current_user['role'].upper()}]")

        top = tk.Frame(self, bg=T["SIDEBAR"], height=48)
        top.pack(side="top", fill="x"); top.pack_propagate(False)
        lbl(top, "⬡  ALCHEMYPOS", 12, True, T["ACCENT"], bg=T["SIDEBAR"]).pack(side="left", padx=18)
        self._clk = tk.StringVar()
        lbl(top, "", 9, color=T["TEXT3"], bg=T["SIDEBAR"],
            textvariable=self._clk).pack(side="left", padx=10)
        self._tick()

        btn(top, "⏻  Logout", self._logout, "ghost", (10,5)).pack(side="right", padx=12, pady=6)
        lbl(top, f"{auth.current_user['full_name']}  ·  {auth.current_user['role'].upper()}",
            9, color=T["TEXT2"], bg=T["SIDEBAR"]).pack(side="right", padx=6)

        # Theme toggle
        th_btn = tk.Button(top, text="☀" if get_setting("theme","dark")=="dark" else "🌙",
                           command=self._toggle_theme,
                           bg=T["SIDEBAR"], fg=T["TEXT2"], font=F(14), relief="flat",
                           cursor="hand2", bd=0, highlightthickness=0, padx=6)
        th_btn.pack(side="right", pady=6)
        self._th_btn = th_btn

        body = tk.Frame(self, bg=T["BG"]); body.pack(fill="both", expand=True)
        self._sb = tk.Frame(body, bg=T["SIDEBAR"], width=200)
        self._sb.pack(side="left", fill="y"); self._sb.pack_propagate(False)
        self._build_sidebar()
        self._content = tk.Frame(body, bg=T["BG"])
        self._content.pack(side="left", fill="both", expand=True)

        self.after(80, lambda: self._nav_to("pos"))

    def _toggle_theme(self):
        current = get_setting("theme","dark")
        new = "light" if current == "dark" else "dark"
        apply_theme(new)
        messagebox.showinfo("Theme Changed",
                            f"Switched to {new.title()} theme.\nRestart AlchemyPOS to apply fully.",
                            parent=self)

    def _tick(self):
        self._clk.set(datetime.now().strftime("%a %d %b %Y   %H:%M:%S"))
        self.after(1000, self._tick)

    def _build_sidebar(self):
        for w in self._sb.winfo_children(): w.destroy()
        self._nav_btns.clear()
        lbl(self._sb, get_setting("shop_name","AlchemyPOS"), 9, True,
            T["TEXT3"], bg=T["SIDEBAR"], wraplength=180).pack(pady=(14,6), padx=10)
        hsep(self._sb)
        items = [("🖥   POS Terminal", "pos")]
        if auth.can_access_inventory():
            items.append(("📦   Inventory","inventory"))
        if auth.is_admin():
            items += [("📊   Reports","reports"),
                      ("👥   Users","users"),("💾   Backups","backups"),
                      ("⚙    Settings","settings"),
                      ("📋   Audit Log","audit")]
        for txt, key in items:
            b = tk.Button(self._sb, text=txt, anchor="w",
                          command=lambda k=key: self._nav_to(k),
                          font=F(10), bg=T["SIDEBAR"], fg=T["TEXT2"],
                          activebackground=T["HOVER"], activeforeground=T["TEXT"],
                          relief="flat", cursor="hand2", padx=14, pady=10,
                          bd=0, highlightthickness=0)
            b.pack(fill="x", padx=4, pady=1)
            self._nav_btns[key] = b

    def _nav_to(self, key):
        for k, b in self._nav_btns.items():
            b.config(bg=T["SEL"] if k==key else T["SIDEBAR"],
                     fg=T["ACCENT"] if k==key else T["TEXT2"])
        self._clear_content()
        {
            "pos":       self._page_pos,
            "inventory": self._page_inventory,
            "reports":   self._page_reports,
            "users":     self._page_users,
            "backups":   self._page_backups,
            "settings":  self._page_settings,
            "audit":     self._page_audit,
        }.get(key, lambda: None)()

    def _logout(self):
        if messagebox.askyesno("Logout","Log out now?", parent=self):
            auth.logout(); self._nav_btns.clear(); self._show_login()

    # ═══════════════════════════════ POS ═════════════════════════════════════
    def _page_pos(self):
        self._cart   = []
        self._sym    = get_setting("currency_symbol","KSh")
        self._tax_rt = float(get_setting("tax_rate","0"))
        self._sjob   = None
        self._loaded_prod_ids  = object()  # unique sentinel — never matches cached ids
        self._stock_labels     = {}        # {product_id: stock_label_widget}
        root = tk.Frame(self._content, bg=T["BG"]); root.pack(fill="both", expand=True)
        _watermark(root)

        # LEFT
        left = tk.Frame(root, bg=T["BG"])
        left.pack(side="left", fill="both", expand=True, padx=(12,6), pady=10)
        sf = tk.Frame(left, bg=T["CARD"], highlightbackground=T["BORDER"], highlightthickness=1)
        sf.pack(fill="x", pady=(0,6))
        lbl(sf,"🔍",13,color=T["TEXT3"],bg=T["CARD"]).pack(side="left",padx=(12,4))
        self._sq = tk.StringVar()
        se = tk.Entry(sf, textvariable=self._sq, font=F(13), bg=T["CARD"], fg=T["TEXT"],
                      insertbackground=T["TEXT"], relief="flat", highlightthickness=0)
        se.pack(side="left",fill="x",expand=True,ipady=13,padx=(0,12))
        _ph = "Search products…"
        se.insert(0,_ph)
        se.bind("<FocusIn>",  lambda e: se.delete(0,"end") if se.get()==_ph else None)
        se.bind("<FocusOut>", lambda e: se.insert(0,_ph) if not se.get() else None)
        self._sq.trace_add("write", lambda *_: self._debounce())
        se.focus_set()

        self._catbar = tk.Frame(left, bg=T["BG"]); self._catbar.pack(fill="x", pady=(0,6))
        self._selcat = "All"; self._build_cats()

        gw = tk.Frame(left, bg=T["BG"]); gw.pack(fill="both", expand=True)
        self._pc = tk.Canvas(gw, bg=T["BG"], highlightthickness=0)
        psb = ttk.Scrollbar(gw, orient="vertical", command=self._pc.yview)
        self._pc.config(yscrollcommand=psb.set)
        psb.pack(side="right",fill="y"); self._pc.pack(side="left",fill="both",expand=True)
        self._pg = tk.Frame(self._pc, bg=T["BG"])
        self._pgw = self._pc.create_window((0,0), window=self._pg, anchor="nw")
        self._pg.bind("<Configure>", lambda e: self._pc.config(scrollregion=self._pc.bbox("all")))
        self._pc.bind("<Configure>", lambda e: self._pc.itemconfig(self._pgw, width=e.width))
        def _pos_scroll(e):
            if not self._pc.winfo_ismapped(): return
            self._pc.yview_scroll(int(-1*(e.delta/120)),"units")
        def _pos_up(e):
            if self._pc.winfo_ismapped(): self._pc.yview_scroll(-1,"units")
        def _pos_dn(e):
            if self._pc.winfo_ismapped(): self._pc.yview_scroll(1,"units")
        self._pc.bind("<MouseWheel>", _pos_scroll)
        self._pc.bind("<Button-4>",   _pos_up)
        self._pc.bind("<Button-5>",   _pos_dn)
        self._pg.bind("<MouseWheel>", _pos_scroll)
        self._pg.bind("<Button-4>",   _pos_up)
        self._pg.bind("<Button-5>",   _pos_dn)

        # RIGHT cart
        right = tk.Frame(root, bg=T["SIDEBAR"], width=400,
                         highlightbackground=T["BORDER"], highlightthickness=1)
        right.pack(side="right", fill="y", padx=(0,10), pady=10)
        right.pack_propagate(False)
        ch = tk.Frame(right, bg=T["SIDEBAR"]); ch.pack(fill="x", padx=14, pady=(12,6))
        lbl(ch,"CURRENT SALE",9,True,T["TEXT3"],bg=T["SIDEBAR"]).pack(side="left")
        btn(ch,"✕ Clear",self._clear_cart,"ghost",(8,4)).pack(side="right")
        hsep(right)

        cw2 = tk.Frame(right, bg=T["SIDEBAR"]); cw2.pack(fill="both", expand=True)
        self._cc = tk.Canvas(cw2, bg=T["SIDEBAR"], highlightthickness=0)
        csb = ttk.Scrollbar(cw2, orient="vertical", command=self._cc.yview)
        self._cc.config(yscrollcommand=csb.set)
        csb.pack(side="right",fill="y"); self._cc.pack(side="left",fill="both",expand=True)
        self._ci = tk.Frame(self._cc, bg=T["SIDEBAR"])
        self._ciw = self._cc.create_window((0,0), window=self._ci, anchor="nw")
        self._ci.bind("<Configure>", lambda e: self._cc.config(scrollregion=self._cc.bbox("all")))
        self._cc.bind("<Configure>", lambda e: self._cc.itemconfig(self._ciw, width=e.width))

        hsep(right)
        tl = tk.Frame(right, bg=T["SIDEBAR"]); tl.pack(fill="x", padx=14, pady=(6,4))
        self._vitems = tk.StringVar(value="0 items")
        self._vsub   = tk.StringVar(value=f"{self._sym} 0.00")
        self._vtax   = tk.StringVar(value=f"{self._sym} 0.00")
        self._vtot   = tk.StringVar(value=f"{self._sym} 0.00")
        lbl(tl,"",8,color=T["TEXT3"],bg=T["SIDEBAR"],textvariable=self._vitems).pack(anchor="w",pady=(0,4))
        for rl, var, big in [("Subtotal",self._vsub,False),
                              (f"Tax ({self._tax_rt:.0f}%)",self._vtax,False),
                              ("TOTAL",self._vtot,True)]:
            r = tk.Frame(tl,bg=T["SIDEBAR"]); r.pack(fill="x",pady=1)
            lbl(r,rl,13 if big else 10,big,T["ACCENT"] if big else T["TEXT2"],bg=T["SIDEBAR"]).pack(side="left")
            lbl(r,"",13 if big else 10,big,T["ACCENT"] if big else T["TEXT2"],
                bg=T["SIDEBAR"],textvariable=var).pack(side="right")

        dr = tk.Frame(right,bg=T["SIDEBAR"]); dr.pack(fill="x",padx=14,pady=(2,6))
        lbl(dr,f"Discount ({self._sym})",9,color=T["TEXT3"],bg=T["SIDEBAR"]).pack(side="left")
        self._dv = tk.StringVar(value="0")
        entry(dr,self._dv,width=9).pack(side="right",ipady=4)
        self._dv.trace_add("write", lambda *_: self._recalc())

        hsep(right)
        pf = tk.Frame(right, bg=T["SIDEBAR"]); pf.pack(fill="x", padx=10, pady=(4,4))

        # Dynamic payment method buttons from DB
        methods = get_payment_methods()
        if not methods:
            methods = [("cash","Cash"),("mpesa","M-Pesa")]

        for idx, (name, label) in enumerate(methods[:6]):
            sty = "green" if name=="cash" else ("primary" if "mpesa" in name.lower() or "pochi" in name.lower() or "paybill" in name.lower() or "till" in name.lower() or "send" in name.lower() else "blue")
            b = btn(pf, f"  {label}  ", lambda m=name,l=label: self._pay(m,l), sty, (0,0))
            b.config(font=F(10,True))
            b.pack(fill="x", ipady=9, pady=(0,4))

        hsep(right)
        qp = tk.Frame(right,bg=T["SIDEBAR"]); qp.pack(fill="x",padx=10,pady=(2,10))
        qb=btn(qp,"⚡  QUICK CASH + PRINT",self._quick_cash_print,"dark",(0,0))
        qb.config(font=F(10,True)); qb.pack(fill="x",ipady=7)

        self._load_prods(); self._render_cart()

    def _build_cats(self):
        for w in self._catbar.winfo_children(): w.destroy()
        cats = ["All"] + get_categories()
        for c in cats:
            sel = (c==self._selcat)
            b = tk.Button(self._catbar, text=c, command=lambda v=c: self._pick_cat(v),
                          font=F(9,sel), bg=T["ACCENT"] if sel else T["CARD2"],
                          fg="#000" if sel else T["TEXT2"],
                          activebackground=T["ACCENT"], activeforeground="#000",
                          relief="flat", cursor="hand2", padx=10, pady=5, bd=0, highlightthickness=0)
            b.pack(side="left", padx=3, pady=2)

    def _pick_cat(self, cat):
        self._selcat = cat; self._build_cats(); self._load_prods()

    def _debounce(self):
        if self._sjob: self.after_cancel(self._sjob)
        self._sjob = self.after(180, self._load_prods)

    def _load_prods(self):
        ph = "Search products…"
        q = self._sq.get()
        if q in (ph,""): q = ""
        cat = None if self._selcat=="All" else self._selcat
        prods = inventory_manager.search_products(q, cat, limit=120, in_stock_only=True)

        # Same product list as currently displayed — just refresh stock badges
        ids = tuple(p["id"] for p in prods)
        if ids == self._loaded_prod_ids:
            self._update_stock_badges(prods)
            return

        # Different product set — full redraw
        self._loaded_prod_ids = ids
        self._stock_labels = {}

        for w in self._pg.winfo_children(): w.destroy()
        if not prods:
            lbl(self._pg,"No products found.",11,color=T["TEXT3"],bg=T["BG"]).grid(
                row=0,column=0,padx=20,pady=40)
            self._pg.update_idletasks()
            self._pc.config(scrollregion=self._pc.bbox("all"))
            return
        COLS = 4
        for i, p in enumerate(prods):
            row, col = divmod(i, COLS)
            self._pg.columnconfigure(col, weight=1, uniform="col")
            self._prod_card(p, row, col)
        # Force canvas to recalculate scroll region after drawing all cards
        self._pg.update_idletasks()
        self._pc.config(scrollregion=self._pc.bbox("all"))
        # Enable scroll propagation to product cards
        self.after(50, lambda: scroll_canvas_to_content(self._pc, self._pg))

    def _refresh_stock_badges(self):
        """Re-fetch stock from DB and update badges in-place — no widget destroy."""
        cat = None if self._selcat=="All" else self._selcat
        ph = "Search products…"
        q = self._sq.get()
        if q in (ph,""): q = ""
        prods = inventory_manager.search_products(q, cat, limit=120, in_stock_only=True)
        self._update_stock_badges(prods)

    def _update_stock_badges(self, prods):
        """No-op — stock badges removed from POS cards. Kept for compatibility."""
        pass

    def _prod_card(self, p, row, col):
        card = tk.Frame(self._pg,bg=T["CARD"],highlightbackground=T["BORDER"],highlightthickness=1)
        card.grid(row=row,column=col,padx=4,pady=4,sticky="nsew")
        inner = tk.Frame(card,bg=T["CARD"]); inner.pack(fill="both",expand=True,padx=10,pady=9)
        lbl(inner,(p.get("category") or "General").upper(),8,color=T["TEXT3"],bg=T["CARD"]).pack(anchor="w")
        lbl(inner,p["name"],10,True,bg=T["CARD"],wraplength=130,justify="left").pack(anchor="w",pady=(3,5))
        bot = tk.Frame(inner,bg=T["CARD"]); bot.pack(fill="x")
        lbl(bot,f"{self._sym} {p['price']:.2f}",14,True,T["ACCENT"],bg=T["CARD"]).pack(side="left")
        def click(prod=p):
            if prod.get("quantity",0)<=0:
                if get_setting("allow_negative_stock","0")=="1":
                    if get_setting("warn_out_of_stock","1")=="1":
                        if not messagebox.askyesno("Out of Stock",
                            f"'{prod['name']}' is out of stock.\nSelling below zero is enabled. Add anyway?",
                            parent=self): return
                else:
                    messagebox.showwarning("Out of Stock",
                        f"'{prod['name']}' is currently out of stock.\n\nRestock it in Inventory to sell it.",
                        parent=self)
                    return
            self._cart_add(prod)
        def _scroll_up(e): 
            if self._pc.winfo_ismapped(): self._pc.yview_scroll(-1,"units")
        def _scroll_dn(e): 
            if self._pc.winfo_ismapped(): self._pc.yview_scroll(1,"units")
        def _scroll_mw(e): 
            if self._pc.winfo_ismapped(): self._pc.yview_scroll(int(-1*(e.delta/120)),"units")
        for w in [card,inner,bot]+list(inner.winfo_children())+list(bot.winfo_children()):
            w.bind("<Button-1>", lambda e,cb=click: cb())
            try: w.config(cursor="hand2")
            except: pass
            w.bind("<MouseWheel>", _scroll_mw)
            w.bind("<Button-4>",   _scroll_up)
            w.bind("<Button-5>",   _scroll_dn)

    def _cart_add(self, p):
        for item in self._cart:
            if item["id"]==p["id"]:
                item["qty"]+=1; self._render_cart(); self._recalc(); return
        self._cart.append({"id":p["id"],"name":p["name"],"price":p["price"],
                           "qty":1,"max_qty":p.get("quantity",9999)})
        self._render_cart(); self._recalc()

    def _render_cart(self):
        for w in self._ci.winfo_children(): w.destroy()
        if not self._cart:
            lbl(self._ci,"Cart is empty\n\nClick a product to add it.",10,
                color=T["TEXT3"],bg=T["SIDEBAR"],justify="center").pack(pady=30,padx=10)
            self._cc.config(scrollregion=self._cc.bbox("all"))
            return
        for i, item in enumerate(self._cart):
            row = tk.Frame(self._ci,bg=T["CARD2"],highlightbackground=T["BORDER"],highlightthickness=1)
            row.pack(fill="x",padx=6,pady=2)
            inner = tk.Frame(row,bg=T["CARD2"]); inner.pack(fill="x",padx=9,pady=7)
            lbl(inner,item["name"],10,True,bg=T["CARD2"],anchor="w",justify="left",wraplength=195).pack(anchor="w")
            ctrl = tk.Frame(inner,bg=T["CARD2"]); ctrl.pack(fill="x",pady=(5,0))
            lbl(ctrl,f"{self._sym} {item['price']:.2f} × {item['qty']}  =  {self._sym} {item['price']*item['qty']:.2f}",
                9,color=T["TEXT2"],bg=T["CARD2"]).pack(side="left")
            def mk_rm(idx=i):
                def f(): self._cart.pop(idx); self._render_cart(); self._recalc()
                return f
            def mk_dec(idx=i):
                def f():
                    if self._cart[idx]["qty"]>1: self._cart[idx]["qty"]-=1
                    else: self._cart.pop(idx)
                    self._render_cart(); self._recalc()
                return f
            def mk_inc(idx=i):
                def f(): self._cart[idx]["qty"]+=1; self._render_cart(); self._recalc()
                return f
            for txt,fn,sty in [("✕",mk_rm(),"red"),("−",mk_dec(),"dark"),("＋",mk_inc(),"dark")]:
                btn(ctrl,txt,fn,sty,(7,3)).pack(side="right",padx=2)
        # Update scroll region and propagate scroll to cart items
        self._ci.update_idletasks()
        self._cc.config(scrollregion=self._cc.bbox("all"))
        self.after(30, lambda: scroll_canvas_to_content(self._cc, self._ci))

    def _recalc(self):
        try: d = float(self._dv.get() or 0)
        except: d=0
        sub = sum(i["qty"]*i["price"] for i in self._cart)
        tax = round(max(0,sub-d)*self._tax_rt/100,2)
        tot = round(max(0,sub-d)+tax,2)
        cnt = sum(i["qty"] for i in self._cart)
        self._vsub.set(f"{self._sym} {sub:.2f}")
        self._vtax.set(f"{self._sym} {tax:.2f}")
        self._vtot.set(f"{self._sym} {tot:.2f}")
        self._vitems.set(f"{cnt} item{'s' if cnt!=1 else ''}")

    def _get_totals(self):
        try: d=float(self._dv.get() or 0)
        except: d=0
        sub=sum(i["qty"]*i["price"] for i in self._cart)
        tax=round(max(0,sub-d)*self._tax_rt/100,2)
        tot=round(max(0,sub-d)+tax,2)
        return sub,d,tax,tot

    def _clear_cart(self):
        if self._cart and messagebox.askyesno("Clear Sale","Clear all items?",parent=self):
            self._cart.clear(); self._dv.set("0"); self._render_cart(); self._recalc()

    def _quick_cash_print(self):
        if not self._cart: messagebox.showwarning("Empty Cart","Add items first.",parent=self); return
        sub,d,tax,tot = self._get_totals()
        if not messagebox.askyesno("Quick Sale",
                                   f"Complete sale for {self._sym} {tot:.2f} (exact cash)?",parent=self): return
        ok,msg,sd = sales_manager.process_sale(self._cart,"cash",tot,d,
                    auth.current_user["id"],auth.current_user["full_name"])
        if ok:
            self._cart.clear(); self._dv.set("0"); self._render_cart(); self._recalc()
            self._refresh_stock_badges()
            self._show_receipt(sd, auto_print=True)
        else: messagebox.showerror("Error",msg,parent=self)

    def _pay(self, method, label):
        if not self._cart: messagebox.showwarning("Empty Cart","Add items first.",parent=self); return
        sub,d,tax,tot = self._get_totals(); sym = self._sym

        win = tk.Toplevel(self); win.title(f"Payment — {label}")
        win.configure(bg=T["BG"]); win.geometry("440x560")
        win.transient(self); win.resizable(True,True); win.after(50, lambda: win.grab_set() if win.winfo_exists() else None)
        win.minsize(380, 400)
        _watermark(win)

        # Scrollable body — buttons pinned at bottom
        pay_sf, pay_body = scrolled_frame(win, bg=T["BG"])
        pay_sf.pack(fill="both", expand=True)

        lbl(pay_body,"PROCESS PAYMENT",14,True,T["ACCENT"],bg=T["BG"]).pack(pady=(20,2))
        lbl(pay_body,label,12,True,bg=T["BG"]).pack(pady=(0,10))

        # Show M-Pesa details if relevant
        mpesa_methods = {"mpesa","paybill","till","send_money","pochi"}
        if method in mpesa_methods:
            mf = tk.Frame(pay_body,bg=T["CARD"],highlightbackground=T["BORDER"],highlightthickness=1)
            mf.pack(fill="x",padx=30,pady=(0,6))
            pb = get_setting("paybill_number",""); tn = get_setting("till_number","")
            sm = get_setting("send_money_name",""); po = get_setting("pochi_number","")
            details = {"paybill":("Paybill No.",pb),"till":("Till No.",tn),
                       "send_money":("Send Money To",sm),"pochi":("Pochi No.",po)}.get(method)
            if details and details[1]:
                r = tk.Frame(mf,bg=T["CARD"]); r.pack(fill="x",padx=14,pady=8)
                lbl(r,details[0],9,color=T["TEXT3"],bg=T["CARD"]).pack(side="left")
                lbl(r,details[1],12,True,T["ACCENT"],bg=T["CARD"]).pack(side="right")
            lbl(mf,f"Amount: {sym} {tot:.2f}",12,True,T["GREEN"],bg=T["CARD"]).pack(padx=14,pady=(4,10))

        info = tk.Frame(pay_body,bg=T["CARD"],highlightbackground=T["BORDER"],highlightthickness=1)
        info.pack(fill="x",padx=30,pady=4)
        def irow(a,b_txt,big=False):
            r=tk.Frame(info,bg=T["CARD"]); r.pack(fill="x",padx=14,pady=3)
            lbl(r,a,12 if big else 10,big,T["ACCENT"] if big else T["TEXT"],bg=T["CARD"]).pack(side="left")
            lbl(r,b_txt,12 if big else 10,big,T["ACCENT"] if big else T["TEXT"],bg=T["CARD"]).pack(side="right")
        irow("Subtotal:",f"{sym} {sub:.2f}")
        if d: irow("Discount:",f"-{sym} {d:.2f}")
        if tax: irow(f"Tax:",f"{sym} {tax:.2f}")
        irow("TOTAL DUE:",f"{sym} {tot:.2f}",big=True)

        tv=tk.StringVar(value=f"{tot:.2f}"); cv=tk.StringVar(value=f"{sym} 0.00")
        if method=="cash":
            lbl(pay_body,"AMOUNT TENDERED",9,color=T["TEXT3"],bg=T["BG"]).pack(anchor="w",padx=30,pady=(10,2))
            te=tk.Entry(pay_body,textvariable=tv,font=F(20,True),bg=T["IN_BG"],fg=T["GREEN"],
                        insertbackground=T["TEXT"],relief="flat",
                        highlightbackground=T["BORDER"],highlightthickness=1,justify="right")
            te.pack(fill="x",padx=30,ipady=11); te.focus_set(); te.select_range(0,"end")
            cr=tk.Frame(pay_body,bg=T["BG"]); cr.pack(fill="x",padx=30,pady=6)
            lbl(cr,"CHANGE:",11,True,T["TEXT2"],bg=T["BG"]).pack(side="left")
            lbl(cr,"",18,True,T["GREEN"],bg=T["BG"],textvariable=cv).pack(side="right")
            def upd(*_):
                try: cv.set(f"{sym} {max(0,float(tv.get() or 0)-tot):.2f}")
                except: cv.set(f"{sym} 0.00")
            tv.trace_add("write",upd); upd()
            # Quick amounts
            qf=tk.Frame(pay_body,bg=T["BG"]); qf.pack(fill="x",padx=30,pady=(0,4))
            for amt in self._quick_amounts(tot):
                btn(qf,f"{sym}{amt:.0f}",lambda a=amt: tv.set(f"{a:.2f}"),"dark",(6,4)).pack(side="left",padx=2)
            btn(qf,"Exact",lambda: tv.set(f"{tot:.2f}"),"ghost",(6,4)).pack(side="right")

        def confirm():
            try: tendered=float(tv.get() or tot)
            except: tendered=tot
            if method=="cash" and tendered<tot:
                messagebox.showerror("Insufficient","Amount tendered < total.",parent=win); return
            win.destroy()
            ok,msg,sd=sales_manager.process_sale(self._cart,method,tendered,d,
                       auth.current_user["id"],auth.current_user["full_name"])
            if ok:
                self._cart.clear(); self._dv.set("0")
                self._render_cart(); self._recalc()
                self._refresh_stock_badges()
                self._show_receipt(sd)
            else: messagebox.showerror("Error",msg,parent=self)

        bf=tk.Frame(win,bg=T["BG"]); bf.pack(fill="x",padx=30,pady=(0,10))
        btn(bf,"✓  COMPLETE SALE & PRINT",confirm,"green",(0,0)).pack(fill="x",ipady=11,pady=(0,5))
        btn(bf,"Cancel",win.destroy,"ghost").pack(fill="x")
        win.bind("<Return>", lambda _: confirm())

    def _quick_amounts(self, total):
        amounts=[]
        for base in [50,100,200,500,1000,2000,5000]:
            if base>=total: amounts.append(base)
            if len(amounts)>=4: break
        return amounts or [total]

    def _show_receipt(self, sd, auto_print=False):
        shop=get_setting("shop_name","AlchemyPOS"); addr=get_setting("shop_address","")
        phone=get_setting("shop_phone",""); footer=get_setting("receipt_footer","Asante!")
        pb=get_setting("paybill_number",""); tn=get_setting("till_number","")
        sym=self._sym

        win=tk.Toplevel(self); win.title("Receipt"); win.configure(bg=T["BG"])
        win.geometry("400x680"); win.transient(self); win.resizable(True,True)

        # Pin watermark + buttons at bottom BEFORE canvas so pack order is right
        _watermark(win)
        bf=tk.Frame(win,bg=T["BG"]); bf.pack(side="bottom",fill="x",padx=10,pady=8)

        wrap=tk.Frame(win,bg=T["CARD"],highlightbackground=T["BORDER"],highlightthickness=1)
        wrap.pack(fill="both",expand=True,padx=10,pady=(10,0))
        can=tk.Canvas(wrap,bg=T["CARD"],highlightthickness=0)
        rsb=ttk.Scrollbar(wrap,orient="vertical",command=can.yview)
        can.config(yscrollcommand=rsb.set)
        rsb.pack(side="right",fill="y"); can.pack(fill="both",expand=True)
        inn=tk.Frame(can,bg=T["CARD"])
        cw2=can.create_window((0,0),window=inn,anchor="nw")
        inn.bind("<Configure>",lambda e: can.config(scrollregion=can.bbox("all")))
        can.bind("<Configure>",lambda e: can.itemconfig(cw2,width=e.width))
        # Scroll on hover over canvas or inner content
        def _rs_bind(e):
            can.bind_all("<MouseWheel>",lambda ev: can.yview_scroll(int(-1*(ev.delta/120)),"units"))
            can.bind_all("<Button-4>",  lambda ev: can.yview_scroll(-1,"units"))
            can.bind_all("<Button-5>",  lambda ev: can.yview_scroll( 1,"units"))
        def _rs_unbind(e):
            can.unbind_all("<MouseWheel>"); can.unbind_all("<Button-4>"); can.unbind_all("<Button-5>")
        can.bind("<Enter>",_rs_bind); can.bind("<Leave>",_rs_unbind)
        inn.bind("<Enter>",_rs_bind); inn.bind("<Leave>",_rs_unbind)

        def rl(text,sz=9,bold=False,color=None):
            tk.Label(inn,text=text,font=F(sz,bold),fg=color or T["TEXT2"],
                     bg=T["CARD"],anchor="center",justify="center").pack(fill="x",padx=14,pady=1)

        rl(shop,14,True,T["ACCENT"])
        if addr: rl(addr,9,color=T["TEXT3"])
        if phone: rl(phone,9,color=T["TEXT3"])
        if pb: rl(f"Paybill: {pb}  |  Till: {tn}" if tn else f"Paybill: {pb}",9,color=T["TEXT3"])
        elif tn: rl(f"Till No: {tn}",9,color=T["TEXT3"])
        rl("━"*34,8,color=T["BORDER"])
        rl(f"Receipt : {sd['receipt_number']}",9)
        rl(f"Date    : {sd['created_at']}",9)
        rl(f"Cashier : {sd['cashier']}",9)
        rl(f"Method  : {sd['payment_method'].upper()}",9)
        rl("─"*34,8,color=T["BORDER"])
        for it in sd["items"]:
            rb=tk.Frame(inn,bg=T["CARD2"],highlightbackground=T["BORDER"],highlightthickness=1)
            rb.pack(fill="x",padx=14,pady=2)
            inner_it=tk.Frame(rb,bg=T["CARD2"]); inner_it.pack(fill="x",padx=10,pady=6)
            # Name row
            nr=tk.Frame(inner_it,bg=T["CARD2"]); nr.pack(fill="x")
            lbl(nr,it["name"],10,True,bg=T["CARD2"],anchor="w",wraplength=240,justify="left").pack(side="left",fill="x",expand=True)
            lbl(nr,f"{sym} {it['qty']*it['price']:.2f}",10,True,T["ACCENT"],bg=T["CARD2"]).pack(side="right")
            # Qty×price row
            qr=tk.Frame(inner_it,bg=T["CARD2"]); qr.pack(fill="x",pady=(2,0))
            lbl(qr,f"{it['qty']:.0f} × {sym} {it['price']:.2f}",8,color=T["TEXT3"],bg=T["CARD2"]).pack(side="left")
        rl("─"*34,8,color=T["BORDER"])
        if sd["discount"]: rl(f"Discount  : -{sym} {sd['discount']:.2f}",9,color=T["YELLOW"])
        if sd["tax"]:      rl(f"Tax       :  {sym} {sd['tax']:.2f}",9)
        rl(f"TOTAL     :  {sym} {sd['total']:.2f}",14,True,T["ACCENT"])
        if sd["payment_method"]=="cash":
            rl(f"Tendered  :  {sym} {sd['amount_tendered']:.2f}",9)
            rl(f"Change    :  {sym} {sd['change']:.2f}",10,True,T["GREEN"])
        rl("━"*34,8,color=T["BORDER"]); rl(footer,9,color=T["TEXT3"])

        btn(bf,"✓  New Sale",win.destroy,"green").pack(side="right")
        btn(bf,"🖨  Print",lambda: self._print_receipt(sd),"blue").pack(side="right",padx=(0,8))
        if auto_print: self.after(300, lambda: self._print_receipt(sd))

    def _print_receipt(self, sd):
        sym=self._sym; shop=get_setting("shop_name","AlchemyPOS")
        footer=get_setting("receipt_footer","Asante!"); w=42
        lines=[
            "="*w,f"{shop:^{w}}",
            f"{get_setting('shop_address',''):^{w}}",f"{get_setting('shop_phone',''):^{w}}",
        ]
        pb=get_setting("paybill_number",""); tn=get_setting("till_number","")
        if pb: lines.append(f"{'Paybill: '+pb:^{w}}")
        if tn: lines.append(f"{'Till: '+tn:^{w}}")
        lines+=[
            "="*w,f"Receipt : {sd['receipt_number']}",
            f"Date    : {sd['created_at']}",f"Cashier : {sd['cashier']}",
            f"Method  : {sd['payment_method'].upper()}","-"*w,
        ]
        for it in sd["items"]:
            n=it["name"][:24]; t=f"{sym} {it['qty']*it['price']:.2f}"
            lines.append(f"{n:<24} {it['qty']:>3}x{sym}{it['price']:.2f}  {t:>8}")
        lines+=["-"*w,f"{'TOTAL':<32}{sym} {sd['total']:.2f}"]
        if sd["payment_method"]=="cash":
            lines.append(f"{'Tendered':<32}{sym} {sd['amount_tendered']:.2f}")
            lines.append(f"{'Change':<32}{sym} {sd['change']:.2f}")
        lines+=["="*w,f"{footer:^{w}}","",
               "-"*w,
               f"{"Developer: njorogefrancis":^{w}}",
               f"{"njorogefrancis.dev@gmail.com":^{w}}",
               f"{"0115634345":^{w}}",
               "",""]
        try:
            import subprocess
            cmd=get_setting("printer_command","lp")
            p=subprocess.Popen([cmd,"-"],stdin=subprocess.PIPE)
            p.communicate("\n".join(lines).encode())
            messagebox.showinfo("Print","Receipt sent to printer.",parent=self)
        except:
            rp=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            f"receipt_{sd['receipt_number']}.txt")
            with open(rp,"w") as f: f.write("\n".join(lines))
            messagebox.showinfo("Print",f"Saved receipt to:\n{rp}",parent=self)

    # ═══════════════════════════ INVENTORY ═══════════════════════════════════
    def _page_inventory(self):
        root=tk.Frame(self._content,bg=T["BG"]); root.pack(fill="both",expand=True)
        tk.Label(root,
                 text="Developer: njorogefrancis  |  njorogefrancis.dev@gmail.com  |  0115634345",
                 font=("Courier New", 7), fg=T.get("TEXT3","#484F58"), bg=T["BG"],
                 anchor="center").pack(side="bottom", fill="x", pady=(1,2))
        left=tk.Frame(root,bg=T["BG"]); left.pack(side="left",fill="both",expand=True,padx=(12,0),pady=10)

        tb=tk.Frame(left,bg=T["BG"]); tb.pack(fill="x",pady=(0,8))
        lbl(tb,"INVENTORY",14,True).pack(side="left")
        btn(tb,"＋  Add Product",lambda: self._prod_dialog(None),"primary").pack(side="right")
        btn(tb,"📦  Adjust Stock",lambda: self._inv_act("stock"),"yellow",(10,5)).pack(side="right",padx=(0,8))
        btn(tb,"⬆  Import CSV",self._inv_import,"blue",(10,5)).pack(side="right",padx=(0,8))
        btn(tb,"⬇  Export CSV",lambda: self._exp_inv("CSV"),"ghost",(10,5)).pack(side="right",padx=(0,8))
        btn(tb,"📄  Sample CSV",self._inv_sample,"ghost",(10,5)).pack(side="right",padx=(0,8))

        self._isv=tk.StringVar()
        se=entry(left,self._isv); se.pack(fill="x",ipady=7,pady=(0,6))
        self._isv.trace_add("write",lambda *_: self._inv_load())
        lbl(left,"Click a product to see details. Double-click to edit.",
            8,color=T["TEXT3"],bg=T["BG"]).pack(anchor="w",pady=(0,4))

        low=inventory_manager.get_low_stock()
        if low:
            lbl(left,f"⚠  {len(low)} item(s) low / out of stock",9,True,T["YELLOW"],bg=T["BG"]).pack(anchor="w",pady=(0,4))

        apply_tv("Inv")
        cols=("Name","Category","Price","Cost","Stock","Min","Status")
        self._inv_tv=ttk.Treeview(left,columns=cols,show="headings",style="Inv.Treeview")
        for c,w in zip(cols,[220,110,80,80,70,55,60]):
            self._inv_tv.heading(c,text=c); self._inv_tv.column(c,width=w,minwidth=40)
        isc=ttk.Scrollbar(left,orient="vertical",command=self._inv_tv.yview)
        self._inv_tv.configure(yscrollcommand=isc.set)
        isc.pack(side="right",fill="y"); self._inv_tv.pack(fill="both",expand=True)
        self._inv_tv.bind("<<TreeviewSelect>>",lambda _: self._inv_on_select())
        self._inv_tv.bind("<Double-1>",lambda _: self._inv_act("edit"))

        ar=tk.Frame(left,bg=T["BG"]); ar.pack(fill="x",pady=6)
        for txt,sty,act in [("✏  Edit","blue","edit"),("🗑  Delete","red","delete")]:
            btn(ar,txt,lambda a=act: self._inv_act(a),sty,(10,5)).pack(side="left",padx=(0,6))

        # Right panel — stock alerts on top, product detail below
        right=tk.Frame(root,bg=T["SIDEBAR"],width=320,
                       highlightbackground=T["BORDER"],highlightthickness=1)
        right.pack(side="right",fill="y",padx=(6,10),pady=10); right.pack_propagate(False)

        # ── Stock Alerts section (fixed top portion) ──────────────────────────
        alert_hdr=tk.Frame(right,bg=T["SIDEBAR"]); alert_hdr.pack(fill="x",padx=14,pady=(12,4))
        lbl(alert_hdr,"STOCK ALERTS",9,True,T["TEXT3"],bg=T["SIDEBAR"]).pack(side="left")
        self._alert_count_lbl=lbl(alert_hdr,"",9,True,T["RED"],bg=T["SIDEBAR"])
        self._alert_count_lbl.pack(side="right")
        hsep(right)

        # Scrollable alerts list — fixed height so detail panel always visible
        alerts_outer=tk.Frame(right,bg=T["SIDEBAR"],height=220); alerts_outer.pack(fill="x"); alerts_outer.pack_propagate(False)
        self._alerts_canvas=tk.Canvas(alerts_outer,bg=T["SIDEBAR"],highlightthickness=0)
        alerts_sb=ttk.Scrollbar(alerts_outer,orient="vertical",command=self._alerts_canvas.yview)
        self._alerts_canvas.configure(yscrollcommand=alerts_sb.set)
        alerts_sb.pack(side="right",fill="y")
        self._alerts_canvas.pack(side="left",fill="both",expand=True)
        self._alerts_inner=tk.Frame(self._alerts_canvas,bg=T["SIDEBAR"])
        _aw=self._alerts_canvas.create_window((0,0),window=self._alerts_inner,anchor="nw")
        self._alerts_inner.bind("<Configure>",lambda e: self._alerts_canvas.configure(scrollregion=self._alerts_canvas.bbox("all")))
        self._alerts_canvas.bind("<Configure>",lambda e: self._alerts_canvas.itemconfig(_aw,width=e.width))
        # Scroll on hover
        def _asc_enter(e):
            self._alerts_canvas.bind_all("<MouseWheel>",lambda ev: self._alerts_canvas.yview_scroll(int(-1*(ev.delta/120)),"units"))
            self._alerts_canvas.bind_all("<Button-4>",  lambda ev: self._alerts_canvas.yview_scroll(-1,"units"))
            self._alerts_canvas.bind_all("<Button-5>",  lambda ev: self._alerts_canvas.yview_scroll( 1,"units"))
        def _asc_leave(e):
            self._alerts_canvas.unbind_all("<MouseWheel>"); self._alerts_canvas.unbind_all("<Button-4>"); self._alerts_canvas.unbind_all("<Button-5>")
        self._alerts_canvas.bind("<Enter>",_asc_enter); self._alerts_canvas.bind("<Leave>",_asc_leave)
        self._alerts_inner.bind("<Enter>",_asc_enter); self._alerts_inner.bind("<Leave>",_asc_leave)

        hsep(right)

        # ── Product Detail section (fills remaining space) ────────────────────
        lbl(right,"PRODUCT DETAILS",9,True,T["TEXT3"],bg=T["SIDEBAR"]).pack(padx=14,pady=(8,6),anchor="w")
        hsep(right)
        self._detail_frame=tk.Frame(right,bg=T["SIDEBAR"]); self._detail_frame.pack(fill="both",expand=True)
        self._show_detail_placeholder()
        self._build_stock_alerts()
        self._inv_load()

    def _build_stock_alerts(self):
        """Rebuild the out-of-stock and low-stock alert list in the right panel."""
        for w in self._alerts_inner.winfo_children(): w.destroy()
        items = inventory_manager.get_low_stock()   # already sorted: qty ASC (zeros first)
        out   = [i for i in items if i.get("quantity",0) <= 0]
        low   = [i for i in items if i.get("quantity",0) >  0]

        total = len(items)
        if total == 0:
            self._alert_count_lbl.config(text="All OK ✓", fg=T["GREEN"])
            tk.Label(self._alerts_inner, text="No stock issues  ✓",
                     font=("Courier New",9), fg=T["GREEN"], bg=T["SIDEBAR"],
                     anchor="w").pack(fill="x", padx=12, pady=8)
            return

        self._alert_count_lbl.config(text=f"{total} alerts", fg=T["RED"] if out else T["YELLOW"])

        def _alert_row(prod, is_out):
            bg2 = T["SIDEBAR"]
            row = tk.Frame(self._alerts_inner, bg=bg2,
                           highlightbackground=T["BORDER"], highlightthickness=1)
            row.pack(fill="x", padx=6, pady=2)
            inner = tk.Frame(row, bg=bg2); inner.pack(fill="x", padx=8, pady=5)
            # Badge
            badge_color = T["RED"] if is_out else T["YELLOW"]
            badge_text  = "OUT" if is_out else f"{prod['quantity']:.0f}"
            tk.Label(inner, text=badge_text, font=("Courier New",8,"bold"),
                     fg=badge_color, bg=bg2, width=4, anchor="e").pack(side="right")
            # Name (truncated so it fits)
            name = prod["name"]
            if len(name) > 20: name = name[:19] + "…"
            tk.Label(inner, text=name, font=("Courier New",9,"bold"),
                     fg=T["TEXT"], bg=bg2, anchor="w").pack(side="left", fill="x", expand=True)
            # Click row to select product in treeview + show detail
            def _click(pid=prod["id"], e=None):
                for iid in self._inv_tv.get_children():
                    tags = self._inv_tv.item(iid,"tags")
                    if str(pid) in tags:
                        self._inv_tv.selection_set(iid)
                        self._inv_tv.see(iid)
                        self._inv_on_select()
                        break
            for w in [row, inner] + list(inner.winfo_children()):
                w.bind("<Button-1>", _click)
                try: w.config(cursor="hand2")
                except: pass
            # Propagate hover scroll to alerts canvas
            for w in [row, inner] + list(inner.winfo_children()):
                w.bind("<Enter>", lambda e: self._alerts_canvas.event_generate("<Enter>"))

        if out:
            tk.Label(self._alerts_inner, text=f"OUT OF STOCK  ({len(out)})",
                     font=("Courier New",8,"bold"), fg=T["RED"], bg=T["SIDEBAR"],
                     anchor="w").pack(fill="x", padx=10, pady=(6,2))
            for p in out:
                _alert_row(p, is_out=True)

        if low:
            tk.Label(self._alerts_inner, text=f"LOW STOCK  ({len(low)})",
                     font=("Courier New",8,"bold"), fg=T["YELLOW"], bg=T["SIDEBAR"],
                     anchor="w").pack(fill="x", padx=10, pady=(8,2))
            for p in low:
                _alert_row(p, is_out=False)

    def _show_detail_placeholder(self):
        for w in self._detail_frame.winfo_children(): w.destroy()
        lbl(self._detail_frame,"Select a product\nto view details",10,
            color=T["TEXT3"],bg=T["SIDEBAR"],justify="center").pack(pady=40,padx=10)

    def _inv_on_select(self):
        pid=self._inv_sel_id()
        if not pid: self._show_detail_placeholder(); return
        p=inventory_manager.get_product_by_id(pid)
        if p: self._show_detail_panel(p)
        else: self._show_detail_placeholder()

    def _show_detail_panel(self, p):
        for w in self._detail_frame.winfo_children(): w.destroy()
        frm,inner=scrolled_frame(self._detail_frame,bg=T["SIDEBAR"])
        frm.pack(fill="both",expand=True)
        self.after(80, lambda: propagate_scroll(inner))
        sym=get_setting("currency_symbol","KSh")
        qty=p.get("quantity",0); low=p.get("low_stock_threshold",5)
        sc=T["RED"] if qty<=0 else (T["YELLOW"] if qty<=low else T["GREEN"])
        status="OUT OF STOCK" if qty<=0 else (f"LOW ({qty:.0f})" if qty<=low else f"OK ({qty:.0f})")

        def drow(label_txt, value, vc=None):
            r=tk.Frame(inner,bg=T["SIDEBAR"]); r.pack(fill="x",padx=12,pady=4)
            lbl(r,label_txt,8,color=T["TEXT3"],bg=T["SIDEBAR"]).pack(anchor="w")
            lbl(r,str(value),11,True,vc or T["TEXT"],bg=T["SIDEBAR"]).pack(anchor="w")

        drow("Name",       p["name"])
        drow("Category",   p.get("category","—"))
        drow("Price",      f"{sym} {p['price']:.2f}",   T["ACCENT"])
        drow("Cost",       f"{sym} {p['cost']:.2f}")
        drow("Unit",       p.get("unit","pcs"))
        drow("Barcode",    p.get("barcode") or "—")
        drow("Stock",      status, sc)
        drow("Low Stock ≤",f"{low:.0f} units")

        hsep(inner)
        lbl(inner,"QUICK STOCK ADJUST",8,True,T["TEXT3"],bg=T["SIDEBAR"]).pack(anchor="w",padx=12,pady=(4,4))
        adj_row=tk.Frame(inner,bg=T["SIDEBAR"]); adj_row.pack(fill="x",padx=12)
        av=tk.StringVar(value="")
        ae=entry(adj_row,av,width=7); ae.pack(side="left",ipady=6)
        lbl(adj_row,f" {p.get('unit','pcs')}",9,color=T["TEXT3"],bg=T["SIDEBAR"]).pack(side="left")

        def do_add():
            try: delta=float(av.get() or 0)
            except: messagebox.showerror("Error","Enter a valid number.",parent=self); return
            if delta<=0: messagebox.showerror("Error","Enter a positive number.",parent=self); return
            inventory_manager.adjust_stock(p["id"],delta,auth.current_user["id"],auth.current_user["username"],"Manual add")
            av.set(""); self._inv_load(); self._build_stock_alerts()
            p2=inventory_manager.get_product_by_id(p["id"])
            if p2: self._show_detail_panel(p2)

        def do_remove():
            try: delta=float(av.get() or 0)
            except: messagebox.showerror("Error","Enter a valid number.",parent=self); return
            if delta<=0: messagebox.showerror("Error","Enter a positive number.",parent=self); return
            inventory_manager.adjust_stock(p["id"],-delta,auth.current_user["id"],auth.current_user["username"],"Manual remove")
            av.set(""); self._inv_load(); self._build_stock_alerts()
            p2=inventory_manager.get_product_by_id(p["id"])
            if p2: self._show_detail_panel(p2)

        bf=tk.Frame(inner,bg=T["SIDEBAR"]); bf.pack(fill="x",padx=12,pady=(4,0))
        btn(bf,"＋ Add",do_add,"green",(8,5)).pack(side="left",padx=(0,4))
        btn(bf,"− Remove",do_remove,"red",(8,5)).pack(side="left")
        hsep(inner)
        btn(inner,"✏  Full Edit",lambda: self._prod_dialog(p),"blue",(0,0)).pack(
            fill="x",padx=12,ipady=7)

    def _inv_load(self):
        q=self._isv.get() if hasattr(self,"_isv") else ""
        prods=inventory_manager.search_products(q,limit=500)
        self._inv_tv.delete(*self._inv_tv.get_children())
        sym=get_setting("currency_symbol","KSh")
        for p in prods:
            qty=p.get("quantity",0); low=p.get("low_stock_threshold",5)
            st ="OUT" if qty<=0 else ("LOW" if qty<=low else "OK")
            tg ="out" if qty<=0 else ("low" if qty<=low else "ok")
            self._inv_tv.insert("","end",
                values=(p["name"],p.get("category",""),f"{sym} {p['price']:.2f}",
                        f"{sym} {p['cost']:.2f}",f"{qty:.0f}",f"{low:.0f}",st),
                tags=(tg,str(p["id"])))
        self._inv_tv.tag_configure("out",foreground=T["RED"])
        self._inv_tv.tag_configure("low",foreground=T["YELLOW"])
        self._inv_tv.tag_configure("ok", foreground=T["TEXT"])

    def _inv_sel_id(self):
        sel=self._inv_tv.selection()
        if not sel: return None
        for t in self._inv_tv.item(sel[0],"tags"):
            if t.isdigit(): return int(t)
        return None

    def _inv_act(self, act):
        pid=self._inv_sel_id()
        if act=="edit":
            if not pid: return
            self._prod_dialog(inventory_manager.get_product_by_id(pid))
        elif act=="stock":
            if not pid: return
            self._stock_dialog(inventory_manager.get_product_by_id(pid))
        elif act=="delete":
            if not pid: return
            p=inventory_manager.get_product_by_id(pid)
            if messagebox.askyesno("Delete",f"Delete '{p['name']}'?",parent=self):
                inventory_manager.delete_product(pid,auth.current_user["id"],auth.current_user["username"])
                self._show_detail_placeholder(); self._inv_load(); self._build_stock_alerts()

    def _stock_dialog(self, p):
        sym=get_setting("currency_symbol","KSh")
        win=tk.Toplevel(self); win.title("Adjust Stock"); win.configure(bg=T["BG"])
        win.geometry("360x340"); win.transient(self); win.resizable(False,False); win.after(50, lambda: win.grab_set() if win.winfo_exists() else None)
        lbl(win,"ADJUST STOCK",14,True,T["ACCENT"],bg=T["BG"]).pack(pady=(20,4))
        lbl(win,p["name"],11,True,bg=T["BG"]).pack()
        lbl(win,f"Current: {p.get('quantity',0):.0f} {p.get('unit','pcs')}",9,color=T["TEXT3"],bg=T["BG"]).pack(pady=(2,16))
        frm=tk.Frame(win,bg=T["BG"]); frm.pack(padx=36,fill="x")
        lbl(frm,"Quantity:",9,color=T["TEXT3"],bg=T["BG"]).pack(anchor="w")
        av=tk.StringVar(); ae=entry(frm,av,big=True); ae.pack(fill="x",ipady=10,pady=(4,4)); ae.focus_set()
        lbl(frm,"Reason (optional):",9,color=T["TEXT3"],bg=T["BG"]).pack(anchor="w",pady=(8,2))
        rv=tk.StringVar(); entry(frm,rv).pack(fill="x",ipady=6)
        ev=tk.StringVar(); lbl(frm,"",9,color=T["RED"],bg=T["BG"],textvariable=ev).pack(pady=3)
        bf=tk.Frame(frm,bg=T["BG"]); bf.pack(fill="x",pady=4)
        def do_adj(sign):
            try: delta=float(av.get() or 0)
            except: ev.set("Enter a valid number."); return
            if delta<=0: ev.set("Enter a positive number."); return
            inventory_manager.adjust_stock(p["id"],sign*delta,
                auth.current_user["id"],auth.current_user["username"],rv.get())
            win.destroy(); self._inv_load()
            if hasattr(self,"_build_stock_alerts"): self._build_stock_alerts()
            p2=inventory_manager.get_product_by_id(p["id"])
            if p2: self._show_detail_panel(p2)
        btn(bf,"＋  ADD STOCK",  lambda: do_adj(+1),"green", (0,0)).pack(fill="x",ipady=9,pady=(0,4))
        btn(bf,"−  REMOVE STOCK",lambda: do_adj(-1),"red",   (0,0)).pack(fill="x",ipady=9,pady=(0,4))
        btn(bf,"Cancel",win.destroy,"ghost").pack(fill="x")

    def _prod_dialog(self, product=None):
        editing=product is not None
        win=tk.Toplevel(self); win.title("Edit Product" if editing else "Add Product")
        win.configure(bg=T["BG"]); win.geometry("520x580")
        win.transient(self); win.resizable(True,True); win.after(50, lambda: win.grab_set() if win.winfo_exists() else None)
        win.minsize(440, 400)
        _watermark(win)
        lbl(win,"EDIT PRODUCT" if editing else "NEW PRODUCT",14,True,T["ACCENT"],bg=T["BG"]).pack(pady=(20,14))

        sf_outer, scroll_inner = scrolled_frame(win, bg=T["BG"])
        sf_outer.pack(fill="both",expand=True,padx=28)
        win.after(120, lambda: propagate_scroll(scroll_inner))

        outer=tk.Frame(scroll_inner,bg=T["BG"]); outer.pack(fill="both",expand=True)
        col1=tk.Frame(outer,bg=T["BG"]); col1.pack(side="left",fill="both",expand=True,padx=(0,8))
        col2=tk.Frame(outer,bg=T["BG"]); col2.pack(side="left",fill="both",expand=True,padx=(8,0))
        p=product or {}; fields={}

        def field(parent, label_txt, key, default=""):
            lbl(parent,label_txt,9,color=T["TEXT3"],bg=T["BG"]).pack(anchor="w",pady=(6,1))
            v=tk.StringVar(value=str(default))
            entry(parent,v).pack(fill="x",ipady=7)
            fields[key]=v

        field(col1,"Product Name *","name",    p.get("name",""))
        field(col1,"Selling Price *","price",  f"{p.get('price',0):.2f}" if p else "0.00")
        field(col1,"Cost Price",    "cost",    f"{p.get('cost',0):.2f}" if p else "0.00")
        field(col1,"Unit",          "unit",    p.get("unit",get_setting("default_unit","pcs")))
        field(col2,"Barcode",       "barcode", p.get("barcode","") or "")
        field(col2,"Stock Quantity","quantity",f"{p.get('quantity',0):.0f}" if p else "0")
        field(col2,"Low Stock Alert","low_stock",
              f"{p.get('low_stock_threshold',0):.0f}" if p else get_setting("default_low_stock","5"))

        # Category as dropdown
        lbl(col2,"Category",9,color=T["TEXT3"],bg=T["BG"]).pack(anchor="w",pady=(6,1))
        cats=get_categories() or ["General"]
        cat_var=tk.StringVar(value=p.get("category","General") if p else cats[0])
        fields["category"]=cat_var
        combo(col2,cat_var,cats,width=18).pack(fill="x",pady=(0,4))

        ev=tk.StringVar()
        lbl(scroll_inner,"",9,color=T["RED"],bg=T["BG"],textvariable=ev).pack(anchor="w",padx=2,pady=(6,0))

        def save():
            if editing:
                ok,msg=inventory_manager.update_product(
                    product["id"],fields["name"].get(),fields["price"].get(),
                    fields["cost"].get(),fields["category"].get(),fields["unit"].get(),
                    fields["barcode"].get(),fields["quantity"].get(),fields["low_stock"].get(),
                    auth.current_user["id"],auth.current_user["username"])
            else:
                ok,msg=inventory_manager.add_product(
                    fields["name"].get(),fields["price"].get(),fields["cost"].get(),
                    fields["category"].get(),fields["unit"].get(),fields["barcode"].get(),
                    fields["quantity"].get(),fields["low_stock"].get(),
                    auth.current_user["id"],auth.current_user["username"])
            if ok:
                win.destroy(); self._inv_load()
                if hasattr(self,"_build_stock_alerts"): self._build_stock_alerts()
                if editing:
                    p2=inventory_manager.get_product_by_id(product["id"])
                    if p2: self._show_detail_panel(p2)
            else: ev.set(msg)

        bf=tk.Frame(win,bg=T["BG"]); bf.pack(fill="x",padx=28,pady=10)
        btn(bf,"SAVE PRODUCT",save,"primary",(0,0)).pack(fill="x",ipady=10,pady=(0,4))
        btn(bf,"Cancel",win.destroy,"ghost").pack(fill="x")

    # ── Inventory import / sample ────────────────────────────────────────────
    def _inv_import(self):
        path = filedialog.askopenfilename(
            filetypes=[("CSV files","*.csv"),("All files","*.*")],
            title="Import Inventory CSV")
        if not path: return
        ok, added, skipped, errors = inventory_manager.import_from_csv(path,
            auth.current_user["id"], auth.current_user["username"])
        if ok:
            self._inv_load()
            msg = f"Import complete.\n\nAdded:   {added}\nSkipped (already exist):  {skipped}"
            if errors: msg += f"\nErrors:  {len(errors)}\n\n" + "\n".join(errors[:10])
            _build_stock_alerts_safe = getattr(self,"_build_stock_alerts",None)
            if _build_stock_alerts_safe: _build_stock_alerts_safe()
            messagebox.showinfo("Import Complete", msg, parent=self)
        else:
            messagebox.showerror("Import Failed", added, parent=self)

    def _inv_sample(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV","*.csv")],
            title="Save Sample Inventory CSV")
        if not path: return
        ok, msg = inventory_manager.generate_sample_csv(path)
        if ok:
            messagebox.showinfo("Sample Created",
                f"Sample CSV saved to:\n{path}\n\nEdit it and use Import CSV to load your products.",
                parent=self)
        else:
            messagebox.showerror("Error", msg, parent=self)

    # ═══════════════════════════ REPORTS ═════════════════════════════════════
    def _page_reports(self):
        root=tk.Frame(self._content,bg=T["BG"]); root.pack(fill="both",expand=True,padx=14,pady=10)
        lbl(root,"REPORTS & ANALYTICS",14,True).pack(anchor="w",pady=(0,8))

        # ── Filter bar ──────────────────────────────────────────────────────
        ff=tk.Frame(root,bg=T["CARD"],highlightbackground=T["BORDER"],highlightthickness=1)
        ff.pack(fill="x",pady=(0,10))
        frow=tk.Frame(ff,bg=T["CARD"]); frow.pack(fill="x",padx=14,pady=10)

        def flbl(txt): lbl(frow,txt,9,color=T["TEXT3"],bg=T["CARD"]).pack(side="left",padx=(10,3))

        self._f_from=tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self._f_to=tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))

        def pick_date(var):
            self._show_calendar(var)

        flbl("FROM")
        fe=tk.Frame(frow,bg=T["CARD"]); fe.pack(side="left")
        entry(fe,self._f_from,width=11).pack(side="left",ipady=5)
        tk.Button(fe,text="📅",command=lambda: pick_date(self._f_from),
                  bg=T["CARD2"],fg=T["TEXT"],font=F(10),relief="flat",
                  cursor="hand2",bd=0,highlightthickness=0,padx=4).pack(side="left")
        flbl("TO")
        te=tk.Frame(frow,bg=T["CARD"]); te.pack(side="left")
        entry(te,self._f_to,width=11).pack(side="left",ipady=5)
        tk.Button(te,text="📅",command=lambda: pick_date(self._f_to),
                  bg=T["CARD2"],fg=T["TEXT"],font=F(10),relief="flat",
                  cursor="hand2",bd=0,highlightthickness=0,padx=4).pack(side="left")

        flbl("CASHIER")
        cashiers=report_manager.get_cashier_list()
        self._f_cashier=tk.StringVar(value="All")
        combo(frow,self._f_cashier,cashiers,width=14).pack(side="left")

        flbl("METHOD")
        methods=["All"]+[lbl for _,lbl in get_payment_methods()]
        self._f_method_lbl=tk.StringVar(value="All")
        combo(frow,self._f_method_lbl,methods,width=14).pack(side="left")

        flbl("SEARCH")
        self._f_search=tk.StringVar()
        entry(frow,self._f_search,width=16).pack(side="left",ipady=5)

        btn(frow,"🔍  Apply",self._rep_load,"primary",(10,5)).pack(side="left",padx=(10,0))
        btn(frow,"Today",lambda:(self._f_from.set(datetime.now().strftime("%Y-%m-%d")),
                                  self._f_to.set(datetime.now().strftime("%Y-%m-%d")),
                                  self._rep_load()),"ghost",(8,5)).pack(side="left",padx=3)
        btn(frow,"This Week",self._filter_week,"ghost",(8,5)).pack(side="left",padx=3)
        btn(frow,"This Month",self._filter_month,"ghost",(8,5)).pack(side="left",padx=3)

        # ── KPI cards ───────────────────────────────────────────────────────
        sc_row=tk.Frame(root,bg=T["BG"]); sc_row.pack(fill="x",pady=(0,10))
        self._rv={}
        for title,key in [("TRANSACTIONS","tx"),("REVENUE","rev"),
                           ("DISCOUNTS","disc"),("AVG SALE","avg"),
                           ("TAX COLLECTED","tax"),("PROFIT","profit")]:
            c=tk.Frame(sc_row,bg=T["CARD"],highlightbackground=T["BORDER"],highlightthickness=1)
            c.pack(side="left",fill="x",expand=True,padx=3)
            lbl(c,title,7,True,T["TEXT3"],bg=T["CARD"]).pack(anchor="w",padx=12,pady=(10,2))
            v=tk.StringVar(value="—"); self._rv[key]=v
            lbl(c,"",16,True,T["ACCENT"],bg=T["CARD"],textvariable=v).pack(anchor="w",padx=12,pady=(0,10))

        # ── Body ────────────────────────────────────────────────────────────
        body=tk.Frame(root,bg=T["BG"]); body.pack(fill="both",expand=True)

        # Sales detail table
        lf=tk.Frame(body,bg=T["BG"]); lf.pack(side="left",fill="both",expand=True,padx=(0,8))
        lbl(lf,"SALES HISTORY",10,True,T["TEXT3"],bg=T["BG"]).pack(anchor="w",pady=(0,4))
        apply_tv("Rep")
        rc=("Receipt","Date/Time","Cashier","Method","Total","Disc","Tax","Status")
        self._rep_tv=ttk.Treeview(lf,columns=rc,show="headings",style="Rep.Treeview")
        for c,w in zip(rc,[110,120,100,80,75,60,55,55]):
            self._rep_tv.heading(c,text=c); self._rep_tv.column(c,width=w)
        rs=ttk.Scrollbar(lf,orient="vertical",command=self._rep_tv.yview)
        self._rep_tv.config(yscrollcommand=rs.set)
        rs.pack(side="right",fill="y"); self._rep_tv.pack(fill="both",expand=True)
        self._rep_tv.bind("<Double-1>", lambda _: self._view_receipt_items())
        lbl(lf,"↑ Double-click any row to view receipt items",8,color=T["TEXT3"],bg=T["BG"]).pack(anchor="w",pady=(2,0))

        # Right panels stacked
        rf=tk.Frame(body,bg=T["BG"],width=280); rf.pack(side="right",fill="y"); rf.pack_propagate(False)

        # Top products
        lbl(rf,"TOP PRODUCTS",10,True,T["TEXT3"],bg=T["BG"]).pack(anchor="w",pady=(0,4))
        apply_tv("Top")
        tc=("Product","Qty","Revenue")
        self._top_tv=ttk.Treeview(rf,columns=tc,show="headings",style="Top.Treeview",height=8)
        for c,w in zip(tc,[130,50,90]): self._top_tv.heading(c,text=c); self._top_tv.column(c,width=w)
        ts=ttk.Scrollbar(rf,orient="vertical",command=self._top_tv.yview)
        self._top_tv.config(yscrollcommand=ts.set)
        ts.pack(side="right",fill="y"); self._top_tv.pack(fill="x")

        # Payment split
        lbl(rf,"PAYMENT SPLIT",10,True,T["TEXT3"],bg=T["BG"]).pack(anchor="w",pady=(10,4))
        apply_tv("Pay")
        pc2=("Method","Count","Total")
        self._pay_tv=ttk.Treeview(rf,columns=pc2,show="headings",style="Pay.Treeview",height=7)
        for c,w in zip(pc2,[100,60,110]): self._pay_tv.heading(c,text=c); self._pay_tv.column(c,width=w)
        psc=ttk.Scrollbar(rf,orient="vertical",command=self._pay_tv.yview)
        self._pay_tv.config(yscrollcommand=psc.set)
        psc.pack(side="right",fill="y"); self._pay_tv.pack(fill="x")

        # Cashier summary
        lbl(rf,"BY CASHIER",10,True,T["TEXT3"],bg=T["BG"]).pack(anchor="w",pady=(10,4))
        apply_tv("Cas")
        cc2=("Cashier","Txns","Revenue","Avg")
        self._cas_tv=ttk.Treeview(rf,columns=cc2,show="headings",style="Cas.Treeview",height=6)
        for c,w in zip(cc2,[100,45,90,75]): self._cas_tv.heading(c,text=c); self._cas_tv.column(c,width=w)
        csc=ttk.Scrollbar(rf,orient="vertical",command=self._cas_tv.yview)
        self._cas_tv.config(yscrollcommand=csc.set)
        csc.pack(side="right",fill="y"); self._cas_tv.pack(fill="x")

        # Export bar
        eb=tk.Frame(root,bg=T["BG"]); eb.pack(fill="x",pady=6)
        lbl(eb,"Export sales:",9,color=T["TEXT3"],bg=T["BG"]).pack(side="left")
        for fmt in ["CSV","XML","PDF"]:
            btn(eb,f"⬇ {fmt}",lambda f=fmt: self._exp_sales(f),"dark",(8,4)).pack(side="left",padx=3)
        lbl(eb,"  Inventory:",9,color=T["TEXT3"],bg=T["BG"]).pack(side="left",padx=(10,0))
        for fmt in ["CSV","XML","PDF"]:
            btn(eb,f"⬇ {fmt}",lambda f=fmt: self._exp_inv(f),"ghost",(8,4)).pack(side="left",padx=3)

        self._rep_load()

    def _filter_week(self):
        now=datetime.now()
        self._f_from.set((now-timedelta(days=now.weekday())).strftime("%Y-%m-%d"))
        self._f_to.set(now.strftime("%Y-%m-%d")); self._rep_load()

    def _filter_month(self):
        now=datetime.now()
        self._f_from.set(now.strftime("%Y-%m-01"))
        self._f_to.set(now.strftime("%Y-%m-%d")); self._rep_load()

    def _rep_load(self):
        sym=get_setting("currency_symbol","KSh")
        df=self._f_from.get(); dt=self._f_to.get()
        cashier=self._f_cashier.get()
        method_lbl=self._f_method_lbl.get()
        method_name=None
        if method_lbl!="All":
            for n,l in get_payment_methods():
                if l==method_lbl: method_name=n; break
        search=self._f_search.get()

        rows=report_manager.get_sales_detail(df,dt,cashier,method_name,search)
        rev   = sum(float(r.get("total",0))    for r in rows)
        disc  = sum(float(r.get("discount",0)) for r in rows)
        tax   = sum(float(r.get("tax",0))      for r in rows)
        avg   = rev/len(rows) if rows else 0
        profit= report_manager.get_profit(df, dt, cashier, method_name)
        self._rv["tx"].set(str(len(rows)))
        self._rv["rev"].set(f"{sym} {rev:,.2f}")
        self._rv["disc"].set(f"{sym} {disc:,.2f}")
        self._rv["avg"].set(f"{sym} {avg:,.2f}")
        self._rv["tax"].set(f"{sym} {tax:,.2f}")
        self._rv["profit"].set(f"{sym} {profit:,.2f}")

        self._rep_tv.delete(*self._rep_tv.get_children())
        for r in rows:
            self._rep_tv.insert("","end",values=(
                r.get("receipt_number",""),
                (r.get("created_at","") or "")[:16],
                r.get("cashier","") or "",
                (r.get("payment_method","") or "").upper(),
                f"{sym} {float(r.get('total',0)):,.2f}",
                f"{sym} {float(r.get('discount',0)):,.2f}",
                f"{sym} {float(r.get('tax',0)):,.2f}",
                r.get("status",""),
            ))

        self._top_tv.delete(*self._top_tv.get_children())
        for p in report_manager.get_top_products(date_from=df,date_to=dt):
            self._top_tv.insert("","end",values=(
                p["product_name"][:20],f"{p['total_qty']:.0f}",
                f"{sym} {p['total_revenue']:,.2f}"))

        # Payment split — also show total row, filtered by current method if set
        self._pay_tv.delete(*self._pay_tv.get_children())
        split_rows = report_manager.get_payment_split(df, dt, method_name)
        split_total = sum(float(r["total"]) for r in split_rows)
        for p in split_rows:
            self._pay_tv.insert("","end",values=(
                (p["payment_method"] or "").upper(),
                str(p["count"]),f"{sym} {p['total']:,.2f}"))
        if split_rows:
            self._pay_tv.insert("","end",values=("─"*10,"",""))
            self._pay_tv.insert("","end",values=(
                "TOTAL",str(sum(r["count"] for r in split_rows)),
                f"{sym} {split_total:,.2f}"),tags=("total",))
            self._pay_tv.tag_configure("total",foreground=T["ACCENT"])

        self._cas_tv.delete(*self._cas_tv.get_children())
        for c in report_manager.get_cashier_summary(df,dt):
            self._cas_tv.insert("","end",values=(
                c["cashier"],str(c["tx_count"]),
                f"{sym} {c['revenue']:,.2f}",f"{sym} {c['avg_sale']:,.2f}"))

    def _exp_sales(self, fmt):
        ext=fmt.lower(); df=self._f_from.get(); dt=self._f_to.get()
        path=filedialog.asksaveasfilename(defaultextension=f".{ext}",
             filetypes=[(fmt,f"*.{ext}")],title=f"Export Sales as {fmt}")
        if not path: return
        rows=report_manager.get_sales_detail(df,dt)
        if   fmt=="CSV": ok,msg=report_manager.export_sales_csv(path,rows)
        elif fmt=="XML": ok,msg=report_manager.export_sales_xml(path,rows)
        elif fmt=="PDF": ok,msg=report_manager.export_sales_pdf(path,rows,df,dt)
        else: return
        messagebox.showinfo("Export",msg,parent=self)

    def _exp_inv(self, fmt):
        ext=fmt.lower()
        path=filedialog.asksaveasfilename(defaultextension=f".{ext}",
             filetypes=[(fmt,f"*.{ext}")],title=f"Export Inventory as {fmt}")
        if not path: return
        if   fmt=="CSV": ok,msg=report_manager.export_inventory_csv(path)
        elif fmt=="XML": ok,msg=report_manager.export_inventory_xml(path)
        elif fmt=="PDF": ok,msg=report_manager.export_inventory_pdf(path)
        else: return
        messagebox.showinfo("Export",msg,parent=self)

    # ═══════════════════════════ USERS ═══════════════════════════════════════
    def _page_users(self):
        root=tk.Frame(self._content,bg=T["BG"]); root.pack(fill="both",expand=True,padx=14,pady=10)
        tb=tk.Frame(root,bg=T["BG"]); tb.pack(fill="x",pady=(0,8))
        lbl(tb,"USER MANAGEMENT",14,True).pack(side="left")
        btn(tb,"＋  Add User",lambda: self._user_dialog(None),"primary").pack(side="right")
        apply_tv("Usr")
        cols=("Username","Full Name","Role","Status","Last Login","Created")
        self._usr_tv=ttk.Treeview(root,columns=cols,show="headings",style="Usr.Treeview")
        for c,w in zip(cols,[130,170,80,70,140,100]):
            self._usr_tv.heading(c,text=c); self._usr_tv.column(c,width=w)
        us=ttk.Scrollbar(root,orient="vertical",command=self._usr_tv.yview)
        self._usr_tv.config(yscrollcommand=us.set)
        us.pack(side="right",fill="y"); self._usr_tv.pack(fill="both",expand=True)
        ar=tk.Frame(root,bg=T["BG"]); ar.pack(fill="x",pady=6)
        for txt,sty,act in [("✏  Edit","blue","edit"),("🔑  Reset Password","dark","reset"),
                             ("🗑  Delete","red","delete")]:
            btn(ar,txt,lambda a=act: self._usr_act(a),sty,(10,5)).pack(side="left",padx=(0,6))
        self._usr_load()

    def _usr_load(self):
        self._usr_tv.delete(*self._usr_tv.get_children())
        for u in auth.get_all_users():
            role_display = {"admin":"Admin","cashier":"Cashier",
                             "inventory_manager":"Inv. Manager"}.get(u.get("role",""), u.get("role","").title())
            self._usr_tv.insert("","end",values=(
                u["username"],u.get("full_name",""),role_display,
                "Active" if u["is_active"] else "Disabled",
                (u.get("last_login") or "Never")[:16],
                (u.get("created_at") or "")[:10]),
                tags=(str(u["id"]),))

    def _usr_sel_id(self):
        sel=self._usr_tv.selection()
        if not sel: return None
        for t in self._usr_tv.item(sel[0],"tags"):
            if t.isdigit(): return int(t)
        return None

    def _usr_act(self, act):
        uid=self._usr_sel_id()
        if not uid: return
        user=next((u for u in auth.get_all_users() if u["id"]==uid),None)
        if not user: return
        if act=="edit": self._user_dialog(user)
        elif act=="delete":
            if messagebox.askyesno("Delete",f"Delete '{user['username']}'?",parent=self):
                ok,msg=auth.delete_user(uid,auth.current_user["id"])
                messagebox.showinfo("Result",msg,parent=self); self._usr_load()
        elif act=="reset":
            pw=simpledialog.askstring("Reset Password",f"New password for '{user['username']}':",
                                      parent=self,show="*")
            if pw:
                ok,msg=auth.reset_user_password(uid,pw,auth.current_user["id"],auth.current_user["username"])
                messagebox.showinfo("Result",msg,parent=self)

    def _user_dialog(self, user=None):
        editing=user is not None
        win=tk.Toplevel(self); win.title("Edit User" if editing else "Add User")
        win.configure(bg=T["BG"]); win.geometry("480x620")
        win.transient(self); win.resizable(True,True); win.after(50, lambda: win.grab_set() if win.winfo_exists() else None)
        win.minsize(420, 400)
        _watermark(win)
        lbl(win,"EDIT USER" if editing else "NEW USER",14,True,T["ACCENT"],bg=T["BG"]).pack(pady=(20,14))
        sf_outer, frm = scrolled_frame(win, bg=T["BG"])
        sf_outer.pack(fill="both",expand=True,padx=32,pady=(0,4))
        win.after(120, lambda: propagate_scroll(frm))
        u=user or {}

        def row(label_txt,default="",show=None):
            lbl(frm,label_txt,9,color=T["TEXT3"],bg=T["BG"]).pack(anchor="w",pady=(6,1))
            v=tk.StringVar(value=default)
            entry(frm,v,show=show).pack(fill="x",ipady=7)
            return v

        uv=row("Username *",  u.get("username",""))
        fv=row("Full Name",   u.get("full_name",""))
        pv=None if editing else row("Password *",show="*")
        rv=tk.StringVar(value=u.get("role","cashier"))
        av=tk.BooleanVar(value=bool(u.get("is_active",1)))

        rr=tk.Frame(frm,bg=T["BG"]); rr.pack(fill="x",pady=8)
        lbl(rr,"Role:",9,color=T["TEXT3"],bg=T["BG"]).pack(side="left",padx=(0,10))
        for role, role_label in [("cashier","Cashier"),("inventory_manager","Inv. Manager"),("admin","Admin")]:
            tk.Radiobutton(rr,text=role_label,variable=rv,value=role,
                           font=F(10),bg=T["BG"],fg=T["TEXT"],
                           selectcolor=T["CARD"],activebackground=T["BG"]).pack(side="left",padx=8)
        if editing:
            tk.Checkbutton(frm,text="Account Active",variable=av,font=F(10),
                           bg=T["BG"],fg=T["TEXT"],selectcolor=T["CARD"],
                           activebackground=T["BG"]).pack(anchor="w",pady=4)

        # 3 Security questions
        lbl(frm,"Security Questions",9,True,T["ACCENT"],bg=T["BG"]).pack(anchor="w",pady=(10,4))
        sq_vars=[]; sa_vars=[]
        for qi in range(NUM_SEC_QUESTIONS):
            lbl(frm,f"Question {qi+1}",8,color=T["TEXT3"],bg=T["BG"]).pack(anchor="w",pady=(4,1))
            sqv=tk.StringVar(value=SECURITY_QUESTIONS[qi*5 % len(SECURITY_QUESTIONS)])
            combo(frm,sqv,SECURITY_QUESTIONS,width=36).pack(fill="x",pady=(1,3))
            lbl(frm,f"Answer {qi+1}",8,color=T["TEXT3"],bg=T["BG"]).pack(anchor="w")
            sav=tk.StringVar()
            entry(frm,sav).pack(fill="x",ipady=6,pady=(1,2))
            sq_vars.append(sqv); sa_vars.append(sav)
        lbl(frm,"(Leave answers blank to keep existing questions)",8,color=T["TEXT3"],bg=T["BG"]).pack(anchor="w")

        ev=tk.StringVar(); lbl(frm,"",9,color=T["RED"],bg=T["BG"],textvariable=ev).pack(pady=3)

        def save():
            if editing:
                ok,msg=auth.update_user(user["id"],fv.get(),rv.get(),int(av.get()))
            else:
                ok,msg=auth.add_user(uv.get(),pv.get(),rv.get(),fv.get())
            if ok:
                conn=get_connection()
                lookup_un=uv.get() if not editing else user["username"]
                row2=conn.execute("SELECT id FROM users WHERE username=?",(lookup_un,)).fetchone()
                conn.close()
                if row2 and any(v.get().strip() for v in sa_vars):
                    auth.set_security_questions(row2[0],
                        [v.get() for v in sq_vars], [v.get() for v in sa_vars])
                win.destroy(); self._usr_load()
            else: ev.set(msg)

        bf_user=tk.Frame(win,bg=T["BG"]); bf_user.pack(fill="x",padx=32,pady=(4,12))
        btn(bf_user,"SAVE",save,"primary",(0,0)).pack(fill="x",ipady=10,pady=(0,4))
        btn(bf_user,"Cancel",win.destroy,"ghost").pack(fill="x")

    # ═══════════════════════════ BACKUPS ═════════════════════════════════════
    def _page_backups(self):
        root=tk.Frame(self._content,bg=T["BG"]); root.pack(fill="both",expand=True,padx=14,pady=10)
        tb=tk.Frame(root,bg=T["BG"]); tb.pack(fill="x",pady=(0,8))
        lbl(tb,"BACKUP & RESTORE",14,True).pack(side="left")
        btn(tb,"↩  Restore",self._bkp_restore,"blue").pack(side="right")
        btn(tb,"💾  Create Backup",self._bkp_create,"primary").pack(side="right",padx=(0,8))
        lbl(root,f"Backup folder:  {backup_manager.get_backup_dir()}",9,color=T["TEXT3"],bg=T["BG"]).pack(anchor="w",pady=(0,8))
        apply_tv("Bkp")
        cols=("Filename","Created","Size","Created By","Notes","On Disk")
        self._bkp_tv=ttk.Treeview(root,columns=cols,show="headings",style="Bkp.Treeview")
        for c,w in zip(cols,[220,130,70,110,200,60]):
            self._bkp_tv.heading(c,text=c); self._bkp_tv.column(c,width=w)
        bs=ttk.Scrollbar(root,orient="vertical",command=self._bkp_tv.yview)
        self._bkp_tv.config(yscrollcommand=bs.set)
        bs.pack(side="right",fill="y"); self._bkp_tv.pack(fill="both",expand=True)
        ar=tk.Frame(root,bg=T["BG"]); ar.pack(fill="x",pady=6)
        btn(ar,"🗑  Delete Selected",self._bkp_del,"red",(10,5)).pack(side="left")
        self._bkp_load()

    def _bkp_load(self):
        self._bkp_tv.delete(*self._bkp_tv.get_children())
        for b in backup_manager.list_backups():
            sz=f"{b['size_bytes']//1024}KB" if b.get("size_bytes") else "?"
            self._bkp_tv.insert("","end",values=(
                b["filename"],(b["created_at"] or "")[:16],sz,
                b.get("username",""),b.get("notes",""),
                "✓" if b.get("exists") else "✗"),tags=(str(b["id"]),))

    def _bkp_create(self):
        notes=simpledialog.askstring("Backup","Notes (optional):",parent=self) or "Manual backup"
        ok,path,msg=backup_manager.create_backup(auth.current_user["id"],auth.current_user["username"],notes)
        messagebox.showinfo("Backup",msg,parent=self)
        if ok: self._bkp_load()

    def _bkp_restore(self):
        path=filedialog.askopenfilename(filetypes=[("ZIP Backup","*.zip")],title="Select Backup")
        if not path: return
        if not messagebox.askyesno("Restore","This will OVERWRITE the current database.\nContinue?",parent=self): return
        ok,msg=backup_manager.restore_backup(path,auth.current_user["id"],auth.current_user["username"])
        messagebox.showinfo("Restore",msg,parent=self)

    def _bkp_del(self):
        sel=self._bkp_tv.selection()
        if not sel: return
        for t in self._bkp_tv.item(sel[0],"tags"):
            if t.isdigit():
                if messagebox.askyesno("Delete","Delete this backup?",parent=self):
                    ok,msg=backup_manager.delete_backup(int(t),auth.current_user["id"],auth.current_user["username"])
                    messagebox.showinfo("Result",msg,parent=self); self._bkp_load()
                return

    # ═══════════════════════════ SETTINGS ════════════════════════════════════
    def _page_settings(self):
        root=tk.Frame(self._content,bg=T["BG"]); root.pack(fill="both",expand=True)
        _watermark(root)
        outer,inner=scrolled_frame(root); outer.pack(fill="both",expand=True)
        px=20
        self.after(100, lambda: propagate_scroll(inner))
        lbl(inner,"SYSTEM SETTINGS",14,True).pack(anchor="w",padx=px,pady=(14,10))
        fv={}

        def section(title):
            lbl(inner,title,9,True,T["TEXT3"],bg=T["BG"]).pack(anchor="w",padx=px,pady=(14,2))
            card=tk.Frame(inner,bg=T["CARD"],highlightbackground=T["BORDER"],highlightthickness=1)
            card.pack(fill="x",padx=px,pady=(0,4))
            return card

        def field(card,key,label_txt,placeholder="",width=36):
            r=tk.Frame(card,bg=T["CARD"]); r.pack(fill="x",padx=16,pady=8)
            lbl(r,label_txt,9,color=T["TEXT2"],bg=T["CARD"],width=24,anchor="w").pack(side="left")
            v=tk.StringVar(value=get_setting(key,placeholder))
            entry(r,v,width=width).pack(side="left",ipady=6,padx=(8,0))
            fv[key]=v

        def toggle(card,key,label_txt):
            r=tk.Frame(card,bg=T["CARD"]); r.pack(fill="x",padx=16,pady=8)
            lbl(r,label_txt,9,color=T["TEXT2"],bg=T["CARD"]).pack(side="left",expand=True,fill="x")
            v=tk.BooleanVar(value=get_setting(key,"0")=="1")
            def on_tog(): set_setting(key,"1" if v.get() else "0")
            tk.Checkbutton(r,variable=v,command=on_tog,bg=T["CARD"],fg=T["TEXT"],
                           selectcolor=T["IN_BG"],activebackground=T["CARD"]).pack(side="right")

        c=section("STORE INFORMATION")
        field(c,"shop_name","Shop / Business Name")
        field(c,"shop_address","Street Address")
        field(c,"shop_phone","Phone Number")
        field(c,"shop_email","Email Address")

        # M-PESA / PAYMENT DETAILS
        c=section("M-PESA & PAYMENT DETAILS")
        field(c,"paybill_number","Paybill Number","",16)
        field(c,"till_number","Buy Goods Till Number","",16)
        field(c,"send_money_name","Send Money (Name/Number)","",20)
        field(c,"pochi_number","Pochi la Biashara Number","",16)

        # Payment methods active toggles
        lbl(inner,"PAYMENT METHODS (shown on POS)",9,True,T["TEXT3"],bg=T["BG"]).pack(
            anchor="w",padx=px,pady=(14,2))
        pmc=tk.Frame(inner,bg=T["CARD"],highlightbackground=T["BORDER"],highlightthickness=1)
        pmc.pack(fill="x",padx=px,pady=(0,4))
        conn=get_connection()
        pm_rows=conn.execute("SELECT id,name,label,is_active FROM payment_methods ORDER BY sort_order").fetchall()
        conn.close()
        self._pm_vars={}
        for pm in pm_rows:
            r=tk.Frame(pmc,bg=T["CARD"]); r.pack(fill="x",padx=16,pady=6)
            v=tk.BooleanVar(value=bool(pm["is_active"]))
            self._pm_vars[pm["id"]]=v
            lbl(r,pm["label"],10,bg=T["CARD"]).pack(side="left")
            lbl(r,f"  ({pm['name']})",9,color=T["TEXT3"],bg=T["CARD"]).pack(side="left")
            tk.Checkbutton(r,variable=v,bg=T["CARD"],fg=T["TEXT"],
                           selectcolor=T["IN_BG"],activebackground=T["CARD"]).pack(side="right")

        # CATEGORIES
        lbl(inner,"CATEGORIES",9,True,T["TEXT3"],bg=T["BG"]).pack(anchor="w",padx=px,pady=(14,2))
        cat_card=tk.Frame(inner,bg=T["CARD"],highlightbackground=T["BORDER"],highlightthickness=1)
        cat_card.pack(fill="x",padx=px,pady=(0,4))
        cat_list_frame=tk.Frame(cat_card,bg=T["CARD"]); cat_list_frame.pack(fill="x",padx=14,pady=8)
        self._cat_listbox=tk.Listbox(cat_list_frame,bg=T["IN_BG"],fg=T["TEXT"],
                                     font=F(10),relief="flat",height=8,
                                     selectbackground=T["SEL"],selectforeground=T["TEXT"],
                                     highlightthickness=0)
        cat_sb=ttk.Scrollbar(cat_list_frame,orient="vertical",command=self._cat_listbox.yview)
        self._cat_listbox.config(yscrollcommand=cat_sb.set)
        cat_sb.pack(side="right",fill="y"); self._cat_listbox.pack(fill="x",expand=True)
        self._refresh_cat_list()
        car=tk.Frame(cat_card,bg=T["CARD"]); car.pack(fill="x",padx=14,pady=(0,8))
        self._new_cat=tk.StringVar()
        entry(car,self._new_cat,width=20).pack(side="left",ipady=6)
        btn(car,"Add",self._add_category,"green",(8,5)).pack(side="left",padx=4)
        btn(car,"Delete Selected",self._del_category,"red",(8,5)).pack(side="left")

        c=section("RECEIPT")
        field(c,"receipt_header","Header Line")
        field(c,"receipt_footer","Footer / Thank-you")
        toggle(c,"receipt_show_tax","Show tax line on receipt")

        c=section("PRICING & TAX")
        field(c,"currency_symbol","Currency Symbol","KSh",8)
        field(c,"currency_name","Currency Name","KES",12)
        field(c,"tax_rate","Tax Rate (%)","0",10)
        field(c,"tax_name","Tax Label (VAT / GST)","VAT",14)
        toggle(c,"tax_inclusive","Prices are tax-inclusive")

        c=section("INVENTORY")
        field(c,"default_low_stock","Default Low Stock Threshold","5",10)
        field(c,"default_unit","Default Unit","pcs",12)
        toggle(c,"track_stock","Track stock levels")
        toggle(c,"warn_out_of_stock","Warn when item is out of stock")
        toggle(c,"allow_negative_stock","Allow selling below zero stock")

        c=section("SALES")
        toggle(c,"auto_print_receipt","Auto-print receipt after sale")
        field(c,"max_discount_pct","Maximum Discount Allowed (%)","100",10)

        c=section("APPEARANCE")
        lbl(inner,"THEME",9,True,T["TEXT3"],bg=T["BG"]).pack(anchor="w",padx=px,pady=(14,2))
        thc=tk.Frame(inner,bg=T["CARD"],highlightbackground=T["BORDER"],highlightthickness=1)
        thc.pack(fill="x",padx=px,pady=(0,4))
        th_row=tk.Frame(thc,bg=T["CARD"]); th_row.pack(fill="x",padx=16,pady=12)
        th_var=tk.StringVar(value=get_setting("theme","dark"))
        for th in ("dark","light"):
            tk.Radiobutton(th_row,text=th.title()+" Mode",variable=th_var,value=th,
                           font=F(10),bg=T["CARD"],fg=T["TEXT"],
                           selectcolor=T["IN_BG"],activebackground=T["CARD"],
                           command=lambda v=th: (apply_theme(v),
                               messagebox.showinfo("Theme","Restart to fully apply theme.",parent=self))
                           ).pack(side="left",padx=12)

        c=section("PRINTER")
        field(c,"printer_command","Print Command","lp",24)

        c=section("BACKUP")
        field(c,"backup_path","Backup Directory","",40)
        toggle(c,"auto_backup","Enable automatic backups")

        hsep(inner)
        bf=tk.Frame(inner,bg=T["BG"]); bf.pack(anchor="w",padx=px,pady=12)

        def save_all():
            for k,v in fv.items(): set_setting(k,v.get())
            # Save payment method toggles
            conn2=get_connection()
            for pid2,v2 in self._pm_vars.items():
                conn2.execute("UPDATE payment_methods SET is_active=? WHERE id=?",
                              (1 if v2.get() else 0,pid2))
            conn2.commit(); conn2.close()
            messagebox.showinfo("Saved","All settings saved.",parent=self)
            self._build_sidebar()

        btn(bf,"SAVE ALL SETTINGS",save_all,"primary").pack(side="left",padx=(0,8))

        # Change password
        lbl(inner,"CHANGE YOUR PASSWORD",9,True,T["TEXT3"],bg=T["BG"]).pack(anchor="w",padx=px,pady=(14,2))
        pc=section("PASSWORD")
        pv1=tk.StringVar(); pv2=tk.StringVar()
        for label_txt,var in [("New Password",pv1),("Confirm Password",pv2)]:
            r=tk.Frame(pc,bg=T["CARD"]); r.pack(fill="x",padx=16,pady=8)
            lbl(r,label_txt,9,color=T["TEXT2"],bg=T["CARD"],width=22,anchor="w").pack(side="left")
            entry(r,var,show="*",width=28).pack(side="left",ipady=6,padx=8)
        def chg_pw():
            if pv1.get()!=pv2.get(): messagebox.showerror("Error","Passwords do not match.",parent=self); return
            ok,msg=auth.change_password(auth.current_user["id"],pv1.get())
            messagebox.showinfo("Password",msg,parent=self); pv1.set(""); pv2.set("")
        bf2=tk.Frame(inner,bg=T["BG"]); bf2.pack(anchor="w",padx=px,pady=(6,24))
        btn(bf2,"CHANGE PASSWORD",chg_pw,"blue").pack()

    def _refresh_cat_list(self):
        self._cat_listbox.delete(0,"end")
        for c in get_categories(): self._cat_listbox.insert("end",c)

    def _add_category(self):
        name=self._new_cat.get().strip()
        if not name: return
        conn=get_connection()
        try:
            conn.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)",(name,))
            conn.commit()
        finally: conn.close()
        self._new_cat.set(""); self._refresh_cat_list()

    def _del_category(self):
        sel=self._cat_listbox.curselection()
        if not sel: return
        name=self._cat_listbox.get(sel[0])
        if messagebox.askyesno("Delete Category",f"Delete category '{name}'?",parent=self):
            conn=get_connection()
            conn.execute("DELETE FROM categories WHERE name=?",(name,))
            conn.commit(); conn.close()
            self._refresh_cat_list()

    # ═══════════════════════════ AUDIT ═══════════════════════════════════════
    def _page_audit(self):
        root=tk.Frame(self._content,bg=T["BG"]); root.pack(fill="both",expand=True,padx=14,pady=10)
        # Toolbar
        tb=tk.Frame(root,bg=T["BG"]); tb.pack(fill="x",pady=(0,8))
        lbl(tb,"AUDIT LOG",14,True).pack(side="left")
        _watermark(root)

        # Filters
        ff=tk.Frame(root,bg=T["CARD"],highlightbackground=T["BORDER"],highlightthickness=1)
        ff.pack(fill="x",pady=(0,8))
        fr=tk.Frame(ff,bg=T["CARD"]); fr.pack(fill="x",padx=14,pady=8)
        lbl(fr,"ACTION",9,color=T["TEXT3"],bg=T["CARD"]).pack(side="left",padx=(0,4))
        all_logs = report_manager.get_audit_logs(2000)
        actions = ["All"] + sorted(set(l.get("action","") for l in all_logs if l.get("action")))
        self._aud_action=tk.StringVar(value="All")
        combo(fr,self._aud_action,actions,width=18).pack(side="left")
        lbl(fr,"USER",9,color=T["TEXT3"],bg=T["CARD"]).pack(side="left",padx=(14,4))
        users = ["All"] + sorted(set(l.get("username","") for l in all_logs if l.get("username")))
        self._aud_user=tk.StringVar(value="All")
        combo(fr,self._aud_user,users,width=14).pack(side="left")
        lbl(fr,"SEARCH",9,color=T["TEXT3"],bg=T["CARD"]).pack(side="left",padx=(14,4))
        self._aud_search=tk.StringVar()
        entry(fr,self._aud_search,width=20).pack(side="left",ipady=5)
        btn(fr,"Filter",self._audit_reload,"primary",(8,4)).pack(side="left",padx=(10,0))
        btn(fr,"Clear",lambda:(self._aud_action.set("All"),self._aud_user.set("All"),
                                self._aud_search.set(""),self._audit_reload()),
            "ghost",(8,4)).pack(side="left",padx=4)
        lbl(fr,f"  {len(all_logs)} total entries",9,color=T["TEXT3"],bg=T["CARD"]).pack(side="left",padx=(10,0))

        apply_tv("Aud")
        cols=("Time","User","Action","Details")
        self._aud_tv=ttk.Treeview(root,columns=cols,show="headings",style="Aud.Treeview")
        for c,w in zip(cols,[140,100,130,460]):
            self._aud_tv.heading(c,text=c); self._aud_tv.column(c,width=w)
        sc2=ttk.Scrollbar(root,orient="vertical",command=self._aud_tv.yview)
        self._aud_tv.config(yscrollcommand=sc2.set)
        sc2.pack(side="right",fill="y"); self._aud_tv.pack(fill="both",expand=True)
        self._aud_all_logs = all_logs
        self._audit_reload()

    def _audit_reload(self):
        action_f = self._aud_action.get()
        user_f   = self._aud_user.get()
        search_f = self._aud_search.get().lower()
        self._aud_tv.delete(*self._aud_tv.get_children())
        for log in self._aud_all_logs:
            act = log.get("action","")
            usr = log.get("username","")
            det = log.get("details","") or ""
            if action_f != "All" and act != action_f: continue
            if user_f   != "All" and usr != user_f:   continue
            if search_f and search_f.lower() not in act.lower() and search_f.lower() not in usr.lower() and search_f.lower() not in det.lower(): continue
            self._aud_tv.insert("","end",values=(
                (log.get("created_at") or "")[:16], usr, act, det))


    # ─── Calendar date picker ────────────────────────────────────────────────
    def _show_calendar(self, date_var):
        """Mini month-grid calendar popup that sets date_var on click."""
        try:
            y, m, d = [int(x) for x in date_var.get().split("-")]
        except:
            now = datetime.now(); y, m, d = now.year, now.month, now.day
        import calendar as cal_mod

        win = tk.Toplevel(self); win.title("Select Date")
        win.configure(bg=T["BG"]); win.resizable(False, False)
        win.transient(self); win.after(50, lambda: win.grab_set() if win.winfo_exists() else None)
        win.geometry("+%d+%d" % (self.winfo_rootx()+200, self.winfo_rooty()+120))
        _watermark(win)

        state = {"y": y, "m": m}

        def build(sy, sm):
            for w in win.winfo_children(): w.destroy()
            hdr = tk.Frame(win, bg=T["SIDEBAR"]); hdr.pack(fill="x", padx=0, pady=0)
            btn(hdr, "◀", lambda: build(sy if sm>1 else sy-1, sm-1 if sm>1 else 12),
                "ghost", (8,6)).pack(side="left")
            lbl(hdr, f"{cal_mod.month_name[sm]}  {sy}", 11, True,
                bg=T["SIDEBAR"]).pack(side="left", expand=True)
            btn(hdr, "▶", lambda: build(sy if sm<12 else sy+1, sm+1 if sm<12 else 1),
                "ghost", (8,6)).pack(side="right")

            grid = tk.Frame(win, bg=T["BG"], padx=8, pady=6); grid.pack()
            for ci, dn in enumerate(["Mo","Tu","We","Th","Fr","Sa","Su"]):
                lbl(grid, dn, 8, True, T["TEXT3"], bg=T["BG"]).grid(row=0, column=ci, padx=4, pady=2)

            month_cal = cal_mod.monthcalendar(sy, sm)
            for ri, week in enumerate(month_cal, 1):
                for ci, day in enumerate(week):
                    if day == 0:
                        lbl(grid, "", 10, bg=T["BG"]).grid(row=ri, column=ci)
                    else:
                        is_sel = (day == d and sy == y and sm == m)
                        bg2 = T["ACCENT"] if is_sel else T["CARD2"]
                        fg2 = "#000" if is_sel else T["TEXT"]
                        b = tk.Button(grid, text=str(day), width=3,
                                      font=F(10, is_sel), bg=bg2, fg=fg2,
                                      activebackground=T["ACCENT"], activeforeground="#000",
                                      relief="flat", cursor="hand2", bd=0,
                                      highlightthickness=0)
                        b.grid(row=ri, column=ci, padx=2, pady=2, ipady=3)
                        def pick(dy=day, sy_=sy, sm_=sm):
                            date_var.set(f"{sy_:04d}-{sm_:02d}-{dy:02d}")
                            win.destroy()
                        b.config(command=pick)
            state["y"] = sy; state["m"] = sm

        build(y, m)

    # ─── View receipt items from reports ─────────────────────────────────────
    def _view_receipt_items(self):
        sel = self._rep_tv.selection()
        if not sel: return
        vals = self._rep_tv.item(sel[0], "values")
        if not vals: return
        receipt_num = vals[0]
        sym = get_setting("currency_symbol","KSh")

        # Look up the sale
        conn = get_connection()
        sale = conn.execute(
            "SELECT * FROM sales WHERE receipt_number=?", (receipt_num,)
        ).fetchone()
        items = conn.execute(
            "SELECT * FROM sale_items WHERE sale_id=?",
            (sale["id"],)
        ).fetchall() if sale else []
        cashier_row = conn.execute(
            "SELECT full_name FROM users WHERE id=?", (sale["cashier_id"],)
        ).fetchone() if sale else None
        conn.close()

        if not sale:
            messagebox.showinfo("Not Found", f"Receipt {receipt_num} not found.", parent=self)
            return

        win = tk.Toplevel(self); win.title(f"Receipt — {receipt_num}")
        win.configure(bg=T["BG"]); win.geometry("500x600")
        win.transient(self); win.resizable(True, True)
        win.minsize(420, 400)

        # Watermark + buttons pinned at bottom BEFORE scrollable content
        _watermark(win)
        cashier_name = cashier_row["full_name"] if cashier_row else "—"
        sd_for_print = {
            "receipt_number": receipt_num, "cashier": cashier_name,
            "items": [{"name":it["product_name"],"qty":it["quantity"],"price":it["unit_price"]}
                      for it in items],
            "subtotal": sale["subtotal"], "discount": sale["discount"],
            "tax": sale["tax"], "total": sale["total"],
            "payment_method": sale["payment_method"],
            "amount_tendered": sale["amount_tendered"],
            "change": sale["change_given"],
            "created_at": sale["created_at"],
        }
        bf = tk.Frame(win, bg=T["BG"]); bf.pack(side="bottom", fill="x", padx=16, pady=(4,10))
        btn(bf, "🖨  Reprint", lambda: self._print_receipt(sd_for_print), "blue").pack(side="right", padx=(0,8))
        btn(bf, "Close", win.destroy, "ghost").pack(side="right")

        # Scrollable content area
        vri_can = tk.Canvas(win, bg=T["BG"], highlightthickness=0)
        vri_sb  = ttk.Scrollbar(win, orient="vertical", command=vri_can.yview)
        vri_can.configure(yscrollcommand=vri_sb.set)
        vri_sb.pack(side="right", fill="y")
        vri_can.pack(side="left", fill="both", expand=True)
        sc = tk.Frame(vri_can, bg=T["BG"])
        _scw = vri_can.create_window((0,0), window=sc, anchor="nw")
        sc.bind("<Configure>",    lambda e: vri_can.configure(scrollregion=vri_can.bbox("all")))
        vri_can.bind("<Configure>", lambda e: vri_can.itemconfig(_scw, width=e.width))
        def _vri_bind(e):
            vri_can.bind_all("<MouseWheel>", lambda ev: vri_can.yview_scroll(int(-1*(ev.delta/120)),"units"))
            vri_can.bind_all("<Button-4>",   lambda ev: vri_can.yview_scroll(-1,"units"))
            vri_can.bind_all("<Button-5>",   lambda ev: vri_can.yview_scroll( 1,"units"))
        def _vri_unbind(e):
            vri_can.unbind_all("<MouseWheel>"); vri_can.unbind_all("<Button-4>"); vri_can.unbind_all("<Button-5>")
        vri_can.bind("<Enter>", _vri_bind); vri_can.bind("<Leave>", _vri_unbind)
        sc.bind("<Enter>", _vri_bind); sc.bind("<Leave>", _vri_unbind)

        lbl(sc, f"RECEIPT DETAILS", 13, True, T["ACCENT"], bg=T["BG"]).pack(pady=(16,4))
        lbl(sc, receipt_num, 10, False, T["TEXT3"], bg=T["BG"]).pack()

        # Sale metadata
        mf = tk.Frame(sc, bg=T["CARD"], highlightbackground=T["BORDER"], highlightthickness=1)
        mf.pack(fill="x", padx=16, pady=10)
        for label_txt, val in [
            ("Date",    (sale["created_at"] or "")[:16]),
            ("Cashier", cashier_name),
            ("Method",  (sale["payment_method"] or "").upper()),
            ("Status",  sale["status"]),
        ]:
            r = tk.Frame(mf, bg=T["CARD"]); r.pack(fill="x", padx=14, pady=4)
            lbl(r, label_txt, 9, color=T["TEXT3"], bg=T["CARD"]).pack(side="left")
            lbl(r, val, 10, True, bg=T["CARD"]).pack(side="right")

        # Items table
        lbl(sc, "ITEMS SOLD", 9, True, T["TEXT3"], bg=T["BG"]).pack(anchor="w", padx=16, pady=(4,2))
        apply_tv("RcpI")
        cols = ("Product", "Qty", "Unit Price", "Subtotal")
        tv_row = tk.Frame(sc, bg=T["BG"]); tv_row.pack(fill="x", padx=16)
        tv = ttk.Treeview(tv_row, columns=cols, show="headings", style="RcpI.Treeview", height=min(len(items),8))
        for c, w in zip(cols, [220, 55, 95, 95]):
            tv.heading(c, text=c); tv.column(c, width=w)
        isb = ttk.Scrollbar(tv_row, orient="vertical", command=tv.yview)
        tv.config(yscrollcommand=isb.set)
        isb.pack(side="right", fill="y"); tv.pack(side="left", fill="both", expand=True)
        for it in items:
            tv.insert("","end", values=(
                it["product_name"], f"{it['quantity']:.0f}",
                f"{sym} {it['unit_price']:.2f}",
                f"{sym} {it['subtotal']:.2f}"))

        # Totals footer
        tf = tk.Frame(sc, bg=T["CARD"], highlightbackground=T["BORDER"], highlightthickness=1)
        tf.pack(fill="x", padx=16, pady=10)
        for label_txt, val, big in [
            ("Subtotal",  f"{sym} {sale['subtotal']:.2f}",  False),
            ("Discount",  f"-{sym} {sale['discount']:.2f}", False),
            ("Tax",       f"{sym} {sale['tax']:.2f}",       False),
            ("TOTAL",     f"{sym} {sale['total']:.2f}",     True),
        ]:
            r = tk.Frame(tf, bg=T["CARD"]); r.pack(fill="x", padx=14, pady=(6 if big else 3))
            lbl(r, label_txt, 12 if big else 9, big,
                T["ACCENT"] if big else T["TEXT2"], bg=T["CARD"]).pack(side="left")
            lbl(r, val, 12 if big else 9, big,
                T["ACCENT"] if big else T["TEXT"], bg=T["CARD"]).pack(side="right")

        if sale["payment_method"] == "cash":
            r = tk.Frame(tf, bg=T["CARD"]); r.pack(fill="x", padx=14, pady=3)
            lbl(r,"Tendered", 9,color=T["TEXT2"],bg=T["CARD"]).pack(side="left")
            lbl(r,f"{sym} {sale['amount_tendered']:.2f}",9,bg=T["CARD"]).pack(side="right")
            r2 = tk.Frame(tf, bg=T["CARD"]); r2.pack(fill="x", padx=14, pady=(3,8))
            lbl(r2,"Change", 9,color=T["TEXT2"],bg=T["CARD"]).pack(side="left")
            lbl(r2,f"{sym} {sale['change_given']:.2f}",9,T["GREEN"],bg=T["CARD"]).pack(side="right")

        sc.update_idletasks()
        vri_can.configure(scrollregion=vri_can.bbox("all"))


if __name__ == "__main__":
    AlchemyPOS()

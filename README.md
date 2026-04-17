# AlchemyPOS

**Professional offline point-of-sale system**  
Designed for retail businesses. No internet. No subscription. No cloud.

---

## Quick Start

### Windows (Recommended)
1. Install Python 3.8+ from https://www.python.org/downloads/
   - **Important**: Check "Add Python to PATH" during installation
2. Run `build.bat` from the project folder
3. Execute `dist\AlchemyPOS.exe`

### Linux / macOS
```bash
python3 -m pip install pyinstaller reportlab
python3 main.py
```

---

## Building for Distribution

### Windows EXE Build
```batch
REM Full build with icon
build.bat

REM Clean all artifacts
build.bat clean
```

Output: `dist\AlchemyPOS.exe` (~80MB standalone executable)

The Windows build script automatically embeds `setup_files\app.manifest` when present, enabling native Per-Monitor DPI awareness for sharper text on high-DPI displays.

**Requirements:**
- Python 3.8+ (with pip)
- PyInstaller: `pip install pyinstaller`
- ReportLab: `pip install reportlab` (for PDF reports)

---

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [First Launch](#first-launch)
- [User Roles](#user-roles)
- [POS Terminal](#pos-terminal)
- [Inventory](#inventory)
- [Reports](#reports)
- [Users](#users)
- [Backups](#backups)
- [Settings](#settings)
- [Audit Log](#audit-log)
- [Security](#security)
- [Payment Methods](#payment-methods)
- [Printing](#printing)
- [File Structure](#file-structure)
- [Troubleshooting](#troubleshooting)

---

## Requirements

| Component | Requirement |
|-----------|-------------|
| OS | Windows 10/11, Linux (Kali, Ubuntu 20.04+, Debian 11+) |
| Python | 3.8 or later |
| Tkinter | Bundled with most Python installers (Linux: `sudo apt install python3-tk`) |
| ReportLab | `pip install reportlab --break-system-packages` *(PDF export only — optional)* |
| Display | 1280 × 720 minimum |
| Disk | 100 MB free |

All other dependencies (`sqlite3`, `csv`, `zipfile`, `hashlib`) are part of the Python standard library.

---

## Installation

```bash
# 1. Extract the archive
unzip AlchemyPOS.zip
cd alchemypos

# 2. Launch directly
python3 main.py
```

For Windows, use the built EXE from `dist\AlchemyPOS.exe`
---

## First Launch

The first time AlchemyPOS starts, a **Setup Wizard** opens. There is no pre-installed admin account — you create your own.

**You will set:**
1. Administrator username
2. Administrator password
3. Three security questions and answers (required for password self-recovery)

Once the account is created, log in and go to **Settings** to configure your shop name, address, phone number, M-Pesa details, and tax rate before making any sales.

---

## Features

- **Full offline operation** — No internet required
- **Multi-role access control** — Cashier, Inventory Manager, Admin
- **Product search & categorization** — Fast barcode + text search
- **Dynamic pricing & discounts** — Per-transaction discounts
- **Multiple payment methods** — Cash, M-Pesa, Paybill, Till, Send Money, Pochi
- **Real-time inventory tracking** — Low-stock alerts
- **Daily/weekly/monthly reports** — Revenue, profit, tax, payment breakdown
- **Portable & distributable** — Single ~80MB EXE for Windows (no dependencies)
- **Smooth scrolling** — Mouse wheel support across all windows
- **Responsive UI** — Dark & light themes, 1280×720 minimum
- **Secure authentication** — Hashed passwords, security questions
- **Audit trail** — Full system log for compliance

---

## User Roles

Three roles with distinct access levels:

| Module | Cashier | Inv. Manager | Admin |
|--------|:-------:|:------------:|:-----:|
| POS Terminal | ✓ | ✓ | ✓ |
| Inventory | — | ✓ | ✓ |
| Reports | — | — | ✓ |
| Users | — | — | ✓ |
| Backups | — | — | ✓ |
| Settings | — | — | ✓ |
| Audit Log | — | — | ✓ |

**Cashier** — Sells goods, processes payments, prints receipts. No access to stock, prices, or business data.

**Inventory Manager** — Everything a cashier can do, plus full stock management: add/edit/delete products, adjust quantities, import from CSV. Cannot view sales reports or change system settings.

**Admin** — Unrestricted access. Manages users, configures the system, views all reports, creates backups, and reads the audit log.

---

## POS Terminal

The main selling screen. Opens immediately after login.

### Layout
- **Left panel** — product grid, search bar, category filter
- **Right panel** — cart, totals, discount field, payment buttons

### Selling
1. Type a product name or scan a barcode into the search box
2. Use the category tabs to browse by category
3. Click a product card to add it to the cart
4. Use **＋** / **−** in the cart to adjust quantity, **✕** to remove
5. Enter a discount amount (in KSh) if applicable
6. Click a payment method button to open the payment screen

### Rules
- **Out-of-stock products are hidden** — if a product has zero stock it will not appear on the POS grid. Restock it in Inventory to make it sellable again.
- **Stock counts are not shown** on product cards — only name and price. Stock information is for the Inventory screen.
- Search is case-insensitive and matches both product name and barcode.

### Payment
- **Cash** — enter the amount tendered; change is calculated and displayed. Quick-denomination buttons appear for common values.
- **M-Pesa / Paybill / Till / Send Money / Pochi** — your configured account details are displayed for the cashier to read to the customer before confirming the sale.
- After completing a sale, a receipt popup opens automatically.
- **Quick Cash + Print** button completes a cash sale for the exact amount and sends it directly to the printer.

---

## Inventory

Accessible to Admins and Inventory Managers.

### Stock Alerts Panel *(right column, top)*
Live list of all products that are out of stock or below their low-stock threshold.
- **Red** = out of stock (quantity = 0)
- **Yellow** = low stock (quantity ≤ low-stock threshold)
- Click any item to jump to it in the main product list.

### Product Detail Panel *(right column, bottom)*
Displays full details of the selected product. Includes a **Quick Stock Adjust** widget for rapid restocking without opening the full edit dialog.

### Actions

| Button | Action |
|--------|--------|
|  Add Product | Create a new product |
|  Edit | Edit the selected product |
|  Delete | Soft-delete (hidden from POS, data kept) |
|  Adjust Stock | Add or subtract stock with a reason note |
|  Import CSV | Bulk-import products from a file |
|  Export CSV | Export all products to CSV |
|  Sample CSV | Download a blank template to fill in |

### CSV Import Format

```
name,category,price,cost,unit,barcode,quantity,low_stock_threshold
Unga Pembe 2kg,Grains,200,135,bag,6009800340011,50,10
Brookside Milk 500ml,Dairy,75,48,packet,6009800140011,150,25
```

Only `name` and `price` are required. All other columns are optional. Rows with duplicate names or barcodes are skipped without error.

---

## Reports

Flexible sales reporting accessible to Admins.

### Filters
- Date range (calendar picker — no manual date typing)
- Cashier
- Payment method
- Free-text search (matches receipt number, cashier name, payment method)
- Quick filters: **Today**, **This Week**, **This Month**

### KPI Cards
Updated in real time as filters change:

| Card | Description |
|------|-------------|
| Transactions | Number of sales in the filtered period |
| Revenue | Total sales value |
| Discounts | Total discounts given |
| Average Sale | Revenue ÷ transactions |
| Tax Collected | Total tax amount |
| **Profit** | Revenue minus cost of goods sold |

### Panels
- **Sales History** — every transaction. Double-click a row to view the full itemised receipt and reprint it.
- **Top Products** — best sellers by quantity and by revenue
- **Payment Split** — revenue broken down by payment method
- **By Cashier** — transaction count and revenue per staff member

### Export
Reports and inventory can be exported as **CSV**, **XML**, or **PDF** (PDF requires ReportLab).

---

## Users

Admin only.

### Creating a User
1. Click **＋ Add User**
2. Enter username, full name, and password
3. Select role: **Cashier**, **Inventory Manager**, or **Admin**
4. Set three security questions and answers
5. Save

### Editing a User
Click a user row → **✏ Edit**. Leave security-answer fields blank to keep existing answers unchanged.

### Admin Actions
- **Reset Password** — set a new password for any user directly (bypasses security questions)
- **Deactivate** — disable the account without deleting it. The user cannot log in but their sales history is preserved.
- **Delete** — permanently remove the account

---

## Backups

Admin only.

### Creating a Backup
Click **Create Backup**. A timestamped `.zip` file containing the complete database is saved to the backup folder (configured in Settings). Add a note to identify the backup.

### Restoring
Click **Restore**, select a `.zip` file. A confirmation prompt is shown — restoring **overwrites the current database completely**. Use only to recover from data loss or to roll back an error.

**Recommended schedule:** Create a backup at the end of every business day.

---

## Settings

Admin only. Configure all system-wide parameters.

| Section | What you can set |
|---------|-----------------|
| Store Information | Shop name, address, phone, email |
| Receipt | Footer message |
| Tax & Currency | Tax rate (%), currency symbol (default: KSh) |
| Inventory | Default unit of measure, default low-stock threshold |
| M-Pesa & Payments | Paybill number, Till number, Send Money name, Pochi number |
| Payment Methods | Enable or disable individual payment methods |
| Stock Control | Allow sales below zero stock, show out-of-stock warnings |
| Printing | Printer command |
| Theme | Dark (default) or Light |
| Categories | Add, rename, or delete product categories |

**Theme changes require a restart to fully apply.**

---

## Audit Log

Admin only. A complete, immutable log of every significant system action.

### Logged Events
`LOGIN` · `LOGOUT` · `SALE` · `STOCK_ADJUST` · `PRODUCT_ADD` · `PRODUCT_EDIT` · `PRODUCT_DELETE` · `USER_CREATE` · `USER_EDIT` · `USER_DELETE` · `PASSWORD_RESET` · `BACKUP_CREATE` · `BACKUP_RESTORE` · `SETTINGS_CHANGE` · `IMPORT` · `EXPORT`

Filterable by action type, user, and free-text search. All searches are case-insensitive.

---

## Security

| Feature | Detail |
|---------|--------|
| Password hashing | PBKDF2-SHA256 · 310,000 iterations · unique random salt per user |
| Brute-force protection | Account locked for 15 minutes after 5 failed login attempts |
| Password self-recovery | Requires all 3 security questions answered correctly |
| Role enforcement | Enforced in application logic — not just hidden UI elements |
| SQL injection | All database queries use parameterised statements |
| Audit trail | Every state-changing action recorded with user, timestamp, and detail |
| Network | Zero outbound connections — fully air-gap compatible |

### Recommended Hardening
- Run the system on an encrypted disk partition
- Restrict OS user accounts to authorised staff only
- Back up the database to an external drive or encrypted location daily
- Do not share admin credentials with cashiers

---

## Payment Methods

| Method | How it works in AlchemyPOS |
|--------|--------------------------|
| Cash | Tendered amount entered; change calculated automatically |
| M-Pesa | Prompts cashier with your configured M-Pesa number |
| Paybill | Displays your Paybill number for customer to send to |
| Buy Goods Till | Displays your Till number |
| Send Money | Displays your registered send-money name |
| Pochi la Biashara | Displays your Pochi number |
| Card / Bank | Confirmation screen for POS terminal or bank transfer |

Configure your account numbers under **Settings → M-Pesa & Payment Details**.  
Enable or disable individual methods under **Settings → Payment Methods**.

---

## Printing

AlchemyPOS sends plain-text receipts to the system printer using the command configured in **Settings → Printing**.

| Setting | Default | Notes |
|---------|---------|-------|
| Printer command | `lp` | Change to `lpr` or a custom script if needed |

**If no printer is connected:** a plain-text receipt file is automatically saved in the application folder as `receipt_<receipt_number>.txt`.

**Check printer status:**
```bash
lpstat -p
```

**Test print:**
```bash
echo "Test" | lp
```

---

## File Structure

```
alchemypos/
├── main.py                      ← Application entry point
├── run.sh                       ← Launch script
├── install.sh                   ← One-time installer
├── README.md                    ← This file
├── alchemypos.db                ← SQLite database (created on first run)
│
├── database/
│   └── db.py                    ← Schema, migrations, settings helpers
│
├── authentication/
│   └── auth.py                  ← Login, lockout, roles, password hashing
│
├── inventory/
│   └── inventory.py             ← Products, stock levels, CSV import/export
│
├── sales/
│   └── sales.py                 ← Sale processing, receipt generation
│
├── reporting/
│   └── reports.py               ← Analytics, PDF/CSV/XML export
│
└── backup_manager/
    └── backup.py                ← Backup creation and restore
```

### Database Tables

| Table | Purpose |
|-------|---------|
| `users` | Staff accounts, hashed passwords, roles, security questions |
| `products` | Product catalogue |
| `inventory` | Stock quantities and low-stock thresholds |
| `sales` | Sale transactions |
| `sale_items` | Line items per sale |
| `categories` | Product category list |
| `payment_methods` | Available payment methods and enabled state |
| `settings` | All system configuration as key-value pairs |
| `audit_logs` | Timestamped action log |
| `backups` | Backup file metadata |

The database schema is initialised and migrated automatically on every launch. No manual SQL setup is needed.

---

## Troubleshooting

**`No module named 'tkinter'`**
```bash
sudo apt install python3-tk
```

**`No module named 'reportlab'`**  
PDF export will be disabled but the application will still run. CSV and XML export work without ReportLab. To enable PDF:
```bash
pip install reportlab --break-system-packages
```

**Receipt does not print**  
Check that your printer is configured and online:
```bash
lpstat -p
```
If no printer is available, AlchemyPOS saves a `.txt` receipt file in the application folder automatically. Check the printer command in **Settings → Printing** matches your system (`lp` on most Debian/Ubuntu systems, `lpr` on some others).

**Forgot password**  
Use the **Forgot Password** link on the login screen and answer all three security questions. If you cannot answer them, restore from the most recent backup that contains a working admin account.

**Database file is missing**  
Run `bash install.sh` again or `python3 -c "from database.db import init_database; init_database()"` from the `alchemypos/` directory to recreate an empty database.

**Screen layout is clipped**  
Minimum supported resolution is 1280 × 720. Maximise the window or increase display resolution. All panels and dialogs are independently scrollable.

**Text/UI looks blurry on Windows**  
Use a fresh EXE built with `build.bat` (includes DPI manifest support). The app also enables Windows DPI awareness at startup and uses `Segoe UI` on Windows for cleaner native text rendering.

**Inventory stock adjust does nothing**  
Stock changes now validate numeric input and show a clear error message if an update fails. If this happens, reopen the selected product and retry with a positive number in the stock adjust field.

**Application opens but shows a blank white window**  
This is a Tkinter/compositor conflict on some window managers. Try:
```bash
GDK_BACKEND=x11 python3 main.py
```

---

*AlchemyPOS — Built for reliability, designed for speed.*  
*Developer: njorogefrancis · njorogefrancis.dev@gmail.com · 0115634345*

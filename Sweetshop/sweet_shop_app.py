import os

# ADD THIS FUNCTION (just after imports)
def open_pdf(pdf_path):
    """Automatically open the generated bill on screen"""
    try:
        if os.name == 'nt':  # Windows
            os.startfile(pdf_path)
        elif os.name == 'posix':  # macOS or Linux
            os.system(f"open '{pdf_path}'" if sys.platform == 'darwin' else f"xdg-open '{pdf_path}'")
    except Exception as e:
        messagebox.showwarning("Cannot Open", f"PDF saved but could not open automatically.\nOpen manually from:\n{pdf_path}")
import os
import sqlite3
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ---------------------------
# Configuration
# ---------------------------
APP_TITLE = "Sweet Shop"
DB_FILE = "sweets.db"
IMAGES_DIR = "images"
RECEIPTS_DIR = "receipts"
LOGO_PATH = os.path.join(IMAGES_DIR, "logo.png")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(RECEIPTS_DIR, exist_ok=True)

# ---------------------------
# Database Setup
# ---------------------------
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS sweets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    category TEXT DEFAULT 'General',
    image TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    total REAL NOT NULL
)""")

c.execute("""CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    sweet_name TEXT NOT NULL,
    qty INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    subtotal REAL NOT NULL
)""")

conn.commit()

# Insert sample data if empty
c.execute("SELECT COUNT(*) FROM sweets")
if c.fetchone()[0] == 0:
    sample = [
        ("Gulab Jamun", 120, "Milk Sweets", "gulab_jamun.jpg"),
        ("Rasgulla", 100, "Bengali", "rasgulla.jpg"),
        ("Barfi", 150, "Dry Sweets", "barfi.jpg"),
        ("Jalebi", 80, "Deep Fried", "jalebi.jpg"),
        ("Kaju Katli", 200, "Dry Sweets", "kaju_katli.jpg"),
        ("Ladoo", 90, "Festival", "ladoo.jpg"),
        ("Son Papdi", 110, "Dry Sweets", "son_papdi.jpg"),
        ("Rasmalai", 180, "Bengali", "rasmalai.jpg"),
        ("Peda", 130, "Milk Sweets", "peda.jpg"),
        ("Sandesh", 160, "Bengali", "sandesh.jpg"),
    ]
    c.executemany("INSERT INTO sweets (name, price, category, image) VALUES (?,?,?,?)", sample)
    conn.commit()

# ---------------------------
# App State
# ---------------------------
cart = {}
loaded_images = {}

# ---------------------------
# Helpers
# ---------------------------
def get_sweets(search_term=None, category=None):
    query = "SELECT id, name, price, category, image FROM sweets"
    params = []
    clauses = []
    if search_term:
        clauses.append("name LIKE ?")
        params.append(f"%{search_term}%")
    if category and category != "All":
        clauses.append("category = ?")
        params.append(category)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY name"
    cur = conn.cursor()
    cur.execute(query, params)
    return cur.fetchall()

def get_sweet_by_id(sweet_id):
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, category, image FROM sweets WHERE id = ?", (sweet_id,))
    return cur.fetchone()

def load_image(path, size=(160, 160)):
    if not path:
        path = None
    key = (path, size)
    if key in loaded_images:
        return loaded_images[key]

    full_path = os.path.join(IMAGES_DIR, path) if path else None
    try:
        if full_path and os.path.exists(full_path):
            im = Image.open(full_path).convert("RGBA")
        else:
            # Cute fallback laddu
            im = Image.new("RGBA", (200, 200), (255, 248, 240))
            draw = ImageDraw.Draw(im)
            draw.ellipse([40, 40, 160, 160], fill=(255, 140, 0), outline=(200, 80, 0), width=12)
            draw.ellipse([65, 65, 135, 135], fill=(255, 180, 50))
        im.thumbnail(size, Image.LANCZOS)
        photo = ImageTk.PhotoImage(im)
        loaded_images[key] = photo
        return photo
    except Exception as e:
        print("Image error:", e)
        im = Image.new("RGBA", size, (240, 240, 240))
        photo = ImageTk.PhotoImage(im)
        loaded_images[key] = photo
        return photo

def format_price(p):
    return f"₹{p:.2f}"

# ---------------------------
# PROFESSIONAL PDF BILL
# ---------------------------
def generate_professional_receipt(order_id, items, total, customer_name, phone, address, save_path):
    c = canvas.Canvas(save_path, pagesize=A4)
    width, height = A4
    margin = 40
    y = height - 60

    # Logo
    if os.path.exists(LOGO_PATH):
        try:
            c.drawImage(LOGO_PATH, margin, y-60, width=80, height=80, preserveAspectRatio=True)
        except: pass

    # Shop Name
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width/2, y, "Pure Desi Ghee Sweets")
    c.setFont("Helvetica", 12)
    y -= 40

    # Bill Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "TAX INVOICE")
    c.drawRightString(width - margin, y, f"Bill No: {order_id}")
    y -= 25
    c.setFont("Helvetica", 11)
    c.drawString(margin, y, f"Date: {datetime.now().strftime('%d %B %Y, %I:%M %p')}")

    # Customer Box
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y-40, "Customer:")
    c.setFont("Helvetica", 11)
    c.drawString(margin+10, y-60, f"Name: {customer_name}")
    c.drawString(margin+10, y-80, f"Phone: {phone}")
    if address:
        lines = address.split('\n')
        for i, line in enumerate(lines[:2]):
            c.drawString(margin+10, y-100 - i*18, f"Addr: {line}")

    y -= 140

    # Table
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Item")
    c.drawRightString(width-margin-150, y, "Qty")
    c.drawRightString(width-margin-70, y, "Rate")
    c.drawRightString(width-margin, y, "Amount")
    y -= 20
    c.line(margin, y, width-margin, y)
    y -= 15

    c.setFont("Helvetica", 11)
    for name, qty, price, amt in items:
        c.drawString(margin, y, name[:30])
        c.drawRightString(width-margin-150, y, str(qty))
        c.drawRightString(width-margin-70, y, f"₹{price:.2f}")
        c.drawRightString(width-margin, y, f"₹{amt:.2f}")
        y -= 22

    y -= 10
    c.line(margin, y, width-margin, y)
    y -= 30
    c.setFont("Helvetica-Bold", 18)
    c.drawRightString(width-margin, y, f"TOTAL: ₹{total:.2f}")

    y -= 50
    c.setFont("Helvetica-Oblique", 12)
    c.drawCentredString(width/2, y, "Thank You! Visit Again")
    c.drawCentredString(width/2, y-20, "Sweet Wishes from Hadimba Sweet Mart")

    c.save()

# ---------------------------
# GUI Setup
# ---------------------------
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title(APP_TITLE)
app.geometry("1100x750")

# Header
header = ctk.CTkFrame(app)
header.pack(fill="x", padx=15, pady=10)

if os.path.exists(LOGO_PATH):
    try:
        logo_img = Image.open(LOGO_PATH).convert("RGBA")
        logo_img.thumbnail((80, 80), Image.LANCZOS)
        logo_photo = ImageTk.PhotoImage(logo_img)
        ctk.CTkLabel(header, image=logo_photo, text="").pack(side="left", padx=10)
        header.logo_photo = logo_photo
    except: pass

ctk.CTkLabel(header, text="Sweet Shop", font=("Arial", 28, "bold")).pack(side="left", padx=20)

search_var = ctk.StringVar()
category_var = ctk.StringVar(value="All")

search_entry = ctk.CTkEntry(header, width=300, placeholder_text="Search sweets...", textvariable=search_var)
search_entry.pack(side="left", padx=10)

cur = conn.cursor()
cur.execute("SELECT DISTINCT category FROM sweets ORDER BY category")
categories = ["All"] + [row[0] for row in cur.fetchall()]
category_menu = ctk.CTkOptionMenu(header, values=categories, variable=category_var)
category_menu.pack(side="left", padx=10)

view_cart_btn = ctk.CTkButton(header, text="View Cart (0)", width=150, fg_color="orange")
view_cart_btn.pack(side="right", padx=10)

content_frame = ctk.CTkScrollableFrame(app)
content_frame.pack(fill="both", expand=True, padx=15, pady=10)

footer = ctk.CTkFrame(app)
footer.pack(fill="x", padx=15, pady=10)

checkout_btn = ctk.CTkButton(footer, text="Quick Checkout", fg_color="green", width=180, height=40)
checkout_btn.pack(side="right", padx=10)

status_label = ctk.CTkLabel(footer, text="Ready • Browse and add sweets to cart", font=("Arial", 12))
status_label.pack(side="left", padx=10)

# ---------------------------
# Product Display
# ---------------------------
def refresh_products():
    for widget in content_frame.winfo_children():
        widget.destroy()

    sweets = get_sweets(search_var.get().strip(), category_var.get())
    row, col = 0, 0
    for sweet in sweets:
        sid, name, price, _, img_name = sweet
        frame = ctk.CTkFrame(content_frame, width=180, height=280, corner_radius=12)
        frame.grid(row=row, column=col, padx=12, pady=12)
        frame.grid_propagate(False)

        img = load_image(img_name)
        ctk.CTkLabel(frame, image=img, text="").pack(pady=10)
        ctk.CTkLabel(frame, text=name, font=("Arial", 14, "bold"), wraplength=160).pack(pady=5)
        ctk.CTkLabel(frame, text=format_price(price), font=("Arial", 16, "bold"), text_color="green").pack(pady=5)

        def add(sid=sid, n=name): 
            cart[sid] = cart.get(sid, 0) + 1
            update_cart_button()
            status_label.configure(text=f"Added {n}!")
        ctk.CTkButton(frame, text="+ Add", command=add).pack(pady=8)

        col += 1
        if col >= 5: col, row = 0, row + 1

# ---------------------------
# Cart & Checkout
# ---------------------------
def update_cart_button():
    view_cart_btn.configure(text=f"View Cart ({sum(cart.values())})")

def open_cart_window():
    if not cart:
        messagebox.showinfo("Empty", "Cart is empty!")
        return

    win = ctk.CTkToplevel(app)
    win.title("Cart")
    win.geometry("700x550")
    win.grab_set()

    items = []
    total = 0
    for sid, qty in cart.items():
        s = get_sweet_by_id(sid)
        if s:
            _, name, price, _, _ = s
            sub = price * qty
            total += sub
            items.append((sid, name, price, qty, sub))

    ctk.CTkLabel(win, text="Your Cart", font=("Arial", 20, "bold")).pack(pady=10)

    # Table
    table = ctk.CTkFrame(win)
    table.pack(fill="both", expand=True, padx=20, pady=10)
    headers = ["Item", "Qty", "Price", "Subtotal", ""]
    for i, h in enumerate(headers):
        ctk.CTkLabel(table, text=h, font=("Arial", 12, "bold")).grid(row=0, column=i, padx=10, pady=5)

    qty_vars = {}
    for r, (sid, name, price, qty, sub) in enumerate(items, 1):
        ctk.CTkLabel(table, text=name).grid(row=r, column=0, padx=10, sticky="w")
        var = ctk.IntVar(value=qty)
        qty_vars[sid] = var
        ctk.CTkEntry(table, textvariable=var, width=60).grid(row=r, column=1, padx=10)
        ctk.CTkLabel(table, text=format_price(price)).grid(row=r, column=2)
        ctk.CTkLabel(table, text=format_price(sub)).grid(row=r, column=3)
        ctk.CTkButton(table, text="Remove", fg_color="red",
                      command=lambda s=sid: [cart.pop(s, None), update_cart_button(), win.destroy(), open_cart_window()]).grid(row=r, column=4)

    ctk.CTkLabel(win, text=f"Total: {format_price(total)}", font=("Arial", 18, "bold")).pack(pady=10)

    def update_qty():
        for sid, var in qty_vars.items():
            q = var.get()
            if q <= 0: cart.pop(sid, None)
            else: cart[sid] = q
        update_cart_button()
        win.destroy()
        open_cart_window()

    btns = ctk.CTkFrame(win)
    btns.pack(pady=10)
    ctk.CTkButton(btns, text="Update", command=update_qty).pack(side="left", padx=10)
    ctk.CTkButton(btns, text="Clear", fg_color="red", command=lambda: [cart.clear(), update_cart_button(), win.destroy()]).pack(side="left", padx=10)

    # CHECKOUT BUTTON
    def start_checkout():
        win.destroy()
        checkout()  # This opens customer details window

    ctk.CTkButton(btns, text="Proceed to Checkout", fg_color="dark green", font=("Arial", 14, "bold"), command=start_checkout).pack(side="right", padx=20)

# ---------------------------
# FINAL CHECKOUT WITH CUSTOMER DETAILS
# ---------------------------
def checkout():
    if not cart:
        messagebox.showinfo("Empty", "Cart is empty!")
        return

    details_win = ctk.CTkToplevel(app)
    details_win.title("Customer Details")
    details_win.geometry("420x520")
    details_win.grab_set()

    ctk.CTkLabel(details_win, text="Customer Details", font=("Arial", 20, "bold")).pack(pady=20)

    name_var = ctk.StringVar()
    phone_var = ctk.StringVar()

    ctk.CTkLabel(details_win, text="Name *").pack(anchor="w", padx=60)
    ctk.CTkEntry(details_win, textvariable=name_var, width=300).pack(pady=5, padx=60)

    ctk.CTkLabel(details_win, text="Phone *").pack(anchor="w", padx=60, pady=(10,0))
    ctk.CTkEntry(details_win, textvariable=phone_var, width=300).pack(pady=5, padx=60)

    ctk.CTkLabel(details_win, text="Address (Optional)").pack(anchor="w", padx=60, pady=(10,0))
    addr_box = ctk.CTkTextbox(details_win, width=300, height=80)
    addr_box.pack(pady=5, padx=60)

    def generate_bill():
        name = name_var.get().strip()
        phone = phone_var.get().strip()
        address = addr_box.get("1.0", "end").strip()

        if not name or not phone:
            messagebox.showerror("Error", "Name and Phone required!")
            return

        # Calculate
        items = []
        total = 0
        for sid, qty in cart.items():
            s = get_sweet_by_id(sid)
            if s:
                _, n, p, _, _ = s
                sub = p * qty
                total += sub
                items.append((n, qty, p, sub))

        # Save to DB
        cur = conn.cursor()
        now = datetime.now()
        cur.execute("INSERT INTO orders (created_at, total) VALUES (?, ?)", 
                    (now.strftime("%Y-%m-%d %H:%M:%S"), total))
        order_id = cur.lastrowid
        cur.executemany("INSERT INTO order_items (order_id, sweet_name, qty, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)",
                        [(order_id, n, q, p, s) for n, q, p, s in items])
        conn.commit()

                # Generate PDF
        pdf_path = os.path.join(RECEIPTS_DIR, f"Bill_{order_id}_{now.strftime('%Y%m%d_%H%M')}.pdf")
        generate_professional_receipt(order_id, items, total, name, phone, address, pdf_path)

        # THIS LINE OPENS THE BILL AUTOMATICALLY!
        open_pdf(pdf_path)

        messagebox.showinfo("Success! Bill Ready!",
                            f"Bill generated and opened!\n\n"
                            f"Customer: {name}\n"
                            f"Total: ₹{total:.2f}\n\n"
                            f"Location: {pdf_path}")
        cart.clear()
        update_cart_button()
        details_win.destroy()
        status_label.configure(text=f"Thank you {name}!")

    btn_frame = ctk.CTkFrame(details_win)
    btn_frame.pack(pady=20)
    ctk.CTkButton(btn_frame, text="Generate Bill", fg_color="green", width=200, height=40, command=generate_bill).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text="Cancel", command=details_win.destroy).pack(side="left", padx=10)

# ---------------------------
# Bindings & Start
# ---------------------------
def on_search(*args):
    refresh_products()

search_var.trace("w", on_search)
category_var.trace("w", lambda *a: refresh_products())

view_cart_btn.configure(command=open_cart_window)
checkout_btn.configure(command=checkout)  # Direct checkout

refresh_products()
update_cart_button()

app.mainloop()
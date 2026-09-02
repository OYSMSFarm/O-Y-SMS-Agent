import serial
import serial.tools.list_ports
import requests
import time
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading
import sqlite3
import hashlib
import os
from contextlib import contextmanager
from PIL import Image, ImageTk

# --- CONFIGURATION ---
MASTER_URL = "http://192.168.0.132:8000"
SUPPORT_EMAIL = "mailto:erosnowly@gmail.com?subject=Y%26O%20SMS%20Farm%20Support%20Request"
DB_NAME = "yo_sms_farm.db"
SPLASH_DURATION = 3000
LOGO_PATH = "logo.png"

# --- COLORS ---
PRIMARY_COLOR = "#2E86AB"
SUCCESS_COLOR = "#06A77D"
DANGER_COLOR = "#D62828"
BG_COLOR = "#F5F5F5"
DARK_BG = "#1A1A2E"
TEXT_COLOR = "#FFFFFF"
WARNING_COLOR = "#F39C12"
ORANGE_COLOR = "#FF8C00"

# --- TERMS & CONDITIONS ---
TOS_TEXT = """
Y&O SMS FARM - AGENT AGREEMENT

1. ACCOUNT USAGE
   - You must use your own real, registered SIM cards.
   - Using VoIP or unregistered SIMs is strictly prohibited.

2. SIM CARD FRAUD RULE (STRICT)
   - Each SIM must be used ONLY for this network.
   - If used on other platforms >50%, it will be AUTO-BANNED.

3. PAYMENT & COMMISSION
   - You earn 70% of revenue per SMS.
   - Minimum Payout: $1.00.
   - Payouts processed within 48 hours.

4. SIM CARD DURATION
   - Keep SIMs online 24-30 days maximum.

5. SUPPORT & ACCESS
   - Contact support via email for password reset.

6. TERMINATION
   - Admin reserves right to ban accounts violating terms.

By clicking "I AGREE", you accept these terms.
"""

# --- GLOBAL STATE ---
current_user = None
user_balance = 0.00
user_sms_count = 0
sim_threads = {}
dashboard_window = None
logo_image = None

# --- DATABASE ---
@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                password_hash TEXT,
                is_banned INTEGER DEFAULT 0,
                tos_accepted INTEGER DEFAULT 0
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS sim_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                phone TEXT UNIQUE,
                country TEXT,
                carrier TEXT,
                description TEXT,
                serial_port TEXT,
                is_online INTEGER DEFAULT 0,
                started_at TEXT,
                duration_hours INTEGER DEFAULT 24,
                total_sms INTEGER DEFAULT 0,
                total_profit REAL DEFAULT 0.0,
                is_banned INTEGER DEFAULT 0,
                FOREIGN KEY(email) REFERENCES users(email)
            )
        ''')
        conn.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_user_exists(email):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM users WHERE email=?", (email,))
        return c.fetchone() is not None

def verify_password(email, password):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT password_hash, is_banned FROM users WHERE email=?", (email,))
        row = c.fetchone()
        if row:
            stored_hash = row['password_hash']
            is_banned = row['is_banned']
            if is_banned == 1:
                return None, "banned"
            if hash_password(password) == stored_hash:
                return email, "success"
    return None, "invalid"

def get_user_balance(email):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(total_profit) as balance FROM sim_cards WHERE email=?", (email,))
        row = c.fetchone()
        return row['balance'] if row and row['balance'] else 0.0

def get_user_sms_count(email):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(total_sms) as count FROM sim_cards WHERE email=?", (email,))
        row = c.fetchone()
        return row['count'] if row and row['count'] else 0

def get_available_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def simulate_sms_send(serial_port, phone_number):
    return True, "SMS sent successfully (simulated)"

def update_sim_status(sim_id, status, sms_count=0, profit=0.0):
    with get_db_connection() as conn:
        c = conn.cursor()
        if status == "online":
            c.execute("UPDATE sim_cards SET is_online = 1, started_at = ? WHERE id = ?", (datetime.now().isoformat(), sim_id))
        elif status == "offline":
            c.execute("UPDATE sim_cards SET is_online = 0, total_sms = ?, total_profit = ? WHERE id = ?", (sms_count, profit, sim_id))
        conn.commit()

def send_sim_thread(sim_id, serial_port, phone, duration_hours):
    global user_balance, user_sms_count
    try:
        update_sim_status(sim_id, "online")
        start_time = time.time()
        duration_seconds = duration_hours * 3600
        sms_sent = 0
        total_profit = 0.0
        
        while time.time() - start_time < duration_seconds:
            time.sleep(30 + (sim_id % 90))
            success, msg = simulate_sms_send(serial_port, phone)
            if success:
                sms_sent += 1
                profit_per_sms = 0.007
                total_profit += profit_per_sms
                with get_db_connection() as conn:
                    c = conn.cursor()
                    c.execute("UPDATE sim_cards SET total_sms = total_sms + 1, total_profit = total_profit + ? WHERE id = ?", (profit_per_sms, sim_id))
                    conn.commit()
                user_sms_count += 1
                user_balance += profit_per_sms
                if dashboard_window and dashboard_window.winfo_exists():
                    dashboard_window.after(0, update_dashboard_ui)
        update_sim_status(sim_id, "offline", sms_sent, total_profit)
    except Exception as e:
        print(f"Error in SIM thread {sim_id}: {e}")
        update_sim_status(sim_id, "offline")
    finally:
        if sim_id in sim_threads:
            del sim_threads[sim_id]

def load_logo(size=(100, 100)):
    global logo_image
    if not os.path.exists(LOGO_PATH):
        return None
    try:
        img = Image.open(LOGO_PATH)
        img = img.resize(size, Image.LANCZOS)
        logo_image = ImageTk.PhotoImage(img)
        return logo_image
    except Exception as e:
        print(f"Error loading logo: {e}")
        return None

def show_splash_screen(root_window):
    root_window.withdraw()
    splash = tk.Toplevel(root_window)
    splash.title("Y&O SMS")
    splash.geometry("400x450")
    splash.config(bg=BG_COLOR)
    splash.resizable(False, False)
    
    x = (splash.winfo_screenwidth() // 2) - 200
    y = (splash.winfo_screenheight() // 2) - 225
    splash.geometry(f"400x450+{x}+{y}")
    
    logo = load_logo(size=(150, 150))
    if logo:
        tk.Label(splash, image=logo, bg=BG_COLOR).pack(pady=20)
    else:
        tk.Label(splash, text="Y&O", font=("Arial", 40, "bold"), fg=PRIMARY_COLOR, bg=BG_COLOR).pack(pady=20)
    
    tk.Label(splash, text="NETWORK CODE", font=("Arial", 14, "bold"), fg=ORANGE_COLOR, bg=BG_COLOR).pack(pady=5)
    tk.Label(splash, text="Secure SMS Network", font=("Arial", 12), fg="#666", bg=BG_COLOR).pack(pady=10)
  
    progress = ttk.Progressbar(splash, length=300, mode='determinate', maximum=100)
    progress.pack(pady=30)
    
    def animate():
        for i in range(101):
            if not splash.winfo_exists(): break
            progress['value'] = i
            splash.update()
            time.sleep(SPLASH_DURATION / 100 / 1000)
    
    threading.Thread(target=animate, daemon=True).start()
    splash.after(SPLASH_DURATION, lambda: (splash.destroy(), root_window.deiconify(), check_first_launch()))

def check_first_launch():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            show_tos_screen()
        else:
            show_login()

def show_tos_screen():
    root.withdraw()
    tos_win = tk.Toplevel(root)
    tos_win.title("Terms & Conditions")
    tos_win.geometry("700x600")
    tos_win.transient(root)
    tos_win.grab_set()
    
    tk.Label(tos_win, text="IMPORTANT AGREEMENT", font=("Arial", 16, "bold"), fg=DANGER_COLOR, bg=DARK_BG).pack(fill="x", pady=10)
    
    text_frame = tk.Frame(tos_win)
    text_frame.pack(fill="both", expand=True, padx=20, pady=10)
    scrollbar = tk.Scrollbar(text_frame)
    scrollbar.pack(side="right", fill="y")
    
    tos_text = tk.Text(text_frame, wrap="word", yscrollcommand=scrollbar.set, font=("Arial", 9), bg="#F0F0F0")
    tos_text.pack(fill="both", expand=True)
    scrollbar.config(command=tos_text.yview)
    tos_text.insert("1.0", TOS_TEXT)
    tos_text.config(state="disabled")

    def agree():
        tos_win.destroy()
        show_registration()

    def decline():
        messagebox.showinfo("Info", "You must agree to continue.")
        root.destroy()

    btn_frame = tk.Frame(tos_win, bg=DARK_BG)
    btn_frame.pack(pady=20, fill="x")
    tk.Button(btn_frame, text="I AGREE", bg=SUCCESS_COLOR, fg=TEXT_COLOR, font=("Arial", 12, "bold"), command=agree, padx=20, pady=10).pack(side="left", padx=20)
    tk.Button(btn_frame, text="DECLINE", bg=DANGER_COLOR, fg=TEXT_COLOR, font=("Arial", 12, "bold"), command=decline, padx=20, pady=10).pack(side="left", padx=20)

def show_registration():
    root.withdraw()
    reg_win = tk.Toplevel(root)
    reg_win.title("Create Account - Y&O SMS")
    reg_win.geometry("450x450")
    reg_win.config(bg=BG_COLOR)
    
    tk.Label(reg_win, text="Y&O SMS", font=("Arial", 28, "bold"), fg=PRIMARY_COLOR, bg=BG_COLOR).pack(pady=10)
    tk.Label(reg_win, text="NETWORK CODE", font=("Arial", 14, "bold"), fg=ORANGE_COLOR, bg=BG_COLOR).pack()
    tk.Label(reg_win, text="Create Account", font=("Arial", 12), fg="#666", bg=BG_COLOR).pack()
    
    form = tk.Frame(reg_win, bg="white")
    form.pack(padx=30, pady=20, fill="both", expand=True)
    
    tk.Label(form, text="Email:", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(10, 5))
    email = tk.Entry(form, font=("Arial", 11), relief="flat")
    email.pack(pady=5, ipady=8, fill="x")
    
    tk.Label(form, text="Password:", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(10, 5))
    pwd = tk.Entry(form, show="*", font=("Arial", 11), relief="flat")
    pwd.pack(pady=5, ipady=8, fill="x")
    
    tk.Label(form, text="Confirm:", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(10, 5))
    confirm = tk.Entry(form, show="*", font=("Arial", 11), relief="flat")
    confirm.pack(pady=5, ipady=8, fill="x")

    def register():
        e = email.get().strip().lower()
        p = pwd.get()
        c = confirm.get()
        if not e or not p:
            messagebox.showerror("Error", "All fields required.")
            return
        if p != c:
            messagebox.showerror("Error", "Passwords don't match.")
            return
        if check_user_exists(e):
            messagebox.showinfo("Info", "Email exists. Please login.")
            reg_win.destroy()
            show_login()
            return
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (email, password_hash, tos_accepted) VALUES (?, ?, 1)", (e, hash_password(p)))
            conn.commit()
        
        messagebox.showinfo("Success", f"Account created!\nEmail: {e}\nPlease Login.")
        reg_win.destroy()
        show_login()

    tk.Button(form, text="Register", bg=PRIMARY_COLOR, fg=TEXT_COLOR, font=("Arial", 12, "bold"), command=register, padx=20, pady=10).pack(pady=10)

def show_login():
        root.withdraw()
    login_win = tk.Toplevel(root)
    login_win.title("Login - Y&O SMS")
    login_win.geometry("400x350")
    login_win.config(bg=BG_COLOR)
    login_win.transient(root)
    login_win.grab_set()
    
    logo = load_logo(size=(80, 80))
    if logo:
        tk.Label(login_win, image=logo, bg=BG_COLOR).pack(pady=10)
    
    tk.Label(login_win, text="Y&O SMS", font=("Arial", 24, "bold"), fg=PRIMARY_COLOR, bg=BG_COLOR).pack()
    tk.Label(login_win, text="NETWORK CODE", font=("Arial", 12, "bold"), fg=ORANGE_COLOR, bg=BG_COLOR).pack()
    tk.Label(login_win, text="Login to Your Account", font=("Arial", 12), fg="#666", bg=BG_COLOR).pack()
    
    form = tk.Frame(login_win, bg="white")
    form.pack(padx=30, pady=20, fill="both", expand=True)
    
    tk.Label(form, text="Email:", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(10, 5))
    email = tk.Entry(form, font=("Arial", 11), relief="flat")
    email.pack(pady=5, ipady=8, fill="x")
    
    tk.Label(form, text="Password:", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(10, 5))
    pwd = tk.Entry(form, show="*", font=("Arial", 11), relief="flat")
    pwd.pack(pady=5, ipady=8, fill="x")

    def login():
        e = email.get().strip().lower()
        p = pwd.get()
        user, status = verify_password(e, p)
        
        if status == "banned":
            messagebox.showerror("Error", "Account banned. Contact support.")
            return
        elif status == "invalid":
            messagebox.showerror("Error", "Invalid credentials.")
            return
        
        global current_user, user_balance, user_sms_count
        current_user = user
        user_balance = get_user_balance(user)
        user_sms_count = get_user_sms_count(user)
        
        messagebox.showinfo("Success", f"Welcome {user}!\nBalance: ${user_balance:.2f}")
        login_win.destroy()
        show_dashboard()

    tk.Button(form, text="Login", bg=PRIMARY_COLOR, fg=TEXT_COLOR, font=("Arial", 12, "bold"), command=login, padx=20, pady=10).pack(pady=10)
    tk.Button(form, text="Cancel", bg=DARK_BG, fg=TEXT_COLOR, command=lambda: (login_win.destroy(), root.deiconify()), padx=20, pady=10).pack(pady=5)

def update_dashboard_ui():
    global user_balance, user_sms_count
    
    if current_user:
        user_balance = get_user_balance(current_user)
        user_sms_count = get_user_sms_count(current_user)

    if not dashboard_window or not dashboard_window.winfo_exists():
        return

    stats_labels[0].config(text=f"Balance: ${user_balance:.2f}")
    stats_labels[1].config(text=f"Total SMS: {user_sms_count}")

    for item in tree.get_children():
        tree.delete(item)
    
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, phone, country, carrier, 
                   CASE WHEN is_online = 1 THEN 'Online' ELSE 'Offline' END as status,
                   total_sms, total_profit, started_at
            FROM sim_cards 
            WHERE email=?
            ORDER BY is_online DESC, id DESC
        """, (current_user,))
        
        for row in c.fetchall():
            profit_str = f"${row['total_profit']:.2f}"
            tree.insert("", "end", values=(
                row['id'], row['phone'], row['country'], 
                row['status'], row['total_sms'], profit_str
            ))

def show_dashboard():
    global dashboard_window, dashboard_stats, stats_labels, tree
    
    dashboard_window = tk.Toplevel(root)
    dashboard_window.title(f"Y&O SMS - {current_user}")
    dashboard_window.geometry("900x600")
    dashboard_window.config(bg=BG_COLOR)
    
    header_frame = tk.Frame(dashboard_window, bg=BG_COLOR, height=100)
    header_frame.pack(fill="x")
    header_frame.pack_propagate(False)
    
    header_logo = load_logo(size=(50, 50))
    if header_logo:
        lbl_logo = tk.Label(header_frame, image=header_logo, bg=BG_COLOR)
        lbl_logo.image = header_logo
        lbl_logo.pack(side="left", padx=20, pady=15)
    
    tk.Label(header_frame, text="Y&O SMS", font=("Arial", 24, "bold"), fg=PRIMARY_COLOR, bg=BG_COLOR).pack(side="left", pady=15)
    tk.Label(header_frame, text="NETWORK CODE", font=("Arial", 14, "bold"), fg=ORANGE_COLOR, bg=BG_COLOR).pack(side="left", padx=10, pady=15)
    
    dashboard_stats = tk.Frame(dashboard_window, bg=BG_COLOR, pady=15)
    dashboard_stats.pack(fill="x", padx=20)
    
    stats_labels = []
    
    lbl_balance = tk.Label(dashboard_stats, text=f"Balance: ${user_balance:.2f}", font=("Arial", 14, "bold"), fg=SUCCESS_COLOR, bg=BG_COLOR)
    lbl_balance.pack(side="left", padx=20)
    stats_labels.append(lbl_balance)
    
    lbl_sms = tk.Label(dashboard_stats, text=f"Total SMS: {user_sms_count}", font=("Arial", 14, "bold"), fg=PRIMARY_COLOR, bg=BG_COLOR)
    lbl_sms.pack(side="left", padx=20)
    stats_labels.append(lbl_sms)
    
    table_frame = tk.LabelFrame(dashboard_window, text="My SIM Cards", font=("Arial", 12, "bold"), bg=BG_COLOR, padx=15, pady=15)
    table_frame.pack(padx=20, pady=10, fill="both", expand=True)
    
    cols = ("ID", "Phone Number", "Country", "Status", "SMS Count", "Profit")
    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=12)
    
    tree.heading("ID", text="ID"); tree.column("ID", width=50, anchor="center")
    tree.heading("Phone Number", text="Phone Number"); tree.column("Phone Number", width=150, anchor="center")
    tree.heading("Country", text="Country"); tree.column("Country", width=100, anchor="center")
    tree.heading("Status", text="Status"); tree.column("Status", width=100, anchor="center")
    tree.heading("SMS Count", text="SMS Count"); tree.column("SMS Count", width=100, anchor="center")
    tree.heading("Profit", text="Profit"); tree.column("Profit", width=100, anchor="center")
    
    tree.pack(fill="both", expand=True)
    
    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scrollbar.set)
    
    btn_frame = tk.Frame(dashboard_window, bg=BG_COLOR, pady=15)
    btn_frame.pack(fill="x", padx=20)
    
    def add_sim_action():
        add_win = tk.Toplevel(dashboard_window)
        add_win.title("Add New SIM - Y&O SMS")
        add_win.geometry("400x350")
        add_win.config(bg=BG_COLOR)
        add_win.transient(dashboard_window)
        add_win.grab_set()
        
        tk.Label(add_win, text="Add SIM Card Details", font=("Arial", 16, "bold"), bg=BG_COLOR, fg=PRIMARY_COLOR).pack(pady=15)
        
        form = tk.Frame(add_win, bg="white", padx=20, pady=20)
        form.pack(fill="both", expand=True)
        
        tk.Label(form, text="Phone Number:", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(0, 5))
        entry_phone = tk.Entry(form, font=("Arial", 11))
        entry_phone.pack(fill="x", pady=5)
        
        tk.Label(form, text="Country:", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(15, 5))
        entry_country = tk.Entry(form, font=("Arial", 11))
        entry_country.pack(fill="x", pady=5)
        
        tk.Label(form, text="Carrier:", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(15, 5))
        entry_carrier = tk.Entry(form, font=("Arial", 11))
        entry_carrier.pack(fill="x", pady=5)
        
        tk.Label(form, text="Serial Port:", font=("Arial
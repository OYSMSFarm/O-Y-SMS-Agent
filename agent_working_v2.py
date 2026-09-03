import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import hashlib
import threading
import time
import webbrowser

# CONFIG
MASTER_URL = "http://192.168.0.110:8000"
SUPPORT_EMAIL = "mailto:erosnowly@gmail.com?subject=O&Y%20SMS%20Support"
DB_NAME = "agent_data.db"
APP_NAME = "O&Y SMS"

# COLORS
PRIMARY = "#2E86AB"
SUCCESS = "#06A77D"
DANGER = "#D62828"
BG = "#F5F5F5"

# DATABASE
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        password_hash TEXT,
        is_banned TEXT DEFAULT 'false'
    )''')
    conn.commit()
    conn.close()

def hash_pwd(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

current_user = None

# SPLASH
def splash(root):
    root.withdraw()
    splash_win = tk.Toplevel(root)
    splash_win.geometry("400x400")
    splash_win.config(bg=PRIMARY)
    splash_win.resizable(False, False)
    x = (splash_win.winfo_screenwidth() // 2) - 200
    y = (splash_win.winfo_screenheight() // 2) - 200
    splash_win.geometry(f"400x400+{x}+{y}")
    tk.Label(splash_win, text=APP_NAME, font=("Arial", 28, "bold"), fg="white", bg=PRIMARY).pack(pady=50)
    tk.Label(splash_win, text="Secure SMS Network", font=("Arial", 12), fg="#DDD", bg=PRIMARY).pack()
    progress = ttk.Progressbar(splash_win, length=300, mode='determinate', maximum=100)
    progress.pack(pady=30)
    def animate():
        for i in range(101):
            progress['value'] = i
            splash_win.update()
            time.sleep(0.02)
    threading.Thread(target=animate, daemon=True).start()
    def close_splash():
        splash_win.destroy()
        root.deiconify()
        check_users()
    splash_win.after(3000, close_splash)

def check_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    if count == 0:
        show_tos()
    else:
        show_login()

# TERMS
def show_tos():
    root.withdraw()
    tos_win = tk.Toplevel(root)
    tos_win.title("Terms & Conditions")
    tos_win.geometry("600x500")
    tos_win.resizable(False, False)
    tk.Label(tos_win, text="IMPORTANT AGREEMENT", font=("Arial", 14, "bold"), fg=DANGER, bg="white").pack(fill="x", pady=10)
    text_frame = tk.Frame(tos_win)
    text_frame.pack(fill="both", expand=True, padx=10, pady=10)
    scrollbar = tk.Scrollbar(text_frame)
    scrollbar.pack(side="right", fill="y")
    text_widget = tk.Text(text_frame, wrap="word", yscrollcommand=scrollbar.set, font=("Arial", 9))
    text_widget.pack(fill="both", expand=True)
    scrollbar.config(command=text_widget.yview)
    tos_content = """O&Y SMS - AGENT AGREEMENT

1. ACCOUNT USAGE
   - Use only real, registered SIM cards
   - No VoIP or unregistered SIMs

2. SIM FRAUD RULE (STRICT)
   - Each SIM used ONLY for this network
   - >50% use on other platforms = AUTO-BAN

3. PAYMENT & COMMISSION
   - You earn 70% of revenue per SMS
   - Minimum payout: $1.00
   - Payouts within 48 hours

4. SIM DURATION
   - Keep online 24-30 days max

5. SUPPORT
   - Contact via email for password reset

6. TERMINATION
   - Admin can ban accounts anytime

By clicking AGREE, you accept these terms."""
    text_widget.insert("1.0", tos_content)
    text_widget.config(state="disabled")
    btn_frame = tk.Frame(tos_win)
    btn_frame.pack(pady=15)
    def agree():
        tos_win.destroy()
        show_register()
    def decline():
        messagebox.showinfo("Info", "You must agree to continue")
        root.destroy()
    tk.Button(btn_frame, text="I AGREE", bg=SUCCESS, fg="white", font=("Arial", 11, "bold"), command=agree, padx=20, pady=8).pack(side="left", padx=10)
    tk.Button(btn_frame, text="DECLINE", bg=DANGER, fg="white", font=("Arial", 11, "bold"), command=decline, padx=20, pady=8).pack(side="left", padx=10)

# REGISTER
def show_register():
    root.withdraw()
    reg_win = tk.Toplevel(root)
    reg_win.title("Create Account")
    reg_win.geometry("400x300")
    reg_win.config(bg=BG)
    tk.Label(reg_win, text=APP_NAME, font=("Arial", 20, "bold"), fg=PRIMARY, bg=BG).pack(pady=20)
    form = tk.Frame(reg_win, bg="white")
    form.pack(padx=30, pady=20, fill="both", expand=True)
    tk.Label(form, text="Email:", font=("Arial", 10, "bold"), bg="white").pack(anchor="w", pady=(10, 3))
    email_entry = tk.Entry(form, width=30, font=("Arial", 10))
    email_entry.pack(pady=5, ipady=6, fill="x")
    tk.Label(form, text="Password:", font=("Arial", 10, "bold"), bg="white").pack(anchor="w", pady=(10, 3))
    pass_entry = tk.Entry(form, width=30, font=("Arial", 10), show="*")
    pass_entry.pack(pady=5, ipady=6, fill="x")
    tk.Label(form, text="Confirm Password:", font=("Arial", 10, "bold"), bg="white").pack(anchor="w", pady=(10, 3))
    confirm_entry = tk.Entry(form, width=30, font=("Arial", 10), show="*")
    confirm_entry.pack(pady=5, ipady=6, fill="x")
    def register():
        email = email_entry.get().strip().lower()
        pwd = pass_entry.get()
        confirm = confirm_entry.get()
        if not email or not pwd:
            messagebox.showerror("Error", "All fields required")
            return
        if pwd != confirm:
            messagebox.showerror("Error", "Passwords don't match")
            return
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=?", (email,))
        if c.fetchone():
            messagebox.showinfo("Info", "Email exists. Login instead.")
            conn.close()
            reg_win.destroy()
            show_login()
            return
        pwd_hash = hash_pwd(pwd)
        c.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, pwd_hash))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", f"Account created!\n\nEmail: {email}\n\nPlease login.")
        reg_win.destroy()
        show_login()
    tk.Button(form, text="Register", bg=PRIMARY, fg="white", font=("Arial", 11, "bold"), command=register, padx=20, pady=8).pack(pady=20, fill="x")

# LOGIN
def show_login():
    root.withdraw()
    login_win = tk.Toplevel(root)
    login_win.title("Login")
    login_win.geometry("400x280")
    login_win.config(bg=BG)
    tk.Label(login_win, text=APP_NAME, font=("Arial", 20, "bold"), fg=PRIMARY, bg=BG).pack(pady=20)
    form = tk.Frame(login_win, bg="white")
    form.pack(padx=30, pady=20, fill="both", expand=True)
    tk.Label(form, text="Email:", font=("Arial", 10, "bold"), bg="white").pack(anchor="w", pady=(10, 3))
    email_entry = tk.Entry(form, width=30, font=("Arial", 10))
    email_entry.pack(pady=5, ipady=6, fill="x")
    tk.Label(form, text="Password:", font=("Arial", 10, "bold"), bg="white").pack(anchor="w", pady=(10, 3))
    pass_entry = tk.Entry(form, width=30, font=("Arial", 10), show="*")
    pass_entry.pack(pady=5, ipady=6, fill="x")
    def login():
        global current_user
        email = email_entry.get().strip().lower()
        pwd = pass_entry.get()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT password_hash, is_banned FROM users WHERE email=?", (email,))
        user = c.fetchone()
        conn.close()
        if not user:
            messagebox.showerror("Error", "User not found")
            return
        pwd_hash, is_banned = user
        if is_banned == 'true':
            messagebox.showerror("Error", "Account banned")
            return
        if pwd_hash == hash_pwd(pwd):
            current_user = email
            login_win.destroy()
            show_dashboard()
        else:
            messagebox.showerror("Error", "Wrong password")
    tk.Button(form, text="Login", bg=PRIMARY, fg="white", font=("Arial", 11, "bold"), command=login, padx=20, pady=8).pack(pady=10, fill="x")
    tk.Button(form, text="Forgot Password?", bg="gray", fg="white", font=("Arial", 9), command=lambda: webbrowser.open(SUPPORT_EMAIL), padx=20, pady=6).pack(fill="x")

# DASHBOARD
def show_dashboard():
    root.deiconify()
    root.config(bg=BG)
    for widget in root.winfo_children():
        widget.destroy()
    header = tk.Frame(root, bg=PRIMARY)
    header.pack(fill="x")
    tk.Label(header, text=APP_NAME, font=("Arial", 18, "bold"), fg="white", bg=PRIMARY).pack(side="left", padx=20, pady=15)
    tk.Label(header, text=f"Welcome, {current_user}", font=("Arial", 11), fg="white", bg=PRIMARY).pack(side="right", padx=20, pady=15)
    main = tk.Frame(root, bg=BG)
    main.pack(fill="both", expand=True, padx=20, pady=20)
    tk.Label(main, text="Dashboard", font=("Arial", 16, "bold"), fg=PRIMARY, bg=BG).pack(anchor="w", pady=10)
    info_frame = tk.Frame(main, bg="white", relief="solid", bd=1)
    info_frame.pack(fill="both", expand=True, pady=10)
    tk.Label(info_frame, text="Your Balance: $0.00", font=("Arial", 14, "bold"), fg=SUCCESS, bg="white").pack(pady=20)
    tk.Label(info_frame, text="Total SMS: 0", font=("Arial", 12), bg="white").pack(pady=10)
    btn_frame = tk.Frame(main, bg=BG)
    btn_frame.pack(pady=20)
    tk.Button(btn_frame, text="Request Payout", bg=SUCCESS, fg="white", font=("Arial", 11, "bold"), padx=20, pady=10).pack(side="left", padx=10)
    tk.Button(btn_frame, text="Contact Support", bg="orange", fg="white", font=("Arial", 11, "bold"), command=lambda: webbrowser.open(SUPPORT_EMAIL), padx=20, pady=10).pack(side="left", padx=10)

# MAIN
root = tk.Tk()
root.title(APP_NAME)
root.geometry("600x500")
init_db()
splash(root)
root.mainloop()
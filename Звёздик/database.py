import sqlite3
from config import REWARD_PER_TASK

conn = sqlite3.connect("bot_database.db", check_same_thread=False)
cursor = conn.cursor()

def init_db():
    # Пользователи
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance REAL DEFAULT 0.0
    )
    """)

    # Рекламные кампании
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        advertiser_id INTEGER,
        channel_username TEXT,
        channel_title TEXT,
        subscribers_bought INTEGER,
        subscribers_done INTEGER DEFAULT 0,
        price_per_sub REAL DEFAULT 1.0,
        status TEXT DEFAULT 'pending_payment',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Выполненные задания (защита от повторов)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS completed_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        ad_id INTEGER,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, ad_id)
    )
    """)

    # Заявки на вывод
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        amount REAL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()


# ---------- USERS ----------
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def add_user(user_id, username):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
        (user_id, username)
    )
    conn.commit()

def add_balance(user_id, amount):
    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (amount, user_id)
    )
    conn.commit()

def deduct_balance(user_id, amount):
    cursor.execute(
        "UPDATE users SET balance = balance - ? WHERE user_id = ?",
        (amount, user_id)
    )
    conn.commit()


# ---------- ADS ----------
def create_ad(advertiser_id, channel_username, channel_title, amount, price):
    cursor.execute(
        """INSERT INTO ads 
        (advertiser_id, channel_username, channel_title, subscribers_bought, price_per_sub)
        VALUES (?, ?, ?, ?, ?)""",
        (advertiser_id, channel_username, channel_title, amount, price)
    )
    conn.commit()
    return cursor.lastrowid

def get_active_ads():
    cursor.execute(
        """SELECT id, channel_username, channel_title 
        FROM ads 
        WHERE status = 'active' AND subscribers_done < subscribers_bought"""
    )
    return cursor.fetchall()

def get_ad(ad_id):
    cursor.execute("SELECT * FROM ads WHERE id = ?", (ad_id,))
    return cursor.fetchone()

def increment_ad_done(ad_id):
    cursor.execute(
        "UPDATE ads SET subscribers_done = subscribers_done + 1 WHERE id = ?",
        (ad_id,)
    )
    conn.commit()
    cursor.execute(
        "SELECT subscribers_bought, subscribers_done FROM ads WHERE id = ?",
        (ad_id,)
    )
    bought, done = cursor.fetchone()
    if done >= bought:
        cursor.execute("UPDATE ads SET status = 'completed' WHERE id = ?", (ad_id,))
        conn.commit()

def confirm_ad_payment(ad_id):
    cursor.execute("UPDATE ads SET status = 'active' WHERE id = ?", (ad_id,))
    conn.commit()

def reject_ad(ad_id):
    cursor.execute("UPDATE ads SET status = 'rejected' WHERE id = ?", (ad_id,))
    conn.commit()

def get_user_ads(advertiser_id):
    cursor.execute(
        """SELECT id, channel_title, subscribers_bought, subscribers_done, status 
        FROM ads WHERE advertiser_id = ? ORDER BY id DESC""",
        (advertiser_id,)
    )
    return cursor.fetchall()


# ---------- COMPLETED TASKS ----------
def is_task_completed(user_id, ad_id):
    cursor.execute(
        "SELECT 1 FROM completed_tasks WHERE user_id = ? AND ad_id = ?",
        (user_id, ad_id)
    )
    return cursor.fetchone() is not None

def mark_task_completed(user_id, ad_id):
    cursor.execute(
        "INSERT OR IGNORE INTO completed_tasks (user_id, ad_id) VALUES (?, ?)",
        (user_id, ad_id)
    )
    conn.commit()


# ---------- WITHDRAWALS ----------
def create_withdrawal(user_id, username, amount):
    cursor.execute(
        "INSERT INTO withdrawals (user_id, username, amount) VALUES (?, ?, ?)",
        (user_id, username, amount)
    )
    conn.commit()
    return cursor.lastrowid

def get_withdrawal(wid):
    cursor.execute("SELECT * FROM withdrawals WHERE id = ?", (wid,))
    return cursor.fetchone()

def set_withdrawal_status(wid, status):
    cursor.execute("UPDATE withdrawals SET status = ? WHERE id = ?", (status, wid))
    conn.commit()
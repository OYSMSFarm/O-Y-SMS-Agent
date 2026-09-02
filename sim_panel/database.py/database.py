import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('sms_agent.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS sims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imei TEXT UNIQUE,
            imsi TEXT,
            iccid TEXT,
            phone_number TEXT,
            provider TEXT,
            port TEXT,
            status TEXT DEFAULT 'unknown',
            signal_strength INTEGER,
            registered_network TEXT,
            last_seen_at TIMESTAMP,
            balance REAL,
            balance_currency TEXT DEFAULT 'ETB',
            balance_checked_at TIMESTAMP,
            ussd_balance_code TEXT,
            enabled INTEGER DEFAULT 1,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_all_sims():
    conn = sqlite3.connect('sms_agent.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM sims ORDER BY id')
    sims = c.fetchall()
    conn.close()
    return sims

def add_sim(imei, phone_number, provider, port, ussd_code='*100#'):
    conn = sqlite3.connect('sms_agent.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO sims (imei, phone_number, provider, port, ussd_balance_code, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (imei, phone_number, provider, port, ussd_code, datetime.now()))
    conn.commit()
    conn.close()

def update_sim_status(sim_id, status, signal=None, network=None):
    conn = sqlite3.connect('sms_agent.db')
    c = conn.cursor()
    c.execute('''
        UPDATE sims 
        SET status = ?, signal_strength = ?, registered_network = ?, last_seen_at = ?
        WHERE id = ?
    ''', (status, signal, network, datetime.now(), sim_id))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized!")
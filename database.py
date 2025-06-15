import sqlite3

DB_PATH = 'bot.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_warning(user_id: int, moderator_id: int, reason: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO warnings (user_id, moderator_id, reason) VALUES (?, ?, ?)',
              (user_id, moderator_id, reason))
    conn.commit()
    conn.close()

def get_warnings(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM warnings WHERE user_id = ?', (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count
import sqlite3
from werkzeug.security import generate_password_hash

def setup_database():
    conn = sqlite3.connect('prek_billing.db')
    c = conn.cursor()

    # Insert a test user
    username = 'test'
    password = generate_password_hash('password123')
    c.execute("INSERT OR REPLACE INTO users (username, password) VALUES (?, ?)", (username, password))

    conn.commit()
    conn.close()

    print("test  user created successfully.")

if __name__ == '__main__':
    setup_database()

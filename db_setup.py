import sqlite3

def setup_database():
    conn = sqlite3.connect('prek_billing.db')
    c = conn.cursor()

    #create students table
    c.execute('''ALTER TABLE Parents
                ADD COLUMN Email VARCHAR(100) NOT NULL''')
    
    
    conn.commit()
    conn.close()

    print("Parents updated.")

if __name__ == '__main__':
    setup_database()
    
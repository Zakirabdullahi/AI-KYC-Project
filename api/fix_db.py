import sqlite3
import os

db_path = os.path.join('database', 'bank.db')
print(f"Connecting to {db_path}...")
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("UPDATE users SET verification_status='unverified' WHERE verification_status='pending';")
print(f"Updated {c.rowcount} users.")
conn.commit()
conn.close()
print('Finished updating status!')

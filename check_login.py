"""Script to diagnose and fix the login issue"""
import pymysql
from werkzeug.security import check_password_hash, generate_password_hash

conn = pymysql.connect(
    host='localhost', port=3306, user='root', password='',
    database='ai_blind_guide', charset='utf8mb4'
)
cur = conn.cursor()
cur.execute('SELECT email, password_hash, LENGTH(password_hash) as len FROM users')
rows = cur.fetchall()
for r in rows:
    h = r[1]
    print(f"Email: {r[0]}, hash_len={r[2]}")
    # Try common passwords
    for pw in ['Demo@123', 'demo@123', 'Admin@123', 'Test@1234']:
        result = check_password_hash(h, pw)
        if result:
            print(f"  >>> PASSWORD MATCH: '{pw}'")
        else:
            print(f"  no match for '{pw}'")

print("\n--- Generating new hashes for testing ---")
new_hash = generate_password_hash('NewPass@123')
print(f"new hash length: {len(new_hash)}")
print(f"full hash: {new_hash}")

print("\n--- Resetting demo account password to Demo@123 ---")
new_demo_hash = generate_password_hash('Demo@123')
cur.execute("UPDATE users SET password_hash = %s WHERE email = 'demo@blindguide.local'", (new_demo_hash,))
conn.commit()
print("Demo account password reset done.")

# Verify
cur.execute("SELECT password_hash FROM users WHERE email='demo@blindguide.local'")
row = cur.fetchone()
verified = check_password_hash(row[0], 'Demo@123')
print(f"Verification after reset: {verified}")

conn.close()

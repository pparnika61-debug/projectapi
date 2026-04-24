import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Show current users
print("Before Update:")
cursor.execute("SELECT username, tier FROM users")
print(cursor.fetchall())

# Update to premium
cursor.execute("UPDATE users SET tier='premium' WHERE username='parnika'")
conn.commit()

# Show updated users
print("After Update:")
cursor.execute("SELECT username, tier FROM users")
print(cursor.fetchall())

conn.close()
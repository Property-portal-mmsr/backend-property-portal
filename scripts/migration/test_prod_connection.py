import os
import pymysql

# Simple env parser since we want to avoid external dependencies if dotenv isn't there
env_vars = {}
with open('.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            env_vars[key.strip()] = val.strip()

HOST = env_vars.get('DB_HOST')
PORT = int(env_vars.get('DB_PORT', 3306))
USER = env_vars.get('DB_USER')
PASSWORD = env_vars.get('DB_PASSWORD')
DB_NAME = env_vars.get('DB_NAME')

def test_connection():
    try:
        conn = pymysql.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        print("--- CONNECTION SUCCESSFUL ---")
        with conn.cursor() as cur:
            cur.execute("SELECT @@hostname AS hostname, @@port AS port, DATABASE() AS database_name, CURRENT_USER()")
            print(cur.fetchone())
            
            print("\n--- TABLES ---")
            cur.execute("SHOW TABLES")
            tables = cur.fetchall()
            for t in tables:
                print(list(t.values())[0])
            
            print("\n--- COUNTS ---")
            cur.execute("SELECT COUNT(*) AS c FROM properties")
            print(f"properties: {cur.fetchone()['c']}")
            
            try:
                cur.execute("SELECT COUNT(*) AS c FROM property_images")
                print(f"property_images: {cur.fetchone()['c']}")
            except Exception as e:
                print("property_images: table does not exist yet")
                
            try:
                cur.execute("SELECT COUNT(*) AS c FROM property_amenities")
                print(f"property_amenities: {cur.fetchone()['c']}")
            except Exception as e:
                print("property_amenities: table does not exist yet")
                
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == '__main__':
    test_connection()

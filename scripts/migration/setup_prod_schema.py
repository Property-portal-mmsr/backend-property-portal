import pymysql

env_vars = {}
with open('.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            env_vars[key.strip()] = val.strip()

HOST = env_vars.get('DB_HOST', '127.0.0.1')
PORT = int(env_vars.get('DB_PORT', '3336'))
USER = env_vars.get('DB_USER', 'appuser')
PASSWORD = env_vars.get('DB_PASSWORD', '')
DB_NAME = env_vars.get('DB_NAME', 'property_portal')

try:
    conn = pymysql.connect(
        host=HOST,
        port=PORT,
        user=USER,
        password=PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
    with conn.cursor() as cur:
        with open('scripts/migration/01_schema_setup.sql', 'r') as f:
            sql_script = f.read()
            # Split the script into individual statements and execute them
            statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
            for stmt in statements:
                cur.execute(stmt)
    conn.commit()
    conn.close()
    print("Schema setup completed successfully.")
except Exception as e:
    print(f"Schema setup failed: {e}")

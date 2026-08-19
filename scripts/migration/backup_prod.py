import os
import subprocess
from datetime import datetime

env_vars = {}
with open('.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            env_vars[key.strip()] = val.strip()

HOST = env_vars.get('DB_HOST', '127.0.0.1')
PORT = env_vars.get('DB_PORT', '3336')
USER = env_vars.get('DB_USER', 'appuser')
PASSWORD = env_vars.get('DB_PASSWORD', '')
DB_NAME = env_vars.get('DB_NAME', 'property_portal')

backup_file = f"/Users/maheswaranm/dumps/property_portal_prod_backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.sql"

# Make dumps dir if it doesn't exist
os.makedirs("/Users/maheswaranm/dumps", exist_ok=True)

# Note: We pass password securely via env var to subprocess
env = os.environ.copy()
env['MYSQL_PWD'] = PASSWORD

cmd = [
    'mysqldump',
    '-h', HOST,
    '-P', PORT,
    '-u', USER,
    DB_NAME
]

print(f"Starting backup of {DB_NAME} on {HOST}:{PORT}...")
try:
    with open(backup_file, 'w') as out_f:
        process = subprocess.run(cmd, env=env, stdout=out_f, stderr=subprocess.PIPE, text=True)
        if process.returncode != 0:
            print(f"Error during backup: {process.stderr}")
        else:
            print(f"Backup successful: {backup_file}")
            print(f"Backup file size: {os.path.getsize(backup_file)} bytes")
except Exception as e:
    print(f"Failed to create backup: {e}")

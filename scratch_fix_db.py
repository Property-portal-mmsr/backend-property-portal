import sys
import os
sys.path.append(os.getcwd())
from app.database.database import engine
from sqlalchemy import text

with engine.begin() as conn:
    # 1. Delete seed script targets
    conn.execute(text("DELETE FROM employee_monthly_targets WHERE month IN ('7', '8');"))
    
    # 2. Convert string months to ints
    conn.execute(text("UPDATE employee_monthly_targets SET month = '8' WHERE month = 'August';"))
    conn.execute(text("UPDATE employee_monthly_targets SET month = '7' WHERE month = 'July';"))
    
    # 3. Alter table schema
    conn.execute(text("ALTER TABLE employee_monthly_targets DROP COLUMN employee_name;"))
    conn.execute(text("ALTER TABLE employee_monthly_targets MODIFY COLUMN month INT NOT NULL;"))

print("Database fixed successfully.")

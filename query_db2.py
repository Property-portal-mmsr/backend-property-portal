from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import text
from app.database.database import engine

with engine.connect() as conn:
    result = conn.execute(text("SELECT name, is_team_leader, role, designation FROM employees")).fetchall()
    for row in result:
        print(row)

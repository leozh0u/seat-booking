from pathlib import Path
import psycopg
from db import DATABASE_URL

def main():
    sql = Path("schema.sql").read_text()
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(sql)
    print("Schema applied.")

if __name__ == "__main__":
    main()

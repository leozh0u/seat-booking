from pathlib import Path
import psycopg
from db import DATABASE_URL

def main():
    sql = Path("schema.sql").read_text()
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(sql)
        # Seed the 8 demo seats with stable ids 1-8 (matches API validation).
        conn.execute("TRUNCATE event_seats RESTART IDENTITY")
        conn.execute(
            """
            INSERT INTO event_seats (event_id, seat_label)
            SELECT 1, 'A' || n FROM generate_series(1, 8) AS n
            """
        )
    print("Schema applied, 8 demo seats seeded.")

if __name__ == "__main__":
    main()

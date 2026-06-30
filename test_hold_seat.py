from concurrent.futures import ThreadPoolExecutor
import psycopg
from db import DATABASE_URL
from hold_seat import hold_seat

def reset_seat():
    """Wipe and recreate one known seat, status available, return its id."""
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("DELETE FROM event_seats WHERE event_id = 1")
        cur = conn.execute(
            """
            INSERT INTO event_seats (event_id, seat_label, status)
            VALUES (1, 'A1', 'available')
            RETURNING id
            """
        )
        row = cur.fetchone()
        return row[0]

def test_only_one_winner():
    seat_id = reset_seat()

    def try_hold(user_id):
        return hold_seat(seat_id, user_id)

    user_ids = [f"user{i}" for i in range(50)]

    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(try_hold, user_ids))

    winners = results.count(True)
    assert winners == 1
import psycopg
from db import DATABASE_URL

def hold_seat(seat_id: int, user_id: str) -> bool:
    """
    Try to put a hold on a seat. Returns True if this call won the seat,
    False if someone else already holds/booked it.
    """
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        cur = conn.execute(
            """
            UPDATE event_seats
            SET status = 'held', held_by = %s, held_until = now() + interval '5 minutes'
            WHERE id = %s AND status = 'available'
            """,
            (user_id, seat_id),
        )
        return cur.rowcount == 1


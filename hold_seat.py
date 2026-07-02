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
            WHERE id = %s AND (status = 'available' OR (status = 'held' AND held_until < now()))
            """,
            (user_id, seat_id),
        )
        return cur.rowcount == 1

def confirm_seat(seat_id: int, user_id: str, idempotency_key: str) -> dict:
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        # check if this idempotency key already processed this seat
        row = conn.execute(
            "SELECT status, idempotency_key FROM event_seats WHERE id = %s",
            (seat_id,),
        ).fetchone()

        if row and row[1] == idempotency_key:
            return {"confirmed": row[0] == "booked", "replay": True}

        cur = conn.execute(
            """
            UPDATE event_seats
            SET status = 'booked', idempotency_key = %s
            WHERE id = %s AND status = 'held' AND held_by = %s
            """,
            (idempotency_key, seat_id, user_id),
        )
        return {"confirmed": cur.rowcount == 1, "replay": False}
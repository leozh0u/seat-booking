from concurrent.futures import ThreadPoolExecutor
import threading
import psycopg
from db import DATABASE_URL
from hold_seat import hold_seat, confirm_seat

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
    barrier = threading.Barrier(50)

    def try_hold(user_id):
        barrier.wait()
        return hold_seat(seat_id, user_id)

    user_ids = [f"user{i}" for i in range(50)]
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(try_hold, user_ids))

    winners = results.count(True)
    assert winners == 1


def test_expired_hold_reclaimed():
    """A held seat past its TTL should be reclaimable by exactly one concurrent request."""
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("DELETE FROM event_seats WHERE event_id = 1")
        cur = conn.execute(
            """
            INSERT INTO event_seats (event_id, seat_label, status, held_by, held_until)
            VALUES (1, 'A1', 'held', 'old_user', now() - interval '1 minute')
            RETURNING id
            """
        )
        seat_id = cur.fetchone()[0]

    barrier = threading.Barrier(50)

    def try_hold(user_id):
        barrier.wait()
        return hold_seat(seat_id, user_id)

    user_ids = [f"user{i}" for i in range(50)]
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(try_hold, user_ids))

    assert results.count(True) == 1

def test_confirm_idempotent():
    seat_id = reset_seat()
    hold_seat(seat_id, "userA")

    result1 = confirm_seat(seat_id, "userA", "key123")
    assert result1 == {"confirmed": True, "replay": False}

    result2 = confirm_seat(seat_id, "userA", "key123")
    assert result2 == {"confirmed": True, "replay": True}
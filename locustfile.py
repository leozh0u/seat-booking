import random
import uuid
from locust import HttpUser, task, between


class SeatUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(3)
    def hold_seat(self):
        seat_id = random.randint(1, 8)
        user_id = f"user_{random.randint(1, 10000)}"
        self.client.post(f"/seats/{seat_id}/hold?user_id={user_id}")

    @task(1)
    def confirm_seat(self):
        seat_id = random.randint(1, 8)
        user_id = f"user_{random.randint(1, 10000)}"
        key = str(uuid.uuid4())
        self.client.post(
            f"/seats/{seat_id}/confirm?user_id={user_id}&idempotency_key={key}"
        )

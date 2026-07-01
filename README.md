- **Postgres** — stores seat state; atomic UPDATE prevents double-booking
- **Redis** — pub/sub message bus; broadcasts seat changes to all connected clients
- **WebSockets** — pushes real-time seat updates to every open browser
- **React** — seat map UI; seats turn red instantly when booked

## Technical Highlights

- Atomic conditional UPDATE in Postgres prevents double-booking under concurrent load
- Concurrency test fires N simultaneous requests at one seat and asserts exactly one wins
- Redis pub/sub decouples booking logic from notification — multi-server safe
- WebSocket connections subscribe to Redis independently, enabling horizontal scaling
- Dockerized with Docker Compose — entire stack spins up with `docker compose up`
- GitHub Actions CI runs the test suite on every push

## Stack

- **Backend:** Python, FastAPI, psycopg
- **Database:** PostgreSQL
- **Cache/Pub-sub:** Redis
- **Frontend:** React, Vite
- **DevOps:** Docker, Docker Compose, GitHub Actions, Sentry

## Running Locally

### Without Docker

```bash
# Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Apply schema
python setup_db.py

# Start backend
uvicorn main:app --reload

# Start frontend (separate terminal)
cd frontend && npm install && npm run dev
```

### With Docker

```bash
docker compose up

# One-time: apply schema
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/postgres python setup_db.py
```

## Testing

```bash
pytest test_hold_seat.py -v
```

The concurrency test fires multiple simultaneous requests at a single seat and asserts exactly one succeeds.
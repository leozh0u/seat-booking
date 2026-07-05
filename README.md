# SeatLive

Real-time event seat-booking platform. Solves the core hard problem in any booking system: preventing double-booked seats under concurrent load, using an atomic conditional UPDATE in Postgres rather than application-level locking.

## Architecture

```
┌──────────────┐      HTTP       ┌──────────────┐
│  React (5173) │ ───────────────▶│ FastAPI (8000)│
└──────┬───────┘                 └──────┬───────┘
       │  WebSocket                     │
       │                          ┌─────▼─────┐
       │                          │ PostgreSQL │  ← atomic UPDATE,
       │                          │  (5432)    │    row-level locking
       │                          └─────┬─────┘
       │                                │
       │                          ┌─────▼─────┐
       └─────────────────────────▶│   Redis    │  pub/sub broadcast
          seat_updates channel    │  (6379)    │
                                  └────────────┘
```

Flow: client holds a seat → atomic UPDATE wins or loses → winner publishes to Redis → every server instance's WebSocket handler is subscribed and broadcasts to its own connected clients → all browsers update instantly, no polling.

## Core correctness guarantee

```sql
UPDATE event_seats
SET status = 'held', held_by = %s, held_until = now() + interval '5 minutes'
WHERE id = %s AND (status = 'available' OR (status = 'held' AND held_until < now()))
```

The check and the mutation are the same statement — no gap between "is it available?" and "mark it held." Postgres serializes concurrent writes to the same row via row-level locking, so exactly one concurrent request wins. Verified under 50-thread `threading.Barrier` load in `test_hold_seat.py`.

## Stack

- **Backend:** Python 3.14, FastAPI, psycopg
- **Database:** PostgreSQL
- **Real-time:** Redis pub/sub, WebSockets
- **Frontend:** React + Vite
- **Infra:** Docker Compose, GitHub Actions CI, Sentry error monitoring
- **Load testing:** Locust

## Local setup

```bash
git clone https://github.com/leozh0u/seat-booking.git
cd seat-booking
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt --break-system-packages
```

Start Postgres and Redis locally (Postgres.app + `brew services start redis`), or via Docker:

```bash
docker compose up
```

Run the backend:

```bash
export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"
python3.14 -m uvicorn main:app --reload
```

Run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend on `:8000`, frontend on `:5173`.

## API

| Endpoint | Method | Description |
|---|---|---|
| `/seats/{seat_id}/hold` | POST | Atomically hold a seat (rate-limited, validated) |
| `/seats/{seat_id}/confirm` | POST | Convert a hold into a booking, idempotent via client-supplied key |
| `/ws` | WebSocket | Real-time seat status broadcast |

## Testing

```bash
pytest test_hold_seat.py -v
```

Covers: single-winner correctness under 50-thread concurrent load, expired-hold reclamation under concurrency, and confirm idempotency/replay detection.

## Load testing

See [`LOAD_TESTING.md`](./LOAD_TESTING.md) for real Locust results: 4459 requests, 0 failures, 18.7 req/s, p95 570ms.

## Known limitations

- Confirm idempotency key is not scoped per-user — a key collision across two different users' clients would leak one confirm result to the other. Low risk with UUIDs, real tradeoff.
- DB calls are synchronous (psycopg) inside async endpoints, briefly blocking the event loop under load. An async driver would remove this.
- No structured logging yet — Sentry covers unhandled exceptions but there's no request/response audit trail.

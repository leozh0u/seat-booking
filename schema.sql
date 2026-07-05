CREATE TABLE IF NOT EXISTS event_seats (
  id          BIGSERIAL PRIMARY KEY,
  event_id    BIGINT NOT NULL,
  seat_label  TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'available'
              CHECK (status IN ('available','held','booked')),
  held_by     TEXT,
  held_until  TIMESTAMPTZ,
  idempotency_key TEXT,
  UNIQUE (event_id, seat_label)
);

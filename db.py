import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://localhost:5432/postgres",
)

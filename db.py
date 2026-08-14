import os
from sqlmodel import create_engine, SQLModel
from config import settings

# Ensure data directory exists before creating the SQLite DB file
os.makedirs("./data", exist_ok=True)

engine = create_engine(settings.DATABASE_URL, echo=False)

# Create tables (idempotent)
# Note: Importing models is not necessary here; SQLModel.metadata includes definitions when models are imported elsewhere,
# but calling create_all after models are imported ensures tables exist. We'll call create_all where appropriate.

# You may call SQLModel.metadata.create_all(engine) after importing models in main application startup if preferred.

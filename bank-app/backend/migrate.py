"""
Adds new columns to existing tables that were added in models.py
Safe to run multiple times — skips columns that already exist.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine
import models
from sqlalchemy import text

# Create any brand-new tables (loans, notifications)
print("Creating new tables if missing...")
models.Base.metadata.create_all(bind=engine)

# ALTER TABLE for new columns on users (SQLite safe approach)
new_columns = [
    ("users", "phone",   "TEXT"),
    ("users", "address", "TEXT"),
]

with engine.connect() as conn:
    for table, col, col_type in new_columns:
        # Check existing columns
        result = conn.execute(text(f"PRAGMA table_info({table})"))
        existing = [row[1] for row in result.fetchall()]
        if col not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
            print(f"  ✓ Added column '{col}' to '{table}'")
        else:
            print(f"  - Column '{col}' in '{table}' already exists, skipping.")
    conn.commit()

print("\nMigration complete!")

"""Upsert checked-in style packages into the local catalog."""

from style_catalog import connect, seed


if __name__ == "__main__":
    with connect() as db:
        count = seed(db)
    print(f"Seeded {count} styles. Run the preview worker for pending styles.")

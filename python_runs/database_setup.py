import pandas as pd
from sqlalchemy import create_engine
import os

# root project folder is one level above python_runs/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "ecommerce-data")
DB_PATH = os.path.join(BASE_DIR, "ecommerce.db")


def build_ecommerce_db():

    # connect to sqlite - creates ecommerce.db if it doesn't exist yet
    engine = create_engine(f"sqlite:///{DB_PATH}")

    # map each csv to a clean, simple table name
    tables_to_process = {
        "customers": "customers_dataset.csv",
        "orders": "orders_dataset.csv",
        "order_items": "order_items_dataset.csv",
        "order_payments": "order_payments_dataset.csv",
        "order_reviews": "order_reviews_dataset.csv",
        "products": "products_dataset.csv",
        "sellers": "sellers_dataset.csv",
        "geolocation": "geolocation_dataset.csv",
        "category_translation": "product_category_name_translation.csv"
    }

    print("starting the database build...\n")

    for table_name, filename in tables_to_process.items():
        filepath = os.path.join(DATA_DIR, filename)

        # skip missing files instead of crashing
        if not os.path.exists(filepath):
            print(f"warning: {filename} not found - skipping")
            continue

        print(f"processing {filename} into table '{table_name}'...")

        df = pd.read_csv(filepath)

        # --- CLEANING PHASE ---

        # standardize column names to lowercase with underscores
        df.columns = [c.lower().replace(" ", "_").strip() for c in df.columns]

        # convert date columns to consistent text format for sqlite
        for col in df.columns:
            if "date" in col or "timestamp" in col:
                df[col] = pd.to_datetime(df[col], errors="coerce")
                df[col] = df[col].astype(str).replace("NaT", "Unknown")

        # fill missing values so queries don't return None
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].fillna("Unknown")
            else:
                df[col] = df[col].fillna(0)

        # --- SAVE TO DATABASE ---
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        print(f"done - {len(df):,} rows loaded into '{table_name}'")

    print(f"\nall done! your database is ready at: {DB_PATH}")


if __name__ == "__main__":
    build_ecommerce_db()
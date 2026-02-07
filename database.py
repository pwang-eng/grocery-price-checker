"""
database.py - Sets up and manages the SQLite database for grocery prices.
"""

import sqlite3
import pandas as pd
import os

DB_PATH = "grocery.db"

def get_connection():
    """Opens a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """Creates the database tables if they don't exist yet."""
    conn = get_connection()
    cursor = conn.cursor()

    # Products Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            category TEXT,
            brand TEXT,
            unit TEXT,
            no_frills_price REAL,
            food_basics_price REAL,
            walmart_price REAL,
            freshco_price REAL,
            loblaws_price REAL,
            source TEXT DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Flyer Deals Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flyer_deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            store TEXT NOT NULL,
            sale_price REAL NOT NULL,
            regular_price REAL,
            start_date TEXT,
            end_date TEXT,
            flyer_source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Recipes Table (NEW)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            ingredients TEXT NOT NULL,
            instructions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("Database tables created successfully!")

def load_seed_data():
    """Loads seed price data from CSV."""
    csv_path = os.path.join("data", "seed_prices.csv")
    if not os.path.exists(csv_path):
        print(f"Error: Could not find {csv_path}")
        return

    df = pd.read_csv(csv_path)
    conn = get_connection()
    conn.execute("DELETE FROM products")
    df.to_sql("products", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()
    print(f"Loaded {len(df)} products into the database!")

def add_flyer_deal(product_name, store, sale_price, regular_price=None,
                   start_date=None, end_date=None, flyer_source=None):
    """Adds a single flyer deal."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO flyer_deals 
        (product_name, store, sale_price, regular_price, start_date, end_date, flyer_source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (product_name, store, sale_price, regular_price, start_date, end_date, flyer_source))
    conn.commit()
    conn.close()

def get_all_products():
    """Returns all products."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return df

def get_flyer_deals():
    """Returns all flyer deals."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM flyer_deals", conn)
    conn.close()
    return df

def search_products(query):
    """Search for products by name."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM products WHERE LOWER(product_name) LIKE LOWER(?)",
        conn,
        params=[f"%{query}%"]
    )
    conn.close()
    return df

# --- RECIPE MANAGEMENT ---

def save_recipe(title, ingredients, instructions=""):
    """Saves a new recipe to the database."""
    # Ensure table exists (just in case)
    conn = get_connection()
    cursor = conn.cursor()

    # Handle list input
    if isinstance(ingredients, list):
        ingredients = "\n".join(ingredients)

    cursor.execute(
        'INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)',
        (title, ingredients, instructions)
    )
    conn.commit()
    conn.close()

def get_saved_recipes():
    """Retrieves all saved recipes."""
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM recipes ORDER BY created_at DESC", conn)
    except Exception:
        # Return empty DF if table missing
        df = pd.DataFrame(columns=["id", "title", "ingredients", "instructions", "created_at"])
    conn.close()
    return df

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    setup_database()
    load_seed_data()

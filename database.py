"""
database.py - Sets up and manages the SQLite database for grocery prices.

HOW TO RUN (first time setup):
    python database.py

This will:
1. Create a grocery.db SQLite database
2. Load all the seed price data from data/seed_prices.csv
3. Create a table for flyer deals (parsed from flyer images later)

You can also import functions from this file in other scripts.
"""

import sqlite3
import pandas as pd
import os


# ---------------------------------------------------------------------------
# DATABASE FILE LOCATION
# ---------------------------------------------------------------------------
# This is relative to wherever you run the script from.
# If you run `python database.py` from the project root, it will create
# grocery.db in the project root folder.
DB_PATH = "grocery.db"


def get_connection():
    """
    Opens a connection to the SQLite database.
    
    Think of this like opening a file — you need to open it before
    you can read or write to it, and close it when you're done.
    
    Returns:
        sqlite3.Connection object
    """
    conn = sqlite3.connect(DB_PATH)
    # This makes it so query results come back as dictionaries 
    # instead of tuples. Much easier to work with.
    conn.row_factory = sqlite3.Row
    return conn


def setup_database():
    """
    Creates the database tables if they don't exist yet.
    
    We have two tables:
    1. products - the main price comparison table (from seed data + scraped)
    2. flyer_deals - special deals parsed from store flyers
    """
    conn = get_connection()
    cursor = conn.cursor()

    # -----------------------------------------------------------------------
    # TABLE 1: products
    # This stores the "regular" price of items at each store.
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # TABLE 2: flyer_deals
    # This stores temporary sale prices parsed from flyer images.
    # These override the regular prices when active.
    # -----------------------------------------------------------------------
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

    conn.commit()
    conn.close()
    print("✅ Database tables created successfully!")


def load_seed_data():
    """
    Loads the seed price data from the CSV file into the database.
    
    This is the manually-created price data for ~60 common grocery items.
    You only need to run this once (or again if you update the CSV).
    """
    csv_path = os.path.join("data", "seed_prices.csv")

    if not os.path.exists(csv_path):
        print(f"❌ Error: Could not find {csv_path}")
        print("   Make sure you're running this from the project root folder.")
        return

    # Read the CSV into a pandas DataFrame
    df = pd.read_csv(csv_path)

    conn = get_connection()

    # Clear existing data so we don't get duplicates if run multiple times
    conn.execute("DELETE FROM products")

    # Write the DataFrame to the database
    # if_exists='append' means add rows to existing table
    df.to_sql("products", conn, if_exists="append", index=False)

    conn.commit()
    conn.close()

    print(f"✅ Loaded {len(df)} products into the database!")


def add_flyer_deal(product_name, store, sale_price, regular_price=None,
                   start_date=None, end_date=None, flyer_source=None):
    """
    Adds a single flyer deal to the database.
    
    This is called by the flyer parser after it extracts deals from
    a flyer image using Gemini Vision.
    
    Args:
        product_name: Name of the product (e.g., "Chicken Breast")
        store: Store name (e.g., "Food Basics")
        sale_price: The sale price as a float (e.g., 4.98)
        regular_price: Optional regular price for comparison
        start_date: Optional sale start date
        end_date: Optional sale end date
        flyer_source: Optional filename of the flyer image
    """
    conn = get_connection()
    conn.execute("""
        INSERT INTO flyer_deals 
        (product_name, store, sale_price, regular_price, start_date, end_date, flyer_source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (product_name, store, sale_price, regular_price, start_date, end_date, flyer_source))
    conn.commit()
    conn.close()


def get_all_products():
    """
    Returns all products from the database as a pandas DataFrame.
    
    Use this when you need to search through all products for
    price comparison.
    """
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return df


def get_flyer_deals():
    """
    Returns all current flyer deals as a pandas DataFrame.
    """
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM flyer_deals", conn)
    conn.close()
    return df


def search_products(query):
    """
    Search for products by name (case-insensitive partial match).
    
    Args:
        query: Search string (e.g., "milk", "chicken")
    
    Returns:
        pandas DataFrame of matching products
    """
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM products WHERE LOWER(product_name) LIKE LOWER(?)",
        conn,
        params=[f"%{query}%"]
    )
    conn.close()
    return df


# ---------------------------------------------------------------------------
# MAIN - Run this file directly to set up the database
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("🛒 Setting up GrocerAI database...")
    print("-" * 40)
    setup_database()
    load_seed_data()
    print("-" * 40)

    # Quick test: show what's in the database
    df = get_all_products()
    print(f"\n📊 Database contains {len(df)} products")
    print(f"   Categories: {', '.join(df['category'].unique())}")
    print(f"\n🔍 Sample search for 'chicken':")
    results = search_products("chicken")
    for _, row in results.iterrows():
        print(f"   {row['product_name']} ({row['brand']}) - "
              f"No Frills: ${row['no_frills_price']:.2f}, "
              f"Walmart: ${row['walmart_price']:.2f}")
    print("\n✅ Database is ready! You can now run the app with: streamlit run app.py")

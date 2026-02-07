"""
comparison.py - The core price comparison engine.

This is the brain of the app. It takes a user's grocery list,
finds the items in the database, and figures out the cheapest store.

HOW TO USE:
    from comparison import compare_prices, find_cheapest_store
    
    results = compare_prices(["milk", "eggs", "chicken breast", "bread"])
    cheapest = find_cheapest_store(results)
"""

import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
import pandas as pd
from database import get_all_products, get_flyer_deals

load_dotenv()

# Store column mapping - maps store names to database column names
STORE_COLUMNS = {
    "No Frills": "no_frills_price",
    "Food Basics": "food_basics_price",
    "Walmart": "walmart_price",
    "FreshCo": "freshco_price",
    "Loblaws": "loblaws_price",
}


def setup_gemini():
    """Set up Gemini for fuzzy matching."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def fuzzy_match_items(user_items, available_products):
    """
    Uses Gemini to match user's grocery list items to products in our database.
    
    For example, if the user types "milk" and our database has:
    - "2% Milk 4L"
    - "Whole Milk 4L"  
    - "1% Milk 4L"
    
    Gemini will pick the best match (probably "2% Milk 4L" as default).
    
    Args:
        user_items: List of strings the user typed (e.g., ["milk", "chicken"])
        available_products: List of product names from our database
        
    Returns:
        Dictionary mapping user items to database product names.
        Example: {"milk": "2% Milk 4L", "chicken": "Chicken Breast Boneless"}
        If no match found, the value will be None.
    """
    model = setup_gemini()

    if model is None:
        # Fallback: simple keyword matching if no API key
        print("⚠️  No Gemini API key - using basic keyword matching")
        return _basic_keyword_match(user_items, available_products)

    prompt = f"""
    I have a grocery database with these products:
    {json.dumps(available_products)}
    
    A user wants to buy these items:
    {json.dumps(user_items)}
    
    Match each user item to the BEST matching product from the database.
    If there's no reasonable match, set the value to null.
    
    Return ONLY a JSON object mapping user items to database product names.
    No markdown, no backticks, no explanation.
    
    Example: {{"milk": "2% Milk 4L", "chips": "Lays Chips"}}
    """

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Clean up response
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0].strip()

        matches = json.loads(response_text)
        return matches

    except Exception as e:
        print(f"⚠️  Gemini matching failed ({e}), falling back to keyword match")
        return _basic_keyword_match(user_items, available_products)


def _basic_keyword_match(user_items, available_products):
    """
    Simple fallback matching using keyword overlap.
    Used when Gemini is unavailable.
    """
    matches = {}
    for user_item in user_items:
        user_words = user_item.lower().split()
        best_match = None
        best_score = 0

        for product in available_products:
            product_lower = product.lower()
            score = sum(1 for word in user_words if word in product_lower)
            if score > best_score:
                best_score = score
                best_match = product

        matches[user_item] = best_match if best_score > 0 else None

    return matches


def compare_prices(user_grocery_list):
    """
    Main comparison function. Takes a grocery list and returns price data.
    
    Args:
        user_grocery_list: List of item strings (e.g., ["milk", "eggs", "bread"])
    
    Returns:
        Dictionary with:
        - "items": list of matched items with prices at each store
        - "totals": total cost at each store
        - "cheapest_store": name of the cheapest store
        - "potential_savings": how much you save vs the most expensive store
        - "unmatched": items we couldn't find in the database
    """
    # Step 1: Get all products from database
    products_df = get_all_products()
    available_products = products_df["product_name"].tolist()

    # Step 2: Use Gemini to match user items to database products
    print(f"🔍 Matching {len(user_grocery_list)} items...")
    matches = fuzzy_match_items(user_grocery_list, available_products)

    # Step 3: Build the comparison table
    items = []
    unmatched = []

    for user_item, matched_product in matches.items():
        if matched_product is None:
            unmatched.append(user_item)
            continue

        # Find this product in the database
        product_row = products_df[products_df["product_name"] == matched_product]

        if product_row.empty:
            unmatched.append(user_item)
            continue

        product_row = product_row.iloc[0]

        # Build price comparison for this item
        item_data = {
            "user_input": user_item,
            "matched_product": matched_product,
            "brand": product_row.get("brand", ""),
            "unit": product_row.get("unit", ""),
            "prices": {}
        }

        # Get price at each store
        cheapest_price = float("inf")
        cheapest_store = None

        for store_name, col_name in STORE_COLUMNS.items():
            price = product_row.get(col_name)
            if pd.notna(price):
                item_data["prices"][store_name] = float(price)
                if float(price) < cheapest_price:
                    cheapest_price = float(price)
                    cheapest_store = store_name

        item_data["cheapest_store"] = cheapest_store
        item_data["cheapest_price"] = cheapest_price
        items.append(item_data)

    # Step 4: Calculate store totals
    totals = {store: 0.0 for store in STORE_COLUMNS.keys()}

    for item in items:
        for store, price in item["prices"].items():
            totals[store] += price

    # Step 5: Find the overall cheapest store
    cheapest_store = min(totals, key=totals.get)
    most_expensive_store = max(totals, key=totals.get)
    savings = totals[most_expensive_store] - totals[cheapest_store]

    return {
        "items": items,
        "totals": totals,
        "cheapest_store": cheapest_store,
        "cheapest_total": totals[cheapest_store],
        "most_expensive_store": most_expensive_store,
        "most_expensive_total": totals[most_expensive_store],
        "potential_savings": round(savings, 2),
        "unmatched": unmatched,
        "items_matched": len(items),
        "items_total": len(user_grocery_list),
    }


def expand_meal_to_ingredients(meal_description):
    """
    Uses Gemini to convert a meal description into a grocery list.
    
    Example: "tacos for 4 people" -> ["ground beef", "taco shells", 
             "lettuce", "tomatoes", "cheese", "sour cream", "salsa"]
    
    Args:
        meal_description: Natural language description of a meal
        
    Returns:
        List of ingredient strings
    """
    model = setup_gemini()
    if model is None:
        print("❌ Gemini API key required for meal expansion")
        return []

    prompt = f"""
    Convert this meal description into a simple grocery shopping list:
    "{meal_description}"
    
    Return ONLY a JSON array of ingredient strings. Use common/generic names.
    Keep it practical — only include things you'd actually need to buy.
    
    Example: ["ground beef", "taco shells", "shredded cheese", "lettuce", "tomatoes"]
    
    No markdown, no backticks, no explanation. Just the JSON array.
    """

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0].strip()

        ingredients = json.loads(response_text)
        return ingredients

    except Exception as e:
        print(f"❌ Error expanding meal: {e}")
        return []


def format_results_text(results):
    """
    Formats comparison results as readable text.
    Used for terminal output and can be passed to Gemini for summarization.
    """
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"  🛒 GROCERY PRICE COMPARISON")
    lines.append(f"{'='*60}")

    # Item breakdown
    lines.append(f"\n📋 Matched {results['items_matched']}/{results['items_total']} items:\n")

    for item in results["items"]:
        lines.append(f"  {item['user_input']} → {item['matched_product']}")
        for store, price in sorted(item["prices"].items(), key=lambda x: x[1]):
            marker = " ✅" if store == item["cheapest_store"] else ""
            lines.append(f"    {store:15s}  ${price:.2f}{marker}")
        lines.append("")

    # Unmatched items
    if results["unmatched"]:
        lines.append(f"  ⚠️  Could not find: {', '.join(results['unmatched'])}\n")

    # Store totals
    lines.append(f"{'─'*60}")
    lines.append(f"  💰 STORE TOTALS:\n")

    for store, total in sorted(results["totals"].items(), key=lambda x: x[1]):
        marker = " ← CHEAPEST! 🏆" if store == results["cheapest_store"] else ""
        lines.append(f"    {store:15s}  ${total:.2f}{marker}")

    lines.append(f"\n  💵 You save ${results['potential_savings']:.2f} shopping at "
                 f"{results['cheapest_store']} vs {results['most_expensive_store']}!")
    lines.append(f"{'='*60}\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MAIN - Run this file directly to test the comparison engine
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("🧪 Testing comparison engine...\n")

    # Test with a sample grocery list
    test_list = ["milk", "eggs", "chicken breast", "bread", "bananas", "pasta", "cheese"]

    results = compare_prices(test_list)
    print(format_results_text(results))

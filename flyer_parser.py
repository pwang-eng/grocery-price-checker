"""
flyer_parser.py - Uses Gemini Vision to extract prices from grocery store flyer images.

HOW TO USE:
    python flyer_parser.py data/flyers/food_basics_page1.png

    Or import and use in code:
        from flyer_parser import parse_flyer_image
        deals = parse_flyer_image("path/to/flyer.png", "Food Basics")

IMPORTANT: 
    - Use SNIPPET images, not full flyer pages! 
    - Full flyer pages are too small/blurry for the AI to read.
    - Screenshot individual sections of the flyer (4-8 products per image).
    - Save as PNG for best quality.

SETUP:
    1. Make sure you have a .env file with GEMINI_API_KEY=your_key
    2. Put flyer images in data/flyers/
    3. Run this script with the image path as an argument
"""

import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
import sys
from PIL import Image
from database import add_flyer_deal

# Load API key from .env file
load_dotenv()


def setup_gemini():
    """
    Configures the Gemini API with your API key.
    
    The API key comes from your .env file. If you don't have one yet:
    1. Go to https://aistudio.google.com/apikey
    2. Click "Create API Key"
    3. Copy the key
    4. Paste it into your .env file: GEMINI_API_KEY=your_key_here
    """
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key or api_key == "your_gemini_api_key_here":
        print("❌ Error: No Gemini API key found!")
        print("   1. Go to https://aistudio.google.com/apikey")
        print("   2. Create an API key")
        print("   3. Add it to your .env file: GEMINI_API_KEY=your_key")
        sys.exit(1)

    genai.configure(api_key=api_key)
    # Use gemini-2.0-flash for vision tasks (fast + free tier friendly)
    model = genai.GenerativeModel("gemini-2.0-flash")
    return model


def parse_flyer_image(image_path, store_name):
    """
    Takes a flyer image and extracts product names and prices using Gemini Vision.
    
    Args:
        image_path: Path to the flyer image file (PNG recommended)
        store_name: Name of the store (e.g., "Food Basics", "No Frills")
    
    Returns:
        List of dictionaries, each with:
            - product_name (str)
            - sale_price (float)
            - regular_price (float or None)
            - unit (str) - e.g., "each", "per lb", "per kg"
            - brand (str or None)
    
    Example return:
        [
            {
                "product_name": "Chicken Breast Boneless",
                "sale_price": 4.98,
                "regular_price": null,
                "unit": "per lb",
                "brand": "Prime"
            },
            ...
        ]
    """
    model = setup_gemini()

    # Open the image using PIL (Python Imaging Library)
    if not os.path.exists(image_path):
        print(f"❌ Error: Image not found at {image_path}")
        return []

    image = Image.open(image_path)

    # ----- THIS IS THE KEY PART: THE PROMPT -----
    # We tell Gemini exactly what format we want back.
    # The more specific the prompt, the better the results.
    prompt = f"""
    You are analyzing a grocery store flyer image from {store_name} (Canada).
    
    Extract EVERY product you can see with its price. 
    
    Return ONLY a valid JSON array (no markdown, no backticks, no explanation).
    Each item should have these fields:
    - "product_name": descriptive name of the product
    - "sale_price": the advertised price as a number (e.g., 4.98 not "$4.98")
    - "regular_price": the regular/original price if shown, otherwise null
    - "unit": what the price is for - "each", "per lb", "per kg", "per 100g", or the package size like "750g"
    - "brand": the brand name if visible, otherwise null
    
    Rules:
    - Always use the SALE price (the big number), not the regular price
    - If a price says "/LB" or "/lb", set unit to "per lb"  
    - If a price says "/KG" or "/kg", set unit to "per kg"
    - If no unit is specified, assume "each"
    - Include the package size in the product name if visible (e.g., "Ritz Crackers 200g")
    - Do NOT include promotional text, contest info, or non-product items
    
    Return ONLY the JSON array. Example format:
    [
        {{"product_name": "Chicken Breast Boneless", "sale_price": 4.98, "regular_price": 6.99, "unit": "per lb", "brand": "Prime"}},
        {{"product_name": "White Bread 675g", "sale_price": 2.98, "regular_price": null, "unit": "each", "brand": "Dempsters"}}
    ]
    """

    # Send the image + prompt to Gemini
    print(f"🔍 Analyzing flyer image: {image_path}")
    print(f"   Store: {store_name}")

    try:
        response = model.generate_content([prompt, image])
        response_text = response.text.strip()

        # Clean up the response - sometimes Gemini wraps it in ```json blocks
        if response_text.startswith("```"):
            # Remove ```json and ``` wrapper
            response_text = response_text.split("\n", 1)[1]  # Remove first line
            response_text = response_text.rsplit("```", 1)[0]  # Remove last ```
            response_text = response_text.strip()

        # Parse the JSON
        deals = json.loads(response_text)

        print(f"✅ Found {len(deals)} products!")
        return deals

    except json.JSONDecodeError as e:
        print(f"❌ Error: Gemini returned invalid JSON")
        print(f"   Raw response: {response_text[:500]}")
        print(f"   Error: {e}")
        return []
    except Exception as e:
        print(f"❌ Error calling Gemini API: {e}")
        return []


def save_deals_to_database(deals, store_name, flyer_source=None):
    """
    Saves parsed flyer deals to the SQLite database.
    
    Args:
        deals: List of deal dictionaries from parse_flyer_image()
        store_name: Name of the store
        flyer_source: Optional filename of the flyer image
    """
    saved_count = 0
    for deal in deals:
        try:
            add_flyer_deal(
                product_name=deal["product_name"],
                store=store_name,
                sale_price=deal["sale_price"],
                regular_price=deal.get("regular_price"),
                flyer_source=flyer_source
            )
            saved_count += 1
        except Exception as e:
            print(f"   ⚠️  Could not save '{deal.get('product_name', 'unknown')}': {e}")

    print(f"💾 Saved {saved_count}/{len(deals)} deals to database")


def print_deals(deals, store_name):
    """Pretty-prints the extracted deals to the terminal."""
    print(f"\n{'='*60}")
    print(f"  📋 {store_name} Flyer Deals")
    print(f"{'='*60}")

    for deal in deals:
        brand = deal.get('brand', '')
        brand_str = f"({brand}) " if brand else ""
        unit = deal.get('unit', 'each')
        reg_price = deal.get('regular_price')
        reg_str = f" (reg ${reg_price:.2f})" if reg_price else ""

        print(f"  ${deal['sale_price']:.2f}/{unit} - {brand_str}{deal['product_name']}{reg_str}")

    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# MAIN - Run this file directly to parse a flyer image
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Check if user provided an image path
    if len(sys.argv) < 2:
        print("Usage: python flyer_parser.py <image_path> [store_name]")
        print("")
        print("Examples:")
        print("  python flyer_parser.py data/flyers/food_basics_meat.png \"Food Basics\"")
        print("  python flyer_parser.py data/flyers/nofrills_produce.png \"No Frills\"")
        print("")
        print("Tips:")
        print("  - Use cropped SECTIONS of flyers, not full pages")
        print("  - PNG format works best")
        print("  - 4-8 products per image is ideal")
        sys.exit(1)

    image_path = sys.argv[1]
    store_name = sys.argv[2] if len(sys.argv) > 2 else "Unknown Store"

    # Parse the flyer
    deals = parse_flyer_image(image_path, store_name)

    if deals:
        # Show the results
        print_deals(deals, store_name)

        # Ask if user wants to save to database
        save = input("Save these deals to the database? (y/n): ").strip().lower()
        if save == "y":
            save_deals_to_database(deals, store_name, flyer_source=image_path)
            print("✅ Done!")
    else:
        print("No deals found. Try a clearer/closer image of the flyer.")

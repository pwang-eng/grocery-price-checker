"""
app.py - The Streamlit web frontend for Grocery Goose.

HOW TO RUN:
    streamlit run app.py

This will open a browser window with the app.
Make sure you've run `python database.py` first to set up the database!
"""

import streamlit as st
import pandas as pd
from database import setup_database, load_seed_data, get_all_products, get_flyer_deals
from comparison import compare_prices, expand_meal_to_ingredients, STORE_COLUMNS
from flyer_parser import parse_flyer_image, save_deals_to_database
import os


# ---------------------------------------------------------------------------
# PAGE CONFIG - Must be the first Streamlit command
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Grocery Goose - Smart Grocery Price Comparison",
    layout="wide"
)


# ---------------------------------------------------------------------------
# DATABASE INITIALIZATION
# On first run, this creates the database and loads seed data.
# Uses st.session_state so it only runs once per session.
# ---------------------------------------------------------------------------
if "db_initialized" not in st.session_state:
    setup_database()
    if get_all_products().empty:
        load_seed_data()
    st.session_state.db_initialized = True


# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
st.title("Grocery Goose")
st.markdown("*Find the cheapest groceries across local stores using AI*")
st.divider()


# ---------------------------------------------------------------------------
# SIDEBAR - Flyer Upload
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Upload Store Flyers")
    st.caption("Upload flyer screenshots to find the latest deals. "
               "Use cropped sections (4-8 items) for best results.")

    store_name = st.selectbox(
        "Which store is this flyer from?",
        ["Food Basics", "No Frills", "Walmart", "FreshCo", "Loblaws", "Other"]
    )

    uploaded_flyer = st.file_uploader(
        "Upload flyer image",
        type=["png", "jpg", "jpeg"],
        help="Crop to show 4-8 products clearly"
    )

    if uploaded_flyer is not None:
        st.image(uploaded_flyer, caption=f"{store_name} flyer", use_container_width=True)

        if st.button("Parse Flyer with AI", type="primary"):
            # Save uploaded file temporarily
            temp_path = os.path.join("data", "flyers", uploaded_flyer.name)
            os.makedirs(os.path.join("data", "flyers"), exist_ok=True)

            with open(temp_path, "wb") as f:
                f.write(uploaded_flyer.getbuffer())

            with st.spinner("AI is reading the flyer..."):
                deals = parse_flyer_image(temp_path, store_name)

            if deals:
                st.success(f"Found {len(deals)} deals!")

                # Show extracted deals
                for deal in deals:
                    brand = deal.get('brand', '')
                    brand_str = f"({brand}) " if brand else ""
                    st.write(f"• **{brand_str}{deal['product_name']}** — "
                             f"${deal['sale_price']:.2f}/{deal.get('unit', 'each')}")

                if st.button("Save deals to database"):
                    save_deals_to_database(deals, store_name, uploaded_flyer.name)
                    st.success("Saved!")
                    st.rerun()
            else:
                st.error("Couldn't extract deals. Try a clearer/closer image.")

    st.divider()

    # Show current flyer deals in database
    flyer_deals = get_flyer_deals()
    if not flyer_deals.empty:
        st.subheader("Active Flyer Deals")
        st.caption(f"{len(flyer_deals)} deals loaded")
        for _, deal in flyer_deals.iterrows():
            st.write(f"• **{deal['product_name']}** @ {deal['store']} — ${deal['sale_price']:.2f}")


# ---------------------------------------------------------------------------
# MAIN CONTENT - Two input modes
# ---------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["Grocery List", "Meal Planner", "Browse Database"])


# ---- TAB 1: Direct Grocery List Input ----
with tab1:
    st.subheader("Enter your grocery list")
    st.caption("Type one item per line, or separate with commas. "
               "AI will match your items to products in our database.")

    grocery_input = st.text_area(
        "What do you need to buy?",
        placeholder="milk\neggs\nchicken breast\nbread\nbananas\ncheese\npasta sauce",
        height=200
    )

    if st.button("Compare Prices", type="primary", key="compare_list"):
        if not grocery_input.strip():
            st.warning("Please enter at least one item!")
        else:
            # Parse input - handle both newlines and commas
            items = [
                item.strip()
                for item in grocery_input.replace(",", "\n").split("\n")
                if item.strip()
            ]

            with st.spinner(f"Comparing prices for {len(items)} items across 5 stores..."):
                results = compare_prices(items)

            # --- DISPLAY RESULTS ---
            st.divider()

            # Big winner announcement
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Cheapest Store",
                    results["cheapest_store"],
                    f"${results['cheapest_total']:.2f} total"
                )
            with col2:
                st.metric(
                    "You Save",
                    f"${results['potential_savings']:.2f}",
                    f"vs {results['most_expensive_store']}"
                )
            with col3:
                st.metric(
                    "Items Matched",
                    f"{results['items_matched']}/{results['items_total']}",
                )

            # Detailed price table
            st.subheader("Price Breakdown")

            # Build a DataFrame for display
            table_data = []
            for item in results["items"]:
                row = {
                    "Your Item": item["user_input"],
                    "Matched Product": item["matched_product"],
                }
                for store in STORE_COLUMNS.keys():
                    price = item["prices"].get(store, None)
                    if price is not None:
                        row[store] = f"${price:.2f}"
                    else:
                        row[store] = "N/A"
                row["Best Price"] = f"{item['cheapest_store']} (${item['cheapest_price']:.2f})"
                table_data.append(row)

            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Store totals bar chart
            st.subheader("Store Totals")
            totals_df = pd.DataFrame(
                list(results["totals"].items()),
                columns=["Store", "Total"]
            ).sort_values("Total")
            st.bar_chart(totals_df.set_index("Store"))

            # Unmatched items warning
            if results["unmatched"]:
                st.warning(
                    f"Could not find matches for: {', '.join(results['unmatched'])}. "
                    "These items were excluded from the comparison."
                )


# ---- TAB 2: Meal Planner Mode ----
with tab2:
    st.subheader("Describe a meal and we'll find the ingredients")
    st.caption("Tell us what you want to cook and AI will generate a grocery list, "
               "then compare prices automatically.")

    meal_input = st.text_input(
        "What do you want to make?",
        placeholder="e.g., Tacos for 4 people, Chicken stir fry, Pasta night"
    )

    if st.button("Plan & Compare", type="primary", key="compare_meal"):
        if not meal_input.strip():
            st.warning("Please describe a meal!")
        else:
            with st.spinner("AI is generating your grocery list..."):
                ingredients = expand_meal_to_ingredients(meal_input)

            if ingredients:
                st.success(f"Generated {len(ingredients)} ingredients for: {meal_input}")

                # Show the generated list
                st.write("**Shopping list:**")
                for ing in ingredients:
                    st.write(f"• {ing}")

                st.divider()

                with st.spinner("Comparing prices..."):
                    results = compare_prices(ingredients)

                # Same display as Tab 1
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "Cheapest Store",
                        results["cheapest_store"],
                        f"${results['cheapest_total']:.2f} total"
                    )
                with col2:
                    st.metric(
                        "You Save",
                        f"${results['potential_savings']:.2f}",
                        f"vs {results['most_expensive_store']}"
                    )
                with col3:
                    st.metric(
                        "Items Matched",
                        f"{results['items_matched']}/{results['items_total']}",
                    )

                # Price table
                table_data = []
                for item in results["items"]:
                    row = {
                        "Ingredient": item["user_input"],
                        "Matched Product": item["matched_product"],
                    }
                    for store in STORE_COLUMNS.keys():
                        price = item["prices"].get(store, None)
                        row[store] = f"${price:.2f}" if price else "N/A"
                    row["Best"] = f"{item['cheapest_store']} (${item['cheapest_price']:.2f})"
                    table_data.append(row)

                st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

                st.bar_chart(
                    pd.DataFrame(
                        list(results["totals"].items()),
                        columns=["Store", "Total"]
                    ).sort_values("Total").set_index("Store")
                )
            else:
                st.error("Could not generate ingredients. Try a simpler meal description.")


# ---- TAB 3: Browse Database ----
with tab3:
    st.subheader("Browse all products in database")

    products_df = get_all_products()

    if products_df.empty:
        st.warning("No products in database. Run `python database.py` first!")
    else:
        # Category filter
        categories = ["All"] + sorted(products_df["category"].unique().tolist())
        selected_category = st.selectbox("Filter by category", categories)

        if selected_category != "All":
            display_df = products_df[products_df["category"] == selected_category]
        else:
            display_df = products_df

        # Search filter
        search = st.text_input("Search products", placeholder="e.g., chicken, milk")
        if search:
            display_df = display_df[
                display_df["product_name"].str.contains(search, case=False, na=False)
            ]

        # Display columns we care about
        display_cols = ["product_name", "brand", "category", "unit",
                        "no_frills_price", "food_basics_price",
                        "walmart_price", "freshco_price", "loblaws_price"]
        st.dataframe(
            display_df[display_cols].sort_values("product_name"),
            use_container_width=True,
            hide_index=True,
            column_config={
                "product_name": "Product",
                "brand": "Brand",
                "category": "Category",
                "unit": "Unit",
                "no_frills_price": st.column_config.NumberColumn("No Frills", format="$%.2f"),
                "food_basics_price": st.column_config.NumberColumn("Food Basics", format="$%.2f"),
                "walmart_price": st.column_config.NumberColumn("Walmart", format="$%.2f"),
                "freshco_price": st.column_config.NumberColumn("FreshCo", format="$%.2f"),
                "loblaws_price": st.column_config.NumberColumn("Loblaws", format="$%.2f"),
            }
        )
        st.caption(f"Showing {len(display_df)} of {len(products_df)} products")


# ---------------------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------------------
st.divider()
st.caption("Built at CXC AI Hackathon 2026 | Powered by Gemini AI")

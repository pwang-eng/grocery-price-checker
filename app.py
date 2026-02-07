"""
app.py - The Streamlit web frontend for Grocery Goose.

HOW TO RUN:
    streamlit run app.py

This will open a browser window with the app.
Make sure you've run `python database.py` first to set up the database!
"""

import streamlit as st
import pandas as pd
from PIL import Image
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
# CUSTOM CSS
# ---------------------------------------------------------------------------
def load_css():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        div[data-testid="stMetric"] {
            background-color: #16352A;
            border-radius: 12px;
            padding: 15px;
        }

        button[kind="primary"] {
            border-radius: 10px;
            padding: 0.6em 1.2em;
        }

        section[data-testid="stSidebar"] {
            background-color: #10251C;
        }
        </style>
    """, unsafe_allow_html=True)


load_css()


# ---------------------------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------------------------
if "db_initialized" not in st.session_state:
    setup_database()
    if get_all_products().empty:
        load_seed_data()
    st.session_state.db_initialized = True


# ---------------------------------------------------------------------------
# HEADER + LOGO (LOGO LEFT, BIG TITLE)
# ---------------------------------------------------------------------------
col_logo, col_title = st.columns([1, 5])

with col_logo:
    logo = Image.open("branding/Big Logo.png")
    st.image(logo, width=120)

with col_title:
    st.markdown(
        """
        <h1 style="margin-bottom: 0; font-size: 3rem;">
            Grocery Goose
        </h1>
        <p style="margin-top: 0; font-size: 1.1rem; opacity: 0.85;">
            Find the cheapest groceries across local stores using AI
        </p>
        """,
        unsafe_allow_html=True
    )

st.divider()


# ---------------------------------------------------------------------------
# SIDEBAR - Flyer Upload
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Upload Store Flyers")
    st.caption(
        "Upload flyer screenshots to find the latest deals. "
        "Use cropped sections (4–8 items) for best results."
    )

    store_name = st.selectbox(
        "Which store is this flyer from?",
        ["Food Basics", "No Frills", "Walmart", "FreshCo", "Loblaws", "Other"]
    )

    uploaded_flyer = st.file_uploader(
        "Upload flyer image",
        type=["png", "jpg", "jpeg"],
        help="Crop to show 4–8 products clearly"
    )

    if uploaded_flyer is not None:
        st.image(uploaded_flyer, caption=f"{store_name} flyer", use_container_width=True)

        if st.button("Parse Flyer with AI", type="primary"):
            temp_path = os.path.join("data", "flyers", uploaded_flyer.name)
            os.makedirs(os.path.join("data", "flyers"), exist_ok=True)

            with open(temp_path, "wb") as f:
                f.write(uploaded_flyer.getbuffer())

            with st.spinner("AI is reading the flyer..."):
                deals = parse_flyer_image(temp_path, store_name)

            if deals:
                st.success(f"Found {len(deals)} deals!")

                for deal in deals:
                    brand = deal.get("brand", "")
                    brand_str = f"({brand}) " if brand else ""
                    st.write(
                        f"• **{brand_str}{deal['product_name']}** — "
                        f"${deal['sale_price']:.2f}/{deal.get('unit', 'each')}"
                    )

                if st.button("Save deals to database"):
                    save_deals_to_database(deals, store_name, uploaded_flyer.name)
                    st.success("Saved!")
                    st.rerun()
            else:
                st.error("Couldn't extract deals. Try a clearer image.")

    st.divider()

    flyer_deals = get_flyer_deals()
    if not flyer_deals.empty:
        st.subheader("Active Flyer Deals")
        st.caption(f"{len(flyer_deals)} deals loaded")
        for _, deal in flyer_deals.iterrows():
            st.write(
                f"• **{deal['product_name']}** @ {deal['store']} — "
                f"${deal['sale_price']:.2f}"
            )


# ---------------------------------------------------------------------------
# MAIN CONTENT
# ---------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["Grocery List", "Meal Planner", "Browse Database"])


# ---- TAB 1: Grocery List ----
with tab1:
    st.subheader("Enter your grocery list")
    st.caption("One item per line or comma-separated.")

    grocery_input = st.text_area(
        "What do you need to buy?",
        placeholder="milk\neggs\nchicken breast\nbread\nbananas",
        height=200
    )

    if st.button("Find Cheapest Store", type="primary", key="compare_list"):
        if not grocery_input.strip():
            st.warning("Please enter at least one item!")
        else:
            items = [
                item.strip()
                for item in grocery_input.replace(",", "\n").split("\n")
                if item.strip()
            ]

            with st.spinner("Comparing prices..."):
                results = compare_prices(items)

            st.divider()

            col1, col2, col3 = st.columns(3)
            col1.metric("Cheapest Store", results["cheapest_store"],
                        f"${results['cheapest_total']:.2f}")
            col2.metric("You Save",
                        f"${results['potential_savings']:.2f}",
                        f"vs {results['most_expensive_store']}")
            col3.metric("Items Matched",
                        f"{results['items_matched']}/{results['items_total']}")

            st.subheader("Price Breakdown")

            table_data = []
            for item in results["items"]:
                row = {
                    "Item": item["user_input"],
                    "Matched Product": item["matched_product"],
                }
                for store in STORE_COLUMNS:
                    price = item["prices"].get(store)
                    row[store] = f"${price:.2f}" if price else "N/A"
                row["Best"] = f"{item['cheapest_store']} (${item['cheapest_price']:.2f})"
                table_data.append(row)

            st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

            totals_df = pd.DataFrame(
                results["totals"].items(), columns=["Store", "Total"]
            ).sort_values("Total")

            st.bar_chart(totals_df.set_index("Store"))


# ---- TAB 2: Meal Planner ----
with tab2:
    st.subheader("Describe a meal")
    meal_input = st.text_input(
        "What do you want to cook?",
        placeholder="Chicken stir fry, Tacos for 4 people"
    )

    if st.button("Cook Smarter", type="primary", key="compare_meal"):
        if not meal_input.strip():
            st.warning("Please describe a meal!")
        else:
            with st.spinner("Generating ingredients..."):
                ingredients = expand_meal_to_ingredients(meal_input)

            if ingredients:
                st.success(f"Generated {len(ingredients)} ingredients")
                for ing in ingredients:
                    st.write(f"• {ing}")

                with st.spinner("Comparing prices..."):
                    results = compare_prices(ingredients)

                st.bar_chart(
                    pd.DataFrame(
                        results["totals"].items(),
                        columns=["Store", "Total"]
                    ).sort_values("Total").set_index("Store")
                )
            else:
                st.error("Could not generate ingredients.")


# ---- TAB 3: Browse Database ----
with tab3:
    st.subheader("All Products")

    products_df = get_all_products()
    if products_df.empty:
        st.warning("Database is empty.")
    else:
        categories = ["All"] + sorted(products_df["category"].unique())
        selected = st.selectbox("Category", categories)

        if selected != "All":
            products_df = products_df[products_df["category"] == selected]

        search = st.text_input("Search")
        if search:
            products_df = products_df[
                products_df["product_name"].str.contains(search, case=False, na=False)
            ]

        st.dataframe(products_df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------------------
st.divider()
st.caption("Built at CXC AI Hackathon 2026")

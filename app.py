"""
app.py - The Streamlit web frontend for Goose Grocer.

HOW TO RUN:
    python -m streamlit run app.py
"""

import streamlit as st
import pandas as pd
from database import setup_database, load_seed_data, get_all_products, get_flyer_deals, save_recipe, get_saved_recipes
from comparison import compare_prices, expand_meal_to_ingredients, STORE_COLUMNS
from flyer_parser import parse_flyer_image, save_deals_to_database
import os

# Brand Colors
GOOSE_GREEN = "#2E7D32"

# Store color mapping
STORE_COLORS = {
    "No Frills": "#FFD700",
    "Food Basics": "#FF6B35",
    "Walmart": "#0071CE",
    "FreshCo": "#00A651",
    "Loblaws": "#D32F2F"
}

# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Goose Grocer",
    page_icon="🪿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------------------------
if "db_initialized" not in st.session_state:
    setup_database()
    if get_all_products().empty:
        load_seed_data()
    st.session_state.db_initialized = True

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Scan Store Flyers")
    st.caption("Upload flyer screenshots to update our database.")

    store_name = st.selectbox(
        "Select Store",
        ["Food Basics", "No Frills", "Walmart", "FreshCo", "Loblaws", "Other"]
    )

    uploaded_flyer = st.file_uploader(
        "Upload Image",
        type=["png", "jpg", "jpeg"]
    )

    if uploaded_flyer is not None:
        st.image(uploaded_flyer, caption=f"{store_name} flyer", use_container_width=True)

        if st.button("Analyze Flyer", type="primary", key="analyze_flyer"):
            temp_path = os.path.join("data", "flyers", uploaded_flyer.name)
            os.makedirs(os.path.join("data", "flyers"), exist_ok=True)

            with open(temp_path, "wb") as f:
                f.write(uploaded_flyer.getbuffer())

            with st.spinner("Analyzing data..."):
                deals = parse_flyer_image(temp_path, store_name)

            if deals:
                st.success(f"Identified {len(deals)} items.")
                for deal in deals:
                    brand = deal.get('brand', '')
                    brand_str = f"({brand}) " if brand else ""
                    st.write(f"• {brand_str}{deal['product_name']} — ${deal['sale_price']:.2f}")

                if st.button("Save to Database", key="save_flyer"):
                    save_deals_to_database(deals, store_name, uploaded_flyer.name)
                    st.success("Data saved.")
                    st.rerun()
            else:
                st.error("Could not extract data.")

    st.divider()
    flyer_deals = get_flyer_deals()
    if not flyer_deals.empty:
        st.subheader("Active Deals")
        st.caption(f"{len(flyer_deals)} items loaded")
        for _, deal in flyer_deals.iterrows():
            st.write(f"• {deal['product_name']} @ {deal['store']} — ${deal['sale_price']:.2f}")

# ---------------------------------------------------------------------------
# MAIN NAVIGATION
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Home",
    "Grocery List",
    "Meal Planner",
    "Weekly Schedule",
    "Bulk Prep",
    "Database",
    "Recipe Book"
])

# ---- TAB 1: HOME / ABOUT ----
with tab1:

    # Optional vertical centering for columns
    st.markdown("""
    <style>
    [data-testid="column"] {
        display: flex;
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

    # Logo + Title Row
    col_logo, col_title = st.columns([1, 5])

    with col_logo:
        st.image("branding/Big Logo.png", width=250)

    with col_title:
        st.markdown(f"""
            <h1 style='font-size: 80px; margin-bottom: 0;'>
                <span style='color: white;'>Goose</span>
                <span style='color: {GOOSE_GREEN};'>Grocer</span>
            </h1>

            <h3 style='font-weight: 300; margin-top: 10px; font-style: italic; opacity: 0.8;'>
                <span style='color: white;'>Stop spending.</span>
                <span style='color: {GOOSE_GREEN};'>Start saving.</span>
            </h3>
        """, unsafe_allow_html=True)

    st.divider()

    # Mission + Insight
    col_mission, col_why = st.columns([2, 1])

    with col_mission:
        st.markdown("""
        ### Our Mission

        **Grocery shopping takes time, and time is money.**

        Goose Grocer streamlines the grocery experience, making buying local, 
        affordable groceries as efficient as ordering delivery.

        Our platform instantly compares prices across major retailers to 
        optimize your spending without the manual effort.
        """)

    with col_why:
        st.info(
            "**Insight:** Users save an average of 30% on weekly grocery bills "
            "through automated price comparison."
        )

    st.divider()

    # Features Section
    st.markdown("### Platform Features")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"<h4 style='color:{GOOSE_GREEN}'>Smart List</h4>",
            unsafe_allow_html=True
        )
        st.caption("Automated price matching for your custom grocery list.")

    with c2:
        st.markdown(
            f"<h4 style='color:{GOOSE_GREEN}'>Meal Planner</h4>",
            unsafe_allow_html=True
        )
        st.caption("Generate ingredient lists from simple meal descriptions.")

    with c3:
        st.markdown(
            f"<h4 style='color:{GOOSE_GREEN}'>Weekly Schedule</h4>",
            unsafe_allow_html=True
        )
        st.caption("Full-week meal planning and consolidated shopping lists.")

    with c4:
        st.markdown(
            f"<h4 style='color:{GOOSE_GREEN}'>Bulk Prep</h4>",
            unsafe_allow_html=True
        )
        st.caption("Cost analysis for batch cooking and meal preparation.")


# ---- TAB 2: GROCERY LIST ----
with tab2:
    st.subheader("Smart Grocery List")
    st.caption("Enter your items below for instant price comparison.")

    # Initialize Session State
    if 'results_tab2' not in st.session_state:
        st.session_state.results_tab2 = None

    st.write("Examples:")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Everyday Essentials", key="example_essentials"):
            st.session_state['grocery_input'] = "milk\neggs\nbread\nbutter\ncheese"
            st.rerun()
    with col2:
        if st.button("Pasta Dinner", key="example_pasta"):
            st.session_state['grocery_input'] = "pasta\nbacon\neggs\nparmesan cheese\nheavy cream"
            st.rerun()
    with col3:
        if st.button("Salad Ingredients", key="example_salad"):
            st.session_state['grocery_input'] = "lettuce\ntomatoes\ncucumber\ncarrots\nolive oil"
            st.rerun()

    grocery_input = st.text_area(
        "Shopping List",
        value=st.session_state.get('grocery_input', ''),
        height=200
    )

    if st.button("Compare Prices", type="primary", key="compare_list"):
        if not grocery_input.strip():
            st.warning("Please enter at least one item.")
        else:
            items = [item.strip() for item in grocery_input.replace(",", "\n").split("\n") if item.strip()]

            with st.spinner(f"Analyzing prices for {len(items)} items..."):
                st.session_state.results_tab2 = compare_prices(items)

    if st.session_state.results_tab2:
        results = st.session_state.results_tab2
        st.divider()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("### Best Value Store")
            cheapest = results["cheapest_store"]
            st.markdown(f"<h2 style='color: {GOOSE_GREEN};'>{cheapest}</h2>", unsafe_allow_html=True)
            st.write(f"Total: ${results['cheapest_total']:.2f}")
        with col2:
            st.metric("Estimated Savings", f"${results['potential_savings']:.2f}", f"vs {results['most_expensive_store']}")
        with col3:
            st.metric("Items Matched", f"{results['items_matched']}/{results['items_total']}")

        st.dataframe(pd.DataFrame([{
            "Item": i["user_input"],
            "Product": i["matched_product"],
            "Best Price": f"{i['cheapest_store']} (${i['cheapest_price']:.2f})"
        } for i in results["items"]]), use_container_width=True, hide_index=True)

        # Download Button
        list_text = f"Goose Grocer Shopping List\nStore: {results['cheapest_store']}\nTotal: ${results['cheapest_total']:.2f}\n\nItems:\n"
        for item in results["items"]:
            list_text += f"- [ ] {item['matched_product']} (${item['cheapest_price']:.2f})\n"

        st.download_button("Download List", list_text, "grocery_list.txt")

# ---- TAB 3: MEAL PLANNER ----
with tab3:
    st.subheader("Meal Planner")
    st.caption("Describe a meal to generate a shopping list and cost estimate.")

    # Session State
    if 'results_tab3' not in st.session_state:
        st.session_state.results_tab3 = None
    if 'ingredients_tab3' not in st.session_state:
        st.session_state.ingredients_tab3 = None
    if 'meal_name_tab3' not in st.session_state:
        st.session_state.meal_name_tab3 = ""

    meal_input = st.text_input("Meal Description", placeholder="e.g., Tacos for 4 people", key="meal_input")

    if st.button("Generate Plan", type="primary", key="generate_meal_plan"):
        if meal_input:
            with st.spinner("Generating ingredient list..."):
                ingredients = expand_meal_to_ingredients(meal_input)
                st.session_state.ingredients_tab3 = ingredients
                st.session_state.meal_name_tab3 = meal_input

            if ingredients:
                with st.spinner("Calculating costs..."):
                    st.session_state.results_tab3 = compare_prices(ingredients)
            else:
                st.error("Could not interpret meal description.")
        else:
            st.warning("Please enter a description.")

    if st.session_state.results_tab3:
        results = st.session_state.results_tab3
        ingredients = st.session_state.ingredients_tab3

        st.success(f"List generated for: {st.session_state.meal_name_tab3}")
        for ing in ingredients:
            st.write(f"• {ing}")

        st.divider()

        st.markdown(
            f"### Recommended Store: <span style='color:{GOOSE_GREEN}'>{results['cheapest_store']}</span>",
            unsafe_allow_html=True
        )
        st.write(f"Total Cost: ${results['cheapest_total']:.2f}")
        st.caption(f"Savings: ${results['potential_savings']:.2f} vs highest price.")

        col_dl, col_save = st.columns(2)

        with col_dl:
            # Download Button
            plan_text = f"Goose Grocer Meal Plan: {st.session_state.meal_name_tab3}\nStore: {results['cheapest_store']}\nEst. Cost: ${results['cheapest_total']:.2f}\n\nIngredients:\n"
            for ing in ingredients:
                plan_text += f"- [ ] {ing}\n"

            st.download_button("Download Text File", plan_text, "meal_plan.txt")

        with col_save:
            # SAVE TO DB BUTTON
            if st.button("Save to Recipe Book", type="secondary"):
                save_recipe(
                    st.session_state.meal_name_tab3,
                    ingredients,
                    instructions="AI Generated Instructions would go here."
                )
                st.toast(f"Saved '{st.session_state.meal_name_tab3}' to Recipe Book!")

# ---- TAB 4: WEEKLY SCHEDULE ----
with tab4:
    st.subheader("Weekly Schedule")
    st.caption("Plan meals for the week to generate a master shopping list.")

    # CSS for styled inputs
    st.markdown("""
        <style>
        .weekly-input input {
            height: 100px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .weekly-input label { font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    mon_col, tue_col, wed_col, thu_col, fri_col, sat_col, sun_col = st.columns(7)

    def styled_input(label, key, col):
        with col:
            st.markdown(f"<div class='weekly-input'><label>{label}</label></div>", unsafe_allow_html=True)
            return st.text_area("", key=key, height=100)

    mon_input = styled_input("Mon", "tab4_mon", mon_col)
    tue_input = styled_input("Tue", "tab4_tue", tue_col)
    wed_input = styled_input("Wed", "tab4_wed", wed_col)
    thu_input = styled_input("Thu", "tab4_thu", thu_col)
    fri_input = styled_input("Fri", "tab4_fri", fri_col)
    sat_input = styled_input("Sat", "tab4_sat", sat_col)
    sun_input = styled_input("Sun", "tab4_sun", sun_col)

    st.divider()

    if 'results_tab4' not in st.session_state:
        st.session_state.results_tab4 = None
    if 'unique_ings_tab4' not in st.session_state:
        st.session_state.unique_ings_tab4 = None

    if st.button("Generate Master List", type="primary", key="generate_weekly_list"):
        meals = [x for x in [mon_input, tue_input, wed_input, thu_input, fri_input, sat_input, sun_input] if x.strip()]

        if meals:
            with st.spinner("Processing weekly plan..."):
                all_ings = []
                for meal in meals:
                    all_ings.extend(expand_meal_to_ingredients(meal))

                unique_ings = list(set(all_ings))
                st.session_state.unique_ings_tab4 = unique_ings
                st.session_state.results_tab4 = compare_prices(unique_ings)
        else:
            st.warning("Enter at least one meal.")

    if st.session_state.results_tab4:
        results = st.session_state.results_tab4
        unique_ings = st.session_state.unique_ings_tab4

        st.success(f"Master list created: {len(unique_ings)} items.")
        with st.expander("View Shopping List", expanded=True):
            for ing in unique_ings:
                st.write(f"• {ing}")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"### Best Value: <span style='color:{GOOSE_GREEN}'>{results['cheapest_store']}</span>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='color: {GOOSE_GREEN}'>${results['cheapest_total']:.2f}</h2>", unsafe_allow_html=True)
        with col2:
            st.metric("Total Savings", f"${results['potential_savings']:.2f}")

        # Download Button
        weekly_text = f"Goose Grocer Weekly Plan\nStore: {results['cheapest_store']}\nTotal: ${results['cheapest_total']:.2f}\n\nShopping List:\n"
        for ing in unique_ings:
            weekly_text += f"- [ ] {ing}\n"

        st.download_button("Download Weekly List", weekly_text, "weekly_list.txt")


# ---- TAB 5: BULK MEAL PREP ----
with tab5:
    st.subheader("Bulk Meal Prep")
    st.caption("Cost analysis for batch cooking and meal preparation.")

    prep_type = st.radio("Prep Mode:", ["Gym Meal Prep", "Family Batch Cooking"], horizontal=True)
    st.divider()

    if prep_type == "Gym Meal Prep":
        st.write("High-protein meal plan generation.")
        days = st.slider("Number of Days", 3, 7, 5)
        meals_per_day = st.slider("Meals per Day", 1, 5, 3)

        if st.button("Generate Plan", type="primary", key="generate_bulk_gym"):
            base_ings = ["chicken breast", "brown rice", "broccoli", "eggs", "oats",
                         "protein powder", "sweet potato", "greek yogurt", "spinach"]

            with st.spinner("Calculating costs..."):
                results = compare_prices(base_ings)

            st.success(f"Plan generated for {days * meals_per_day} meals.")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Cost", f"${results['cheapest_total']:.2f}")
            with c2:
                cost_per_day = results['cheapest_total'] / days
                st.metric("Cost / Day", f"${cost_per_day:.2f}")
            with c3:
                cost_per_meal = results['cheapest_total'] / (days * meals_per_day)
                st.metric("Cost / Meal", f"${cost_per_meal:.2f}")

            st.markdown(f"### Recommended Store: <span style='color:{GOOSE_GREEN}'>{results['cheapest_store']}</span>", unsafe_allow_html=True)

            # Download
            gym_text = f"Goose Grocer Gym Prep\nTarget: {days} days, {meals_per_day} meals/day\nStore: {results['cheapest_store']}\nTotal: ${results['cheapest_total']:.2f}\n\nList:\n"
            for ing in base_ings:
                gym_text += f"- [ ] {ing}\n"
            st.download_button("Download Prep List", gym_text, "gym_prep.txt")

    else:
        # Session State for Batch
        if 'results_tab5' not in st.session_state:
            st.session_state.results_tab5 = None
        if 'ingredients_tab5' not in st.session_state:
            st.session_state.ingredients_tab5 = None
        if 'recipe_tab5' not in st.session_state:
            st.session_state.recipe_tab5 = ""

        st.write("Batch cooking analysis.")
        recipe = st.text_input("Recipe Name", placeholder="e.g., Vegetarian Chili", key="bulk_recipe")
        servings = st.number_input("Servings", 4, 50, 8, key="bulk_servings")

        if st.button("Analyze Cost", key="analyze_bulk"):
            if recipe:
                with st.spinner("Analyzing ingredients..."):
                    ings = expand_meal_to_ingredients(f"{recipe} for {servings} servings")
                    st.session_state.ingredients_tab5 = ings
                    st.session_state.recipe_tab5 = recipe
                    st.session_state.results_tab5 = compare_prices(ings)
            else:
                st.warning("Please enter a recipe name.")

        if st.session_state.results_tab5:
            results = st.session_state.results_tab5
            ings = st.session_state.ingredients_tab5

            st.success(f"Analysis complete for {servings} servings.")
            st.write("**Ingredients:**")
            st.write(", ".join(ings))

            st.divider()
            st.metric("Total Batch Cost", f"${results['cheapest_total']:.2f}")
            st.caption(f"Cost per serving: ${results['cheapest_total']/servings:.2f}")
            st.markdown(f"### Best Price at <span style='color:{GOOSE_GREEN}'>{results['cheapest_store']}</span>", unsafe_allow_html=True)

            col_dl, col_save = st.columns(2)
            with col_dl:
                # Download
                batch_text = f"Goose Grocer Batch Cook: {st.session_state.recipe_tab5}\nServings: {servings}\nStore: {results['cheapest_store']}\nTotal: ${results['cheapest_total']:.2f}\n\nIngredients:\n"
                for ing in ings:
                    batch_text += f"- [ ] {ing}\n"
                st.download_button("Download Text File", batch_text, "batch_recipe.txt")

            with col_save:
                # SAVE TO DB
                if st.button("Save to Recipe Book", key="save_batch"):
                    save_recipe(
                        st.session_state.recipe_tab5,
                        ings,
                        f"Batch cooking instructions for {servings} servings."
                    )
                    st.toast(f"Saved '{st.session_state.recipe_tab5}' to Recipe Book!")

# ---- TAB 6: BROWSE DB ----
with tab6:
    st.subheader("Product Database")
    products_df = get_all_products()
    if not products_df.empty:
        search = st.text_input("Search Database", placeholder="Product name...", key="db_search")
        if search:
            products_df = products_df[products_df["product_name"].str.contains(search, case=False)]

        # Display all store columns
        st.dataframe(
            products_df[[
                "product_name",
                "category",
                "no_frills_price",
                "food_basics_price",
                "walmart_price",
                "freshco_price",
                "loblaws_price"
            ]],
            use_container_width=True
        )

# ---- TAB 7: RECIPE BOOK ----
with tab7:
    st.subheader("My Saved Recipes")

    saved_df = get_saved_recipes()

    if saved_df.empty:
        st.info("No recipes saved yet. Go to the Meal Planner or Bulk Prep tab to generate and save some!")
    else:
        st.write(f"You have {len(saved_df)} saved recipes.")

        for index, row in saved_df.iterrows():
            with st.expander(f"{row['title']} (Saved: {row['created_at']})"):
                st.write("**Ingredients:**")
                st.text(row['ingredients'])
                if row['instructions']:
                    st.write("**Instructions:**")
                    st.write(row['instructions'])

                # Re-calculate button
                if st.button(f"Check Current Prices for '{row['title']}'", key=f"recheck_{row['id']}"):
                    # Logic to re-run price comparison
                    ings_list = row['ingredients'].split('\n')
                    with st.spinner("Checking fresh prices..."):
                        results = compare_prices(ings_list)
                    st.success(f"Best Price Now: ${results['cheapest_total']:.2f} at {results['cheapest_store']}")


# ---------------------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------------------
st.divider()
st.caption("© 2026 Goose Grocer. All rights reserved.")

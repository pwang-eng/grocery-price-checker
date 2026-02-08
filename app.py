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
    page_icon="🦆",
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

    st.write("Quick List Examples:")

    # CSS with different colors for light items vs full meals
    st.markdown("""
        <style>
        /* Base style for all preset buttons */
        div[data-testid="stHorizontalBlock"] .stButton > button {
            background-color: transparent;
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
        }

        /* Light green hover - buttons 1, 2, 5, 6, 7 (light items) */
        div[data-testid="stHorizontalBlock"] > div:nth-child(1) .stButton > button:hover,
        div[data-testid="stHorizontalBlock"] > div:nth-child(2) .stButton:nth-child(2) > button:hover,
        div[data-testid="stHorizontalBlock"] > div:nth-child(3) .stButton > button:hover,
        div[data-testid="stHorizontalBlock"] > div:nth-child(4) .stButton:nth-child(1) > button:hover {
            background-color: #81C784 !important;
            border-color: #81C784 !important;
        }

        /* Dark green hover - buttons 3, 4, 8 (full meals) */
        div[data-testid="stHorizontalBlock"] > div:nth-child(2) .stButton:nth-child(1) > button:hover,
        div[data-testid="stHorizontalBlock"] > div:nth-child(2) .stButton:nth-child(3) > button:hover,
        div[data-testid="stHorizontalBlock"] > div:nth-child(4) .stButton:nth-child(2) > button:hover {
            background-color: #1B5E20 !important;
            border-color: #1B5E20 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Everyday Essentials", key="example_essentials"):
            st.session_state['grocery_input'] = "milk\neggs\nbread\nbutter\ncheese"
            st.rerun()
        if st.button("Breakfast Staples", key="example_breakfast"):
            st.session_state['grocery_input'] = "eggs\nbacon\nbread\norange juice\ncoffee\nbutter"
            st.rerun()

    with col2:
        if st.button("Pasta Dinner", key="example_pasta"):
            st.session_state['grocery_input'] = "pasta\nbacon\neggs\nparmesan cheese\nheavy cream"
            st.rerun()
        if st.button("Taco Night", key="example_taco"):
            st.session_state['grocery_input'] = "ground beef\ntortillas\nlettuce\ntomatoes\ncheese\nsour cream"
            st.rerun()

    with col3:
        if st.button("Salad Ingredients", key="example_salad"):
            st.session_state['grocery_input'] = "lettuce\ntomatoes\ncucumber\ncarrots\nolive oil"
            st.rerun()
        if st.button("Sandwich Fixings", key="example_sandwich"):
            st.session_state['grocery_input'] = "bread\nham\nturkey\ncheese\nlettuce\nmayo"
            st.rerun()

    with col4:
        if st.button("Smoothie Supplies", key="example_smoothie"):
            st.session_state['grocery_input'] = "bananas\nstrawberries\nyogurt\nspinach\nprotein powder"
            st.rerun()
        if st.button("BBQ Essentials", key="example_bbq"):
            st.session_state['grocery_input'] = "chicken breast\nground beef\nhotdogs\nbuns\nketchup\nmustard"
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
            st.metric("Estimated Savings", f"${results['potential_savings']:.2f}",
                      f"vs {results['most_expensive_store']}")
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

    # -----------------------------------------------------------------------
    # 1. RECIPE INSPIRATION / PRESETS
    # -----------------------------------------------------------------------
    with st.expander("Browse Meals by Cuisine", expanded=False):

        # 1. DATABASE
        MEAL_DB = {
            "East Asian": ["Chicken Stir Fry", "Beef and Broccoli", "Miso Ramen", "Teriyaki Chicken Bowl", "Bibimbap"],
            "South Asian": ["Butter Chicken", "Chana Masala (Chickpea Curry)", "Lentil Daal", "Chicken Biryani",
                            "Aloo Gobi"],
            "Italian": ["Spaghetti Carbonara", "Chicken Parmesan", "Vegetarian Lasagna", "Fettuccine Alfredo",
                        "Caprese Salad"],
            "Mexican": ["Beef Tacos", "Chicken Enchiladas", "Burrito Bowls", "Huevos Rancheros", "Steak Fajitas"],
            "Mediterranean": ["Chicken Shawarma Salad", "Falafel Wrap", "Greek Salad with Chicken",
                              "Hummus & Pita Plate", "Shakshuka"],
            "American / Western": ["Cheeseburger & Fries", "Grilled Cheese & Tomato Soup", "Cobb Salad",
                                   "Macaroni and Cheese", "Roast Chicken & Veggies"],
            "Breakfast": ["Scrambled Eggs & Bacon", "Pancakes with Syrup", "Oatmeal with Berries", "Avocado Toast",
                          "Spinach Omelette"],
            "Snacks": ["Apple & Peanut Butter", "Greek Yogurt Parfait", "Hummus & Carrots", "Trail Mix",
                       "Protein Shake", "Cheese & Crackers"]
        }

        # 2. SETTINGS
        servings_slider = st.slider("Number of People", min_value=1, max_value=10, value=2)
        st.divider()

        # 3. SELECTION
        col_cuisine, col_meal = st.columns(2)
        with col_cuisine:
            selected_cuisine = st.selectbox("Select Cuisine", options=list(MEAL_DB.keys()))
        with col_meal:
            selected_meal_preset = st.selectbox("Select Meal", options=MEAL_DB[selected_cuisine])

        st.write("")

        # 4. ACTION BUTTONS
        col_use, col_random = st.columns(2)

        with col_use:
            if st.button("Use in Calculator", use_container_width=True, key="use_selected_meal"):
                st.session_state.meal_input = f"{selected_meal_preset} for {servings_slider} people"
                st.rerun()

        with col_random:
            if st.button("Random Meal", use_container_width=True, type="secondary", key="random_meal_btn"):
                import random
                # Pick a random cuisine, then a random meal from that cuisine
                random_cuisine = random.choice(list(MEAL_DB.keys()))
                random_meal = random.choice(MEAL_DB[random_cuisine])
                st.session_state.meal_input = f"{random_meal} for {servings_slider} people"
                st.rerun()

    st.divider()

    # -----------------------------------------------------------------------
    # 2. MAIN CALCULATOR
    # -----------------------------------------------------------------------

    # Session State
    if 'results_tab3' not in st.session_state:
        st.session_state.results_tab3 = None
    if 'ingredients_tab3' not in st.session_state:
        st.session_state.ingredients_tab3 = None
    if 'meal_name_tab3' not in st.session_state:
        st.session_state.meal_name_tab3 = ""

    meal_input = st.text_input(
        "Meal Description (Include number of people!)",
        placeholder="e.g., Tacos for 4 people",
        key="meal_input"
    )

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

    # -----------------------------------------------------------------------
    # 3. RESULTS & SCHEDULING
    # -----------------------------------------------------------------------
    if st.session_state.results_tab3:
        results = st.session_state.results_tab3
        ingredients = st.session_state.ingredients_tab3
        current_meal_name = st.session_state.meal_name_tab3

        st.success(f"List generated for: {current_meal_name}")
        for ing in ingredients:
            st.write(f"• {ing}")

        st.divider()

        # --- COST DISPLAY ---
        st.markdown(
            f"### Recommended Store: <span style='color:{GOOSE_GREEN}'>{results['cheapest_store']}</span>",
            unsafe_allow_html=True
        )
        st.write(f"Total Cost: ${results['cheapest_total']:.2f}")
        st.caption(f"Savings: ${results['potential_savings']:.2f} vs highest price.")

        # --- NEW: ADD TO SCHEDULE SECTION ---
        st.markdown("#### Add to Weekly Plan")

        # Ensure DFs exist
        if 'weekly_meals' not in st.session_state:
            st.session_state.weekly_meals = {d: {k: "" for k in
                                                 ["breakfast", "morning_snack", "lunch", "afternoon_snack", "dinner",
                                                  "evening_snack"]}
                                             for d in
                                             ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
                                              "Sunday"]}
        if 'meal_goals_df' not in st.session_state:
            st.session_state.meal_goals_df = pd.DataFrame(columns=["Meal", "Frequency", "People"])

        c_day, c_slot, c_btn = st.columns([2, 2, 2])

        with c_day:
            target_day = st.selectbox("Day",
                                      ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        with c_slot:
            slot_map = {"Breakfast": "breakfast", "Lunch": "lunch", "Dinner": "dinner", "Snack": "afternoon_snack"}
            target_slot_label = st.selectbox("Slot", list(slot_map.keys()))
        with c_btn:
            st.write("")  # Alignment spacer
            if st.button("Add to Schedule", use_container_width=True, key="add_custom_to_schedule"):

                # 1. Update Grid
                target_key = slot_map[target_slot_label]
                current_val = st.session_state.weekly_meals[target_day][target_key]

                if current_val:
                    st.session_state.weekly_meals[target_day][target_key] = f"{current_val}, {current_meal_name}"
                else:
                    st.session_state.weekly_meals[target_day][target_key] = current_meal_name

                # 2. Update Goals Table
                # Try to extract number of people from string, or default to 2
                import re

                people_match = re.search(r'(\d+)\s*people', current_meal_name.lower())
                people_count = int(people_match.group(1)) if people_match else 2

                new_goal = pd.DataFrame([{
                    "Meal": current_meal_name,
                    "Frequency": 1,
                    "People": people_count
                }])
                st.session_state.meal_goals_df = pd.concat([st.session_state.meal_goals_df, new_goal],
                                                           ignore_index=True)

                st.toast(f"Added to {target_day} schedule & goals list!")

        st.divider()

        col_dl, col_save = st.columns(2)

        with col_dl:
            # Download Button
            plan_text = f"Goose Grocer Meal Plan: {current_meal_name}\nStore: {results['cheapest_store']}\nEst. Cost: ${results['cheapest_total']:.2f}\n\nIngredients:\n"
            for ing in ingredients:
                plan_text += f"- [ ] {ing}\n"

            st.download_button("Download Text File", plan_text, "meal_plan.txt")

        with col_save:
            # SAVE TO DB BUTTON
            if st.button("Save to Recipe Book", type="secondary"):
                save_recipe(
                    current_meal_name,
                    ingredients,
                    "AI Generated Instructions would go here."
                )
                st.toast(f"Saved '{current_meal_name}' to Recipe Book!")

# ---- TAB 4: WEEKLY SCHEDULE ----
with tab4:
    st.subheader("Weekly Meal & Shopping Planner")

    # -----------------------------------------------------------------------
    # 0. QUICK ADD SECTION WITH CHECKBOXES
    # -----------------------------------------------------------------------
    st.markdown("### Quick Add Items")
    st.caption("Check items to automatically add them to your meal plan below.")

    # Define common items
    if 'quick_add_items' not in st.session_state:
        st.session_state.quick_add_items = {
            "Meals": ["Chicken Stir Fry", "Spaghetti Carbonara", "Grilled Salmon", "Beef Tacos", "Veggie Curry"],
            "Breakfast": ["Oatmeal Breakfast", "Scrambled Eggs", "Pancakes", "Smoothie Bowl", "Yogurt Parfait"],
            "Snacks": ["Greek Yogurt", "Apple slices", "Granola bar", "Nuts", "Cheese & crackers"]
        }

    # Initialize checked state
    if 'checked_items' not in st.session_state:
        st.session_state.checked_items = {}

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Meals**")
        for item in st.session_state.quick_add_items["Meals"]:
            checked = st.checkbox(item, key=f"check_meal_{item}")
            if checked and item not in st.session_state.checked_items:
                st.session_state.checked_items[item] = {"Category": "Meal", "Frequency": 2, "People": 2}
            elif not checked and item in st.session_state.checked_items:
                del st.session_state.checked_items[item]

    with col2:
        st.markdown("**Breakfast**")
        for item in st.session_state.quick_add_items["Breakfast"]:
            checked = st.checkbox(item, key=f"check_breakfast_{item}")
            if checked and item not in st.session_state.checked_items:
                st.session_state.checked_items[item] = {"Category": "Meal", "Frequency": 5, "People": 1}
            elif not checked and item in st.session_state.checked_items:
                del st.session_state.checked_items[item]

    with col3:
        st.markdown("**Snacks**")
        for item in st.session_state.quick_add_items["Snacks"]:
            checked = st.checkbox(item, key=f"check_snack_{item}")
            if checked and item not in st.session_state.checked_items:
                st.session_state.checked_items[item] = {"Category": "Snack", "Frequency": 3, "People": 1}
            elif not checked and item in st.session_state.checked_items:
                del st.session_state.checked_items[item]

    st.divider()

    # -----------------------------------------------------------------------
    # 1. MEAL GOALS / QUEUE SECTION
    # -----------------------------------------------------------------------
    st.markdown("### 1. Plan Your Meals")
    st.caption("List the items you want to buy or cook this week.")

    # 1. Initialize DF if not exists
    if 'meal_goals_df' not in st.session_state:
        st.session_state.meal_goals_df = pd.DataFrame(
            [
                {"Category": "Meal", "Item": "Chicken Stir Fry", "Frequency": 2, "People": 2},
                {"Category": "Meal", "Item": "Oatmeal Breakfast", "Frequency": 5, "People": 1},
                {"Category": "Snack", "Item": "Greek Yogurt", "Frequency": 3, "People": 1},
            ]
        )

    # AUTO-SYNC: Add checked items to meal_goals_df
    for item_name, item_props in st.session_state.checked_items.items():
        # Check if item already exists in dataframe
        if item_name not in st.session_state.meal_goals_df["Item"].values:
            new_row = pd.DataFrame([{
                "Category": item_props["Category"],
                "Item": item_name,
                "Frequency": item_props["Frequency"],
                "People": item_props["People"]
            }])
            st.session_state.meal_goals_df = pd.concat(
                [st.session_state.meal_goals_df, new_row],
                ignore_index=True
            )

    # Remove unchecked items from dataframe
    checked_item_names = list(st.session_state.checked_items.keys())
    st.session_state.meal_goals_df = st.session_state.meal_goals_df[
        st.session_state.meal_goals_df["Item"].isin(checked_item_names) |
        ~st.session_state.meal_goals_df["Item"].isin(
            [item for category in st.session_state.quick_add_items.values() for item in category]
        )
    ]

    # 2. Backwards Compatibility
    if "Category" not in st.session_state.meal_goals_df.columns:
        st.session_state.meal_goals_df["Category"] = "Meal"
        if "Meal" in st.session_state.meal_goals_df.columns:
            st.session_state.meal_goals_df.rename(columns={"Meal": "Item"}, inplace=True)

    # 3. GLOBAL OVERRIDE CONTROLS
    col_ovr_label, col_ovr_input, col_ovr_btn = st.columns([2, 1, 2])
    with col_ovr_label:
        st.markdown("**Bulk Actions:**")
    with col_ovr_input:
        override_val = st.selectbox("Servings Override", range(1, 11), key="global_servings_select",
                                    label_visibility="collapsed")
    with col_ovr_btn:
        if st.button(f"Set All items for {override_val} servings"):
            st.session_state.meal_goals_df["People"] = override_val
            st.rerun()

    # 4. DATA EDITOR (with cleanup)

    # Ensure only the correct columns exist - STRICT CLEANUP
    required_columns = ["Category", "Item", "Frequency", "People"]

    # Completely rebuild the dataframe with only what we need
    if not st.session_state.meal_goals_df.empty:
        clean_df = pd.DataFrame()
        for col in required_columns:
            if col in st.session_state.meal_goals_df.columns:
                clean_df[col] = st.session_state.meal_goals_df[col].values
        st.session_state.meal_goals_df = clean_df
    else:
        # If empty, create fresh structure
        st.session_state.meal_goals_df = pd.DataFrame(columns=required_columns)

    edited_goals = st.data_editor(
        st.session_state.meal_goals_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Category": st.column_config.SelectboxColumn(
                "Type",
                options=["Meal", "Snack", "Standalone Item"],
                width="medium",
                required=True
            ),
            "Item": st.column_config.TextColumn(
                "Name",
                width="large",
                required=True
            ),
            "Frequency": st.column_config.NumberColumn(
                "Times/Week",
                min_value=1,
                max_value=21,
                step=1
            ),
            "People": st.column_config.NumberColumn(
                "People",
                min_value=1,
                max_value=20,
                step=1
            )
        },
        key="meal_goals_editor"
    )

    # Update state with clean dataframe
    st.session_state.meal_goals_df = edited_goals[required_columns]

    st.divider()

    # -----------------------------------------------------------------------
    # 2. SCHEDULE GRID
    # -----------------------------------------------------------------------
    st.markdown("### 2. Assign to Schedule")
    st.info("Tip: You do not need to fill every slot. Leave days blank if eating out.")

    if 'weekly_meals' not in st.session_state:
        st.session_state.weekly_meals = {
            day: {
                "breakfast": "", "morning_snack": "", "lunch": "",
                "afternoon_snack": "", "dinner": "", "evening_snack": ""
            } for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        }
    if 'shopping_schedule' not in st.session_state:
        st.session_state.shopping_schedule = None

    # Add servings selector for auto-generate
    col_servings, col_snack_check, col_gen, col_plan, col_clear = st.columns([1, 1.5, 2, 2, 1])

    with col_servings:
        default_servings = st.selectbox("Servings", range(1, 11), index=1, key="auto_gen_servings")

    with col_snack_check:
        always_snack = st.checkbox("Always add snacks", value=False, key="always_add_snacks")

    with col_gen:
        if st.button("Auto-Generate Remaining Suggestions", type="secondary", key="auto_generate_week"):
            with st.spinner("Generating meal suggestions for empty slots..."):
                breakfast_ideas = ["Scrambled Eggs & Toast", "Pancakes", "Oatmeal", "Yogurt Parfait", "Smoothie Bowl"]
                lunch_ideas = ["Chicken Caesar Salad", "Turkey Sandwich", "Pasta", "Veggie Wrap", "Soup"]
                dinner_ideas = ["Spaghetti Carbonara", "Beef Tacos", "Grilled Salmon", "Chicken Stir Fry",
                                "Veggie Curry"]
                snack_ideas = ["Apple slices", "Granola bar", "Nuts", "Cheese & crackers"]

                import random

                for day in st.session_state.weekly_meals:
                    breakfast = random.choice(breakfast_ideas)
                    lunch = random.choice(lunch_ideas)
                    dinner = random.choice(dinner_ideas)

                    # Only fill if empty (don't overwrite)
                    if not st.session_state.weekly_meals[day]["breakfast"].strip():
                        if default_servings > 1:
                            st.session_state.weekly_meals[day]["breakfast"] = f"{breakfast} ({default_servings}p)"
                        else:
                            st.session_state.weekly_meals[day]["breakfast"] = breakfast

                    if not st.session_state.weekly_meals[day]["lunch"].strip():
                        if default_servings > 1:
                            st.session_state.weekly_meals[day]["lunch"] = f"{lunch} ({default_servings}p)"
                        else:
                            st.session_state.weekly_meals[day]["lunch"] = lunch

                    if not st.session_state.weekly_meals[day]["dinner"].strip():
                        if default_servings > 1:
                            st.session_state.weekly_meals[day]["dinner"] = f"{dinner} ({default_servings}p)"
                        else:
                            st.session_state.weekly_meals[day]["dinner"] = dinner

                    # Snacks - only fill if empty
                    if not st.session_state.weekly_meals[day]["afternoon_snack"].strip():
                        # If checkbox is checked, always add. Otherwise 50% chance
                        if always_snack or random.random() > 0.5:
                            st.session_state.weekly_meals[day]["afternoon_snack"] = random.choice(snack_ideas)
                st.rerun()

    with col_plan:
        if st.button("Use Planned Meals", type="primary", key="implement_planned_meals"):
            if st.session_state.meal_goals_df.empty:
                st.warning("No meals planned yet! Add items to 'Plan Your Meals' first.")
            else:
                with st.spinner("Implementing your meal plan..."):
                    import random

                    # Clear existing schedule
                    for day in st.session_state.weekly_meals:
                        for meal_type in st.session_state.weekly_meals[day]:
                            st.session_state.weekly_meals[day][meal_type] = ""

                    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

                    # Process each planned meal
                    for _, row in st.session_state.meal_goals_df.iterrows():
                        item = row['Item']
                        category = row['Category']
                        frequency = int(row['Frequency'])
                        people = int(row['People'])

                        # Determine which meal slots to use based on category
                        if category == "Snack":
                            possible_slots = ["morning_snack", "afternoon_snack", "evening_snack"]
                        elif "breakfast" in item.lower() or "oatmeal" in item.lower() or "pancake" in item.lower():
                            possible_slots = ["breakfast"]
                        elif "lunch" in item.lower():
                            possible_slots = ["lunch"]
                        elif "dinner" in item.lower():
                            possible_slots = ["dinner"]
                        else:
                            # Default: assume it's a main meal (lunch or dinner)
                            possible_slots = ["lunch", "dinner"]

                        # Randomly select days for this item based on frequency
                        selected_days = random.sample(days, min(frequency, 7))

                        # Assign to schedule
                        for day in selected_days:
                            slot = random.choice(possible_slots)
                            # Only show servings for meals with 2+ people, not snacks
                            if people > 1 and category != "Snack":
                                meal_text = f"{item} ({people}p)"
                            else:
                                meal_text = item
                            # Find first available slot of this type
                            if not st.session_state.weekly_meals[day][slot]:
                                st.session_state.weekly_meals[day][slot] = meal_text
                            else:
                                # Try other days if this slot is taken
                                for backup_day in days:
                                    if backup_day not in selected_days and not \
                                            st.session_state.weekly_meals[backup_day][slot]:
                                        st.session_state.weekly_meals[backup_day][slot] = meal_text
                                        break

                    st.rerun()

    with col_clear:
        if st.button("Clear Schedule", key="clear_week"):
            st.session_state.weekly_meals = {
                day: {
                    "breakfast": "", "morning_snack": "", "lunch": "",
                    "afternoon_snack": "", "dinner": "", "evening_snack": ""
                } for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            }
            st.session_state.shopping_schedule = None
            st.rerun()

    st.write("")

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    cols = st.columns(7)

    meal_types = [
        ("breakfast", "Breakfast"),
        ("morning_snack", "Snack"),
        ("lunch", "Lunch"),
        ("afternoon_snack", "Snack"),
        ("dinner", "Dinner"),
        ("evening_snack", "Snack")
    ]

    for idx, day in enumerate(days):
        with cols[idx]:
            st.markdown(f"**{day[:3]}**")

            for meal_key, meal_label in meal_types:
                current_val = st.session_state.weekly_meals[day][meal_key]
                new_val = st.text_area(
                    f"{day} {meal_label}",
                    value=current_val,
                    key=f"weekly_{day}_{meal_key}",
                    placeholder=meal_label,
                    label_visibility="collapsed",
                    height=68
                )
                st.session_state.weekly_meals[day][meal_key] = new_val

    st.divider()

    # -----------------------------------------------------------------------
    # 3. SHOPPING OPTIMIZATION
    # -----------------------------------------------------------------------
    st.markdown("### 3. Generate Shopping List")

    if st.button("Generate Shopping Plan", type="primary", key="optimize_shopping"):
        all_meals = []
        for day, meals in st.session_state.weekly_meals.items():
            for meal_type, meal in meals.items():
                if meal.strip():
                    if "snack" in meal_type:
                        all_meals.append(f"{meal} for 1 person")
                    else:
                        all_meals.append(f"{meal} for 2 people")

        # ALSO collect items from the Meal Goals Table
        if 'meal_goals_df' in st.session_state and not st.session_state.meal_goals_df.empty:
            for _, row in st.session_state.meal_goals_df.iterrows():
                item_str = f"{row['Item']} for {row['People']} people"
                all_meals.append(item_str)

        if not all_meals:
            st.warning("Please add some meals to your plan first.")
        else:
            with st.spinner("Analyzing ingredients and optimizing shopping trips..."):
                all_ingredients = []
                for meal in all_meals:
                    ingredients = expand_meal_to_ingredients(meal)
                    all_ingredients.extend(ingredients)

                from collections import Counter

                ingredient_counts = Counter(all_ingredients)
                unique_ingredients = list(ingredient_counts.keys())

                results = compare_prices(unique_ingredients)

                perishable_keywords = ["milk", "eggs", "chicken", "fish", "lettuce", "tomato", "bread", "yogurt",
                                       "cream", "meat", "beef", "turkey", "cheese", "fruit", "vegetable"]
                non_perishable_keywords = ["pasta", "rice", "canned", "oil", "flour", "sugar", "salt", "sauce", "beans",
                                           "cereal", "crackers", "nuts"]

                perishable_items = [item for item in unique_ingredients if
                                    any(keyword in item.lower() for keyword in perishable_keywords)]
                non_perishable_items = [item for item in unique_ingredients if
                                        any(keyword in item.lower() for keyword in non_perishable_keywords)]
                other_items = [item for item in unique_ingredients if
                               item not in perishable_items and item not in non_perishable_items]

                st.session_state.shopping_schedule = {
                    "cheapest_store": results["cheapest_store"],
                    "total_cost": results["cheapest_total"],
                    "perishable": perishable_items,
                    "non_perishable": non_perishable_items,
                    "other": other_items,
                    "all_items": unique_ingredients
                }

    if st.session_state.shopping_schedule:
        schedule = st.session_state.shopping_schedule

        st.success(f"Optimized shopping plan generated!")
        st.markdown(f"**Recommended Store:** {schedule['cheapest_store']}")
        st.markdown(f"**Total Weekly Cost:** ${schedule['total_cost']:.2f}")

        st.write("")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Trip 1: Monday/Tuesday")
            st.caption("Non-perishables & shelf-stable items")
            st.markdown(f"Store: {schedule['cheapest_store']}")

            if schedule['non_perishable']:
                for item in schedule['non_perishable'][:6]:
                    st.write(f"• {item}")
                if len(schedule['non_perishable']) > 6:
                    st.caption(f"... and {len(schedule['non_perishable']) - 6} more")
            else:
                st.info("No non-perishable items")

        with col2:
            st.markdown("#### Trip 2: Thursday/Friday")
            st.caption("Fresh produce & perishables")
            st.markdown(f"Store: {schedule['cheapest_store']}")

            if schedule['perishable']:
                for item in schedule['perishable'][:6]:
                    st.write(f"• {item}")
                if len(schedule['perishable']) > 6:
                    st.caption(f"... and {len(schedule['perishable']) - 6} more")
            else:
                st.info("No perishable items")

        st.divider()

        with st.expander("View Complete Shopping List"):
            st.dataframe(
                pd.DataFrame({
                    "Item": schedule['all_items'],
                    "Category": [
                        "Perishable" if item in schedule['perishable']
                        else "Non-Perishable" if item in schedule['non_perishable']
                        else "Other"
                        for item in schedule['all_items']
                    ]
                }),
                use_container_width=True,
                hide_index=True
            )

        meal_plan_text = "WEEKLY MEAL PLAN\n\n"
        for day, meals in st.session_state.weekly_meals.items():
            meal_plan_text += f"{day}:\n"
            for k, v in meals.items():
                if v: meal_plan_text += f"  {k}: {v}\n"
            meal_plan_text += "\n"

        shopping_text = f"WEEKLY SHOPPING LIST\nStore: {schedule['cheapest_store']}\nTotal: ${schedule['total_cost']:.2f}\n\n"
        shopping_text += "TRIP 1 (Monday/Tuesday) - Non-Perishables:\n"
        for item in schedule['non_perishable']:
            shopping_text += f"- [ ] {item}\n"
        shopping_text += "\nTRIP 2 (Thursday/Friday) - Perishables:\n"
        for item in schedule['perishable']:
            shopping_text += f"- [ ] {item}\n"
        if schedule['other']:
            shopping_text += "\nOther Items:\n"
            for item in schedule['other']:
                shopping_text += f"- [ ] {item}\n"

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button("Download Meal Plan", meal_plan_text, "weekly_meal_plan.txt")
        with col_dl2:
            st.download_button("Download Shopping List", shopping_text, "weekly_shopping_list.txt")

    st.divider()
    st.markdown("### Weekly Schedule View")

    schedule_data = []
    times = ["08:00 AM", "10:30 AM", "12:30 PM", "03:30 PM", "06:30 PM", "09:00 PM"]
    meal_labels = ["Breakfast", "Snack", "Lunch", "Snack", "Dinner", "Snack"]
    keys = ["breakfast", "morning_snack", "lunch", "afternoon_snack", "dinner", "evening_snack"]

    for i, time in enumerate(times):
        row = {"Time": f"{time}\n{meal_labels[i]}"}
        for day in days:
            meal = st.session_state.weekly_meals[day].get(keys[i], "")
            row[day] = meal if meal else ""
        schedule_data.append(row)

    schedule_df = pd.DataFrame(schedule_data)

    st.dataframe(
        schedule_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Time": st.column_config.TextColumn("Time", width="medium", disabled=True),
            "Monday": st.column_config.TextColumn("Mon", width="small"),
            "Tuesday": st.column_config.TextColumn("Tue", width="small"),
            "Wednesday": st.column_config.TextColumn("Wed", width="small"),
            "Thursday": st.column_config.TextColumn("Thu", width="small"),
            "Friday": st.column_config.TextColumn("Fri", width="small"),
            "Saturday": st.column_config.TextColumn("Sat", width="small"),
            "Sunday": st.column_config.TextColumn("Sun", width="small"),
        },
        height=350
    )


# ---- TAB 5: BULK MEAL PREP ----
with tab5:
    st.subheader("Bulk Meal Prep")
    st.caption("Cost analysis for batch cooking and meal preparation.")

    prep_type = st.radio("Prep Mode:", ["Gym Meal Prep", "Custom Batch Prep"], horizontal=True)
    st.divider()

    if prep_type == "Gym Meal Prep":
        st.write("High-protein meal plan generation.")

        col_sets, col_goal = st.columns(2)
        with col_sets:
            days = st.slider("Number of Days", 3, 7, 5)
        with col_goal:
            diet_goal = st.selectbox("Goal", ["Maintenance / Lean Bulk", "Cut / Fat Loss"])

        if st.button("Generate Plan", type="primary", key="generate_bulk_gym"):

            # Define menus based on goal
            if diet_goal == "Maintenance / Lean Bulk":
                plan_name = "Lean Bulk Builder"
                base_ings = ["chicken breast", "ground beef", "brown rice", "pasta", "broccoli",
                             "eggs", "oats", "protein powder", "bananas", "peanut butter"]

                menu = {
                    "Breakfast": "Proats (Oats + Protein Powder) & 2 Eggs",
                    "Lunch": "Chicken Breast, Brown Rice & Broccoli",
                    "Dinner": "Ground Beef Pasta with Tomato Sauce",
                    "Snacks": "Banana & Peanut Butter or Protein Shake"
                }
            else:
                plan_name = "Rapid Fat Loss Cut"
                base_ings = ["chicken breast", "white fish", "sweet potato", "spinach", "asparagus",
                             "egg whites", "berries", "protein powder", "greek yogurt"]

                menu = {
                    "Breakfast": "Egg White Omelet with Spinach",
                    "Lunch": "Grilled Chicken & Asparagus",
                    "Dinner": "White Fish & Sweet Potato",
                    "Snacks": "Greek Yogurt with Berries"
                }

            with st.spinner(f"Calculating costs for {plan_name}..."):
                results = compare_prices(base_ings)

            st.success(f"Generated: {plan_name} ({days} Days)")

            # --- NEW: Meal Breakdown Display ---
            st.markdown("### The Menu")
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown("**Breakfast**")
                st.info(menu["Breakfast"])
            with m2:
                st.markdown("**Lunch**")
                st.info(menu["Lunch"])
            with m3:
                st.markdown("**Dinner**")
                st.info(menu["Dinner"])
            with m4:
                st.markdown("**Snacks**")
                st.info(menu["Snacks"])
            # -----------------------------------

            st.divider()

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Grocery Cost", f"${results['cheapest_total']:.2f}")
            with c2:
                cost_per_day = results['cheapest_total'] / days
                st.metric("Cost / Day", f"${cost_per_day:.2f}")
            with c3:
                # Approx 3 main meals + 1 snack = 4 eating occasions
                cost_per_meal = results['cheapest_total'] / (days * 4)
                st.metric("Cost / Meal (Approx)", f"${cost_per_meal:.2f}")

            st.markdown(f"### Recommended Store: <span style='color:{GOOSE_GREEN}'>{results['cheapest_store']}</span>",
                        unsafe_allow_html=True)

            # Download
            gym_text = f"Goose Grocer {plan_name}\nTarget: {days} days\nStore: {results['cheapest_store']}\nTotal: ${results['cheapest_total']:.2f}\n\n"
            gym_text += "MENU:\n"
            for k, v in menu.items():
                gym_text += f"{k}: {v}\n"
            gym_text += "\nSHOPPING LIST:\n"
            for ing in base_ings:
                gym_text += f"- [ ] {ing}\n"

            st.download_button("Download Prep List", gym_text, "gym_prep.txt")

    else:
        # Custom Batch Prep Logic
        if 'results_tab5' not in st.session_state:
            st.session_state.results_tab5 = None
        if 'ingredients_tab5' not in st.session_state:
            st.session_state.ingredients_tab5 = None
        if 'recipe_tab5' not in st.session_state:
            st.session_state.recipe_tab5 = ""

        st.write("Batch cooking analysis.")

        recipe_query = st.text_input(
            "What do you want to cook?",
            placeholder="e.g., 'Meals with Mac and Cheese' or 'Vegetarian Chili'",
            key="bulk_recipe"
        )
        servings = st.number_input("Servings", 4, 50, 8, key="bulk_servings")

        if st.button("Analyze Cost", key="analyze_bulk"):
            if recipe_query:
                with st.spinner("Analyzing ingredients..."):
                    ings = expand_meal_to_ingredients(f"{recipe_query} for {servings} servings")
                    st.session_state.ingredients_tab5 = ings
                    st.session_state.recipe_tab5 = recipe_query
                    st.session_state.results_tab5 = compare_prices(ings)
            else:
                st.warning("Please describe what you want to cook.")

        if st.session_state.results_tab5:
            results = st.session_state.results_tab5
            ings = st.session_state.ingredients_tab5

            st.success(f"Analysis complete for {servings} servings.")
            st.write("**Ingredients:**")
            st.write(", ".join(ings))

            st.divider()
            st.metric("Total Batch Cost", f"${results['cheapest_total']:.2f}")
            st.caption(f"Cost per serving: ${results['cheapest_total'] / servings:.2f}")
            st.markdown(f"### Best Price at <span style='color:{GOOSE_GREEN}'>{results['cheapest_store']}</span>",
                        unsafe_allow_html=True)

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
        # Create sidebar layout: filters on left, database on right
        filter_col, data_col = st.columns([1, 3])

        with filter_col:
            st.markdown("#### Filters")

            # Initialize session state for filters
            all_stores = ["No Frills", "Food Basics", "Walmart", "FreshCo", "Loblaws"]
            categories = sorted(products_df['category'].dropna().unique())

            if 'selected_stores_checkboxes' not in st.session_state:
                st.session_state.selected_stores_checkboxes = all_stores.copy()
            if 'selected_categories_checkboxes' not in st.session_state:
                st.session_state.selected_categories_checkboxes = categories.copy()

            # Stores filter (compact)
            st.markdown("**Stores**")
            selected_stores = []
            for store in all_stores:
                if st.checkbox(store, value=(store in st.session_state.selected_stores_checkboxes),
                               key=f"store_{store}"):
                    selected_stores.append(store)

            st.divider()

            # Categories filter (compact)
            st.markdown("**Categories**")
            selected_categories = []
            for category in categories:
                if st.checkbox(category, value=(category in st.session_state.selected_categories_checkboxes),
                               key=f"cat_{category}"):
                    selected_categories.append(category)

            st.divider()

            # Reset button without extra spacing
            if st.button("Reset", key="reset_filters", use_container_width=True):
                st.session_state.selected_stores_checkboxes = all_stores.copy()
                st.session_state.selected_categories_checkboxes = categories.copy()
                st.rerun()

            # Update session state
            st.session_state.selected_stores_checkboxes = selected_stores
            st.session_state.selected_categories_checkboxes = selected_categories

        with data_col:
            # Legend with rounded color boxes
            st.markdown("""
            <span style='display: inline-block; width: 15px; height: 15px; background-color: #4CAF50; border-radius: 3px; margin-right: 5px; vertical-align: middle;'></span>Best Price
            <span style='display: inline-block; width: 15px; height: 15px; background-color: #90EE90; border-radius: 3px; margin-left: 12px; margin-right: 5px; vertical-align: middle;'></span>2nd Best
            <span style='display: inline-block; width: 15px; height: 15px; background-color: #FF6B6B; border-radius: 3px; margin-left: 12px; margin-right: 5px; vertical-align: middle;'></span>Most Expensive
            """, unsafe_allow_html=True)

            # Search box right under legend
            search = st.text_input("Search Products", placeholder="e.g., chicken, milk...", key="db_search")

            st.divider()

            # Validation
            if not selected_stores:
                st.warning("Please select at least one store.")
                st.stop()

            if not selected_categories:
                st.warning("Please select at least one category.")
                st.stop()

            # Apply category filter
            filtered_df = products_df[products_df['category'].isin(selected_categories)].copy()

            # Apply search filter
            if search:
                filtered_df = filtered_df[filtered_df["product_name"].str.contains(search, case=False)]

            if filtered_df.empty:
                st.info("No products match your filters.")
            else:
                # Map store names to column names
                store_to_col = {
                    "No Frills": "no_frills_price",
                    "Food Basics": "food_basics_price",
                    "Walmart": "walmart_price",
                    "FreshCo": "freshco_price",
                    "Loblaws": "loblaws_price"
                }

                # Select columns based on selected stores
                selected_price_cols = [store_to_col[store] for store in selected_stores]
                display_cols = ["product_name", "category"] + selected_price_cols

                display_df = filtered_df[display_cols].copy()

                # Rename columns
                col_rename = {
                    "product_name": "Product Name",
                    "category": "Category",
                    "no_frills_price": "No Frills",
                    "food_basics_price": "Food Basics",
                    "walmart_price": "Walmart",
                    "freshco_price": "FreshCo",
                    "loblaws_price": "Loblaws"
                }
                display_df.columns = [col_rename.get(col, col) for col in display_df.columns]

                # Get renamed price columns
                price_cols = [col_rename[pc] for pc in selected_price_cols]


                # Highlighting function
                def highlight_prices(row):
                    styles = [''] * len(row)
                    prices = [(row[col], col) for col in price_cols if pd.notna(row[col]) and row[col] > 0]

                    if len(prices) >= 2:
                        prices.sort(key=lambda x: x[0])
                        best = prices[0][0]
                        second = prices[1][0] if len(prices) > 1 else None
                        worst = prices[-1][0]

                        for idx, col in enumerate(row.index):
                            if col in price_cols and pd.notna(row[col]) and row[col] > 0:
                                if row[col] == best:
                                    styles[idx] = 'background-color: #4CAF50; color: white; font-weight: bold'
                                elif second and row[col] == second and second != best:
                                    styles[idx] = 'background-color: #90EE90; color: black; font-weight: bold'
                                elif row[col] == worst and worst != best:
                                    styles[idx] = 'background-color: #FF6B6B; color: white; font-weight: bold'
                    return styles


                # Format dictionary for selected stores
                format_dict = {col: "${:.2f}" for col in price_cols}

                # Apply styling and formatting
                styled = display_df.style.apply(highlight_prices, axis=1).format(format_dict, na_rep="N/A")

                # Show count
                st.caption(f"Showing {len(display_df)} products")

                st.dataframe(styled, use_container_width=True, hide_index=True, height=600)

# ---- TAB 7: RECIPE BOOK ----
with tab7:
    st.subheader("Your Recipe Book")

    # NEW: Requested Info Box
    st.info(
        "**How it works:** Save your favorite generated meal plans and bulk prep calculations here. This allows you to quickly re-access ingredient lists and track estimated costs without re-entering details.")

    recipes_df = get_saved_recipes()

    if not recipes_df.empty:
        # Display recipes in a grid or list
        for idx, row in recipes_df.iterrows():
            with st.expander(f"{row['recipe_name']}"):
                st.caption(f"Added on: {row['created_at']}")

                col_ing, col_instr = st.columns([1, 2])

                with col_ing:
                    st.markdown("**Ingredients**")
                    # Assuming ingredients are stored as a comma-separated string or list in DB
                    # Adjust depending on your actual DB format
                    ingredients_list = row['ingredients']
                    if isinstance(ingredients_list, str):
                        # Simple cleanup if it's a raw string representation
                        ingredients_list = ingredients_list.replace("[", "").replace("]", "").replace("'", "").split(
                            ",")

                    for ing in ingredients_list:
                        st.write(f"• {ing.strip()}")

                with col_instr:
                    st.markdown("**Notes / Instructions**")
                    st.write(row['instructions'])

                st.divider()
                if st.button("Re-Calculate Price", key=f"recalc_{row['id']}"):
                    st.session_state['grocery_input'] = "\n".join([i.strip() for i in ingredients_list])
                    st.switch_page("app.py")  # Or direct user to Tab 2
                    st.toast("Ingredients loaded into Grocery List calculator!")
    else:
        st.markdown(
            """
            <div style='text-align: center; color: gray; padding: 50px;'>
                <h3>No recipes saved yet</h3>
                <p>Go to the <b>Meal Planner</b> or <b>Bulk Prep</b> tabs to generate and save your first recipe!</p>
            </div>
            """,
            unsafe_allow_html=True
        )

# ---------------------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------------------
st.divider()
st.caption("© 2026 Goose Grocer. All rights reserved.")

# 🛒 GrocerAI - Smart Grocery Price Comparison

> Find the cheapest groceries across local stores using AI.  
> Built at CXC AI Hackathon 2026.

## What it does

1. You enter a grocery list (or describe a meal like "tacos for 4")
2. AI matches your items to products across 5 Canadian grocery stores
3. Shows you which store is cheapest and how much you save
4. Can parse store flyer images to find current deals

## Tech Stack

- **Frontend**: Streamlit (Python web framework)
- **AI**: Google Gemini Pro + Gemini Vision
- **Database**: SQLite
- **Language**: Python

---

## 🚀 COMPLETE SETUP GUIDE (Beginner-Friendly)

### Step 1: Install Python

**Check if you already have Python:**
```bash
python --version
```
or
```bash
python3 --version
```

You need Python 3.10 or higher. If you don't have it:
- **Windows**: Download from https://www.python.org/downloads/ — CHECK the "Add Python to PATH" box during install!
- **Mac**: `brew install python` (if you have Homebrew) or download from python.org
- **Linux**: `sudo apt install python3 python3-pip`

### Step 2: Clone the Repository

```bash
# Open your terminal (Command Prompt on Windows, Terminal on Mac/Linux)
# Navigate to where you want the project
cd Desktop

# Clone the repo (replace with your actual repo URL)
git clone https://github.com/YOUR_TEAM/grocery-ai.git
cd grocery-ai
```

### Step 3: Set Up a Virtual Environment (recommended)

A virtual environment keeps this project's packages separate from your system Python.

```bash
# Create the virtual environment
python -m venv venv

# Activate it:
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# You should see (venv) at the start of your terminal prompt
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs: Streamlit, Google AI SDK, pandas, ChromaDB, and other packages.
It might take a minute or two.

### Step 5: Get Your Gemini API Key

1. Go to https://aistudio.google.com/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key (it looks like: `AIzaSy...`)

### Step 6: Create Your .env File

```bash
# Copy the example file
cp .env.example .env
```

Then open `.env` in your text editor and replace the placeholder with your real key:

```
GEMINI_API_KEY=AIzaSyYOUR_ACTUAL_KEY_HERE
OPENROUTER_API_KEY=your_openrouter_key_if_you_have_one
```

⚠️ **NEVER commit the .env file to GitHub!** The .gitignore already handles this.

### Step 7: Initialize the Database

```bash
python database.py
```

You should see:
```
🛒 Setting up GrocerAI database...
----------------------------------------
✅ Database tables created successfully!
✅ Loaded 60 products into the database!
----------------------------------------
📊 Database contains 60 products
   Categories: Dairy, Bakery, Meat, Produce, ...
✅ Database is ready! You can now run the app with: streamlit run app.py
```

### Step 8: Run the App!

```bash
streamlit run app.py
```

Your browser should open to http://localhost:8501 with the app running!

---

## 📁 Project Structure

```
grocery-ai/
├── app.py              ← Streamlit web interface (Person 4)
├── database.py         ← Database setup and queries (Person 1)
├── flyer_parser.py     ← Gemini Vision flyer parsing (Person 2)
├── comparison.py       ← Price comparison logic (Person 3)
├── data/
│   ├── seed_prices.csv ← Pre-loaded price data (60 items x 5 stores)
│   └── flyers/         ← Store flyer images go here
├── .env                ← Your API keys (gitignored)
├── .env.example        ← Template for .env
├── .gitignore          ← Tells git what not to commit
├── requirements.txt    ← Python dependencies
└── README.md           ← You are here!
```

---

## 🔧 How Each File Works

### database.py
- Creates an SQLite database with two tables: `products` (seed data) and `flyer_deals` (from parsed flyers)
- Run `python database.py` to set it up
- Other files import functions like `get_all_products()` and `search_products()`

### flyer_parser.py
- Takes a flyer image → sends to Gemini Vision → gets back JSON of products and prices
- Run standalone: `python flyer_parser.py data/flyers/image.png "Store Name"`
- Or use from the Streamlit sidebar upload feature

### comparison.py
- Takes a grocery list → uses Gemini to fuzzy-match items → compares prices → returns cheapest store
- Also handles meal-to-ingredient expansion ("tacos for 4" → ingredient list)

### app.py
- The web interface that ties everything together
- Three tabs: Grocery List, Meal Planner, Browse Database
- Sidebar: Upload and parse flyer images

---

## 📸 How to Get Flyer Images

**DO NOT screenshot entire flyer pages** — they're too low resolution.

**Instead:**
1. Go to flipp.com or a store's website (e.g., foodbasics.ca/flyer)
2. Zoom in on a section of the flyer (4-8 products visible)
3. Take a screenshot of JUST that section
4. Save as PNG
5. Repeat for each section you want to capture

**Good image:** Close-up of 4-6 products, prices clearly readable  
**Bad image:** Full flyer page with tiny unreadable text

---

## 🧑‍💻 Git Workflow for the Team

```bash
# Before you start working, always pull the latest changes
git pull

# After you make changes to your files
git add .
git commit -m "describe what you changed"
git push

# If you get a merge conflict, talk to your teammate and resolve together
```

**Rule: Each person works on their own file(s) to avoid conflicts.**

---

## Team Task Assignment

| Person | Primary File | Responsibility |
|--------|-------------|----------------|
| Person 1 | database.py + data/ | Data collection, database, seed data |
| Person 2 | flyer_parser.py | Gemini Vision integration, flyer parsing |
| Person 3 | comparison.py | Price comparison logic, Gemini matching |
| Person 4 | app.py | Streamlit frontend, integration, demo |

---

## 🎯 Hackathon Timeline

### Saturday Morning (Phase 1: Foundation)
- [ ] Everyone: clone repo, install deps, run database.py, run app
- [ ] Person 1: Improve seed data, add more items
- [ ] Person 2: Test flyer parser on real flyer images
- [ ] Person 3: Test comparison engine, tune Gemini prompts
- [ ] Person 4: Polish UI layout, add loading states

### Saturday Afternoon (Phase 2: Integration)
- [ ] Connect flyer parser to sidebar upload
- [ ] Connect comparison engine to grocery list input
- [ ] Test meal planner feature
- [ ] Add error handling everywhere

### Saturday Evening (Phase 2 continued)
- [ ] End-to-end testing (full flow works)
- [ ] Fix bugs found during testing
- [ ] Parse 5-10 real flyers into the database

### Sunday Morning (Phase 3: Polish + Stretch)
- [ ] UI polish (colors, layout, store logos)
- [ ] Add stretch features if time allows
- [ ] ElevenLabs voice output (optional prize category)
- [ ] Auth0 login (optional prize category)

### Sunday Afternoon (Phase 4: Presentation)
- [ ] Build 3-5 slides
- [ ] Practice demo 3 times
- [ ] Prepare backup screenshots in case live demo fails
- [ ] Submit!
# 🎓 Uni Scout

A small Python CLI that pulls **real university data** from the U.S. Department of Education's **College Scorecard API** and prints a bold, neon-coloured comparison in your terminal: acceptance rates, tuition, graduation rates and graduate salaries.

## What it does
1. **Calls a public REST API** – College Scorecard (`api.data.gov`).
2. **Parses the JSON response** – reads each school in `results`.
3. **Stores results in a class** – each school becomes a `University` dataclass (`University.from_json`).
4. **Prints a formatted summary** – stat cards, a university leaderboard with bars, difficulty badges, and a "best value" pick.
5. **Runs in a virtual environment** with the **API key read from `.env`** via `python-dotenv`.

## Setup

```bash
# 1. Create & activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your API key (free at https://api.data.gov/signup)
cp .env.example .env             # Windows: copy .env.example .env
# then edit .env → SCORECARD_API_KEY=your_real_key

# 4. Run
python main.py               # most selective universities
python main.py "Texas"       # search by name
```

## Project structure
```
uni-scout/
├── main.py           # API call, University class, rendering
├── requirements.txt  # requests, python-dotenv, rich
└── README.md
```

## Tech
`requests` · `python-dotenv` · `rich` · `dataclasses`

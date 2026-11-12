# LabhSetu

**AI-powered Government Scheme Discovery Platform** — built by **Team Tech Vedas** for the Aarambh hackathon (theme: *AI for the Next Billion*).

LabhSetu helps citizens discover government schemes they may be eligible for. Instead of reading through dozens of scheme pages, a user simply describes their situation in plain language — and LabhSetu works out which schemes fit, which don't, and what information is still missing.

## How it works

1. **You describe your situation** in everyday language (English, Hinglish and Kanglish phrasing are understood), e.g. *"I am a 20-year-old BTech student from Karnataka, OBC category, family income is 3 lakh."*
2. **AI extracts a structured profile** — age, state, course, income, category — using Groq (`gpt-oss-20b`) on the backend only.
3. **A deterministic rules engine decides** — eligible / not eligible / more information needed. The AI never decides eligibility; every verdict comes from explicit, inspectable rules matched against each scheme's criteria.
4. **You get a clear answer** — matching schemes with reasons, plus the official source for each scheme.

## What's inside

- **41 real schemes** in the database, researched and verified by the team against their official sources (each scheme records its source and last-verified date), with scheme-expiry handling built in.
- Structured eligibility criteria (age, income limits, category, course, state) evaluated by the rules engine.
- Friendly conversation handling — greetings and vague answers get follow-up questions instead of dead ends.

## Tech stack

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, FastAPI
- **Database:** SQLite
- **AI:** Groq API (backend only — the key lives in the backend `.env`, never in the browser)

## Running it locally (Windows)

```powershell
cd backend
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Groq API key, then start the backend and open the frontend.

## Status

Working hackathon product, demoed end-to-end: natural-language profile extraction → rules-based eligibility → explained results across a 41-scheme library.

## Team

**Team Tech Vedas** — built for Aarambh, on the theme *AI for the Next Billion*.

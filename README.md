# LabhSetu

AI-powered Government Scheme Discovery Platform.

LabhSetu helps users describe their situation in plain language and discover
government schemes they may be eligible for. This repository is the initial
project structure for a 36-hour hackathon MVP - no features are implemented yet.

## Technology Stack

- Frontend: HTML, CSS, Vanilla JavaScript
- Backend: Python FastAPI
- Database: SQLite
- AI: Groq API (backend integration only, added in a later task)
- Version Control: GitHub

## Project Structure

```
LabhSetu/
|-- backend/
|   |-- app/
|   |   |-- __init__.py
|   |   |-- main.py
|   |   |-- database.py
|   |   |-- models.py
|   |   |-- routes/
|   |   `-- services/
|   |-- tests/
|   `-- requirements.txt
|-- frontend/
|   |-- index.html
|   |-- css/style.css
|   |-- js/app.js
|   `-- assets/
|-- .env.example
|-- .gitignore
`-- README.md
```

## Windows Setup (PowerShell)

Open PowerShell inside the cloned project folder:

```powershell
cd C:\Users\patel\Desktop\LabhSetu
```

### 1. Create a virtual environment (inside the backend folder)

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, run this once and try again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables (later, when Groq is integrated)

Copy the example file at the project root and fill in your own key.
Never commit the real `.env` file.

```powershell
cd ..
Copy-Item .env.example .env
```

### 4. Start the backend

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

The API now runs at http://127.0.0.1:8000

- Root: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/health
- Interactive docs: http://127.0.0.1:8000/docs

### 5. View the frontend

Open `frontend/index.html` in your browser. Frontend-to-backend
integration will be added in a later task.

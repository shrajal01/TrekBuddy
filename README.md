# TrekBuddy — Your Indian Trek Guide

TrekBuddy is an AI-powered conversational guide designed to help outdoor enthusiasts and beginners plan treks across India. Whether you are preparing for high-altitude Himalayan passes or exploring trails in the Western Ghats and Sahyadris, TrekBuddy provides practical advice on trek difficulty, estimated budgets, optimal seasons, sample itineraries, gear checklists, and mountain safety.

The project features a **FastAPI** backend integrated with an OpenAI LLM, paired with a lightweight, responsive **Vanilla HTML, CSS, and JavaScript** frontend.

- **Live Frontend**: [https://trekbuddy-26.netlify.app](https://trekbuddy-26.netlify.app)
- **Live Backend API**: [https://trekbuddy-vip1.onrender.com](https://trekbuddy-vip1.onrender.com)
- **Live Interactive API Docs**: [https://trekbuddy-vip1.onrender.com/docs](https://trekbuddy-vip1.onrender.com/docs)

---

## Features

- **Indian Trek Guidance**: Covers difficulty ratings, elevation profiles, expense breakdowns, best weather windows, packing lists, and AMS (Acute Mountain Sickness) safety precautions.
- **ChatGPT-Style Streaming Responses**: Real-time token streaming from OpenAI's Responses API progressively updates a single assistant message bubble as chunks arrive.
- **Trekking-Inspired Dark Theme UI**: Styled with dark charcoal/black tones, an atmospheric Himalayan mountain background, a subtle dark overlay for readability, and muted forest/mountain green accents.
- **Smart Automatic Scrolling**: Keeps the latest streaming content in view without expensive animation stutter, while preserving user scroll position when intentionally scrolling up to read earlier replies.
- **Concurrency-Safe Conversation History**: Retains multi-turn conversation context across interactions using backend concurrency locks, ensuring failed or interrupted streams do not corrupt state.
- **Interactive Suggestions**: Quick starter chips for popular queries (e.g., Kedarkantha, Hampta Pass, winter packing lists, and AMS safety).
- **Responsive Layout**: Designed for seamless viewing across mobile and desktop screens without heavy CSS frameworks. Header and input bar remain fixed while the chat messages area scrolls.
- **Chat Reset**: Single-click reset button that clears both the frontend chat area and the backend conversation state (`DELETE /api`).
- **Zero Build Tooling**: Frontend runs directly in the browser or via a simple static file server without Webpack, Vite, Node.js, or npm.

---

## Tech Stack

### Backend
- **Python**: 3.10+ (tested on Python 3.13)
- **FastAPI**: Modern, high-performance web framework for the REST API
- **Uvicorn**: ASGI web server implementation
- **OpenAI Python SDK**: Client for LLM response generation
- **python-dotenv**: Environment variable management
- **httpx**: HTTP client for testing and asynchronous requests

### Frontend
- **HTML5**: Semantic markup for the chat layout and accessibility
- **Vanilla CSS3**: Custom design system, responsive flexbox layout, dark mountain theme
- **Vanilla JavaScript (ES6+)**: DOM manipulation, asynchronous `fetch` requests, and client-side formatting

---

## Project Structure

```text
.
├── .env.example          # Environment variable template
├── .gitignore            # Git ignore file for secrets and virtualenvs
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
├── app/
│   ├── __init__.py       # App package initialization
│   ├── main.py           # FastAPI application, CORS, routes & LLM logic
│   └── service.py        # Support helper services
├── frontend/
│   ├── index.html        # Single-page chat interface
│   ├── style.css         # Dark theme styling and mountain accents
│   ├── app.js            # Frontend logic and backend integration
│   └── assets/
│       └── himalayas_bg.jpg # Background mountain imagery
└── tests/                # Test suite directory
```

---

## Prerequisites

- **Python 3.10 or higher** (Python 3.13 recommended)
- **OpenAI API Key** with access to chat/responses models
- **Windows PowerShell** (or bash/zsh on macOS/Linux)
- A modern web browser (Chrome, Edge, Firefox, Safari)

---

## Local Setup and Installation

Assuming you have opened your terminal in the project root:

### 1. Create and Activate a Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate the virtual environment in PowerShell
.\.venv\Scripts\Activate.ps1
```
> **Note:** If script execution is restricted on Windows, allow scripts for the current user by running:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the example environment template and add your secret API key:
```powershell
Copy-Item .env.example .env
```

Open `.env` in your editor and set your OpenAI API credentials:
```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-6-luna
```

---

## Running the Application Locally

Run the backend and frontend in separate terminals from the project root.

### Terminal 1: Start the FastAPI Backend
```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8080
```
- **Local API Endpoint**: `http://127.0.0.1:8080`
- **Local Interactive Docs**: `http://127.0.0.1:8080/docs`
- **Local ReDoc**: `http://127.0.0.1:8080/redoc`

### Terminal 2: Start the Frontend Server
Serve the `frontend/` directory using Python's built-in HTTP server:
```powershell
python -m http.server 3000 --directory frontend
```
- **Local Frontend URL**: `http://localhost:3000`

*(Alternatively, you can open `frontend/index.html` directly in your browser.)*

### Terminal 3: Run Automated Tests
Run the pytest test suite to verify streaming, concurrency lock, empty message validation, and history reset:
```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

---

## API Documentation

### 1. Conversational Chat (Streaming)
Sends a plain-text prompt to TrekBuddy and receives a real-time streamed response chunk-by-chunk directly from the OpenAI Responses API.

- **Live URL**: `https://trekbuddy-vip1.onrender.com/api/chat`
- **Local URL**: `http://127.0.0.1:8080/api/chat`
- **Method**: `POST`
- **Content-Type**: `text/plain`
- **Accept**: `text/plain`
- **Response Format**: `StreamingResponse` (`text/plain; charset=utf-8`) with `Transfer-Encoding: chunked` and `X-Accel-Buffering: no`

#### Example Request
```powershell
curl -N -X POST "http://127.0.0.1:8080/api/chat" `
  -H "Content-Type: text/plain" `
  --data "What is the difficulty and best season for Kedarkantha trek?"
```
*(Use `-N` or `--no-buffer` with curl to see tokens stream to the terminal in real time).*

#### Example Streamed Response (`200 OK`)
Chunks are progressively emitted as text deltas:
```text
Kedarkantha is generally rated easy to moderate and is suitable for first-time Himalayan trekkers with basic fitness.

- Maximum altitude: about 12,500 ft (3,810 m)
- Typical duration: 4-6 days
- Best season: December to April for snow trekking, or October to November for clear autumn views.
...
```

#### Error Response (`400 Bad Request`)
Returned if the request body is empty:
```json
{
  "detail": "Message cannot be empty."
}
```

#### Error Response (`502 Bad Gateway`)
Returned if OpenAI stream initialization fails:
```json
{
  "detail": "Unable to process your message."
}
```

---

### 2. Standalone LLM Generation
Low-level single-prompt completion endpoint.

- **Live URL**: `https://trekbuddy-vip1.onrender.com/api/generate`
- **Local URL**: `http://127.0.0.1:8080/api/generate`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### Example Request
```json
{
  "model": "gpt-6-luna",
  "input": "Summarize safety protocols for crossing mountain streams."
}
```

#### Example Response (`200 OK`)
```json
{
  "model": "gpt-6-luna",
  "output": "Always unbuckle backpack hip straps, cross early in the morning when glacial melt is lowest, and use trekking poles for a three-point stance.",
  "usage": {
    "input_tokens": 14,
    "output_tokens": 28,
    "total_tokens": 42
  }
}
```

---

### 3. Clear Chat History
Clears the current conversational memory buffer on the backend.

- **Live URL**: `https://trekbuddy-vip1.onrender.com/api`
- **Local URL**: `http://127.0.0.1:8080/api`
- **Method**: `DELETE`
- **Response**: `200 OK` (empty body)

---

## Environment Variables

| Variable | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `OPENAI_API_KEY` | **Yes** | *None* | OpenAI API authentication key. |
| `OPENAI_MODEL` | No | `gpt-6-luna` | Model identifier passed to the OpenAI responses API. |

---

## Security Notes

1. **Keep `.env` Private**: The `.env` file contains your private API credentials and must never be committed to Git. The repository includes `.gitignore` to prevent committing `.env`.
2. **Backend API Key Isolation**: All LLM requests are processed on the FastAPI server. The OpenAI API key is never exposed to the frontend browser client.
3. **CORS Configuration**: The backend explicitly allows the live frontend origin (`https://trekbuddy-26.netlify.app`) as well as local development ports, preventing unauthorized cross-origin requests while maintaining full functionality.

---

## Production Deployment

### Backend on Render
- **Live URL**: `https://trekbuddy-vip1.onrender.com`
- **Service Type**: Web Service (Python)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `OPENAI_API_KEY`: Configured securely in the Render dashboard under Environment.
  - `OPENAI_MODEL`: `gpt-6-luna`

### Frontend on Netlify
- **Live URL**: `https://trekbuddy-26.netlify.app`
- **Service Type**: Static Site
- **Publish Directory**: `frontend`
- **Build Command**: *None (pure static HTML/CSS/JS)*
- The frontend connects directly to the production backend via `API_BASE` defined in [`frontend/app.js`](file:///frontend/app.js):
  ```javascript
  const API_BASE = "https://trekbuddy-vip1.onrender.com";
  ```

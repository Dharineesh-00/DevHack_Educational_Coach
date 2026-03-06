# DevHack Educational Coach — DSA Tutor

An AI-powered, full-stack Data Structures & Algorithms tutoring platform that runs a **Good Cop / Bad Cop Interview Panel** on every code submission. Powered by **OpenRouter (Claude 3 Haiku)** with automatic free-model fallbacks, a live Monaco code editor, a Socratic chatbot, and an agent debate terminal.

---

## Features

- **Socratic Tutor Chat** — Ask questions and get guided hints, never direct answers
- **AI Agent Debate Panel** — Three agents (Critic, Defender, Judge) review your code in real time
- **Code Execution** — Runs your Python code via the Piston API
- **Complexity Analysis** — Automatic time/space complexity detection
- **LeetCode-style Problems** — Curated DSA problem set with starter code
- **OpenRouter LLM** — Claude 3 Haiku as primary model; free-tier fallbacks (Mistral, LLaMA, Gemma, Qwen)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite, Tailwind CSS v4, Monaco Editor |
| Backend | Python 3.13, FastAPI, uvicorn |
| LLM | OpenRouter API (Claude 3 Haiku + free fallbacks) |
| Code Runner | Piston API |
| HTTP Client | httpx (async) |

---

## Project Structure

```
project2/
├── backend/
│   ├── main.py              # FastAPI app — /submit and /chat endpoints
│   ├── orchestrator.py      # Agent debate pipeline
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── complexity_agent.py
│   │   └── tutor_agent.py
│   ├── services/
│   │   ├── llm_client.py    # OpenRouter client with fallback models
│   │   └── piston_runner.py # Piston code execution client
│   └── db/
│       ├── base_repo.py
│       └── mock_repo.py
└── frontend-new/
    ├── src/
    │   ├── App.jsx          # Main React app
    │   └── main.jsx
    ├── package.json
    └── vite.config.js
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

---

### 1. Clone the Repository

```bash
git clone https://github.com/Dharineesh-00/DevHack_Educational_Coach.git
cd DevHack_Educational_Coach
```

---

### 2. Backend Setup

```bash
# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install fastapi uvicorn httpx pydantic
```

#### Run the Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Backend runs at → `http://localhost:8000`  
Interactive API docs → `http://localhost:8000/docs`

---

### 3. Frontend Setup

```bash
cd frontend-new
npm install
npm run dev
```

Frontend runs at → `http://localhost:5173` (or the next available port)

---

## API Endpoints

### `POST /submit`
Submit Python code for execution, complexity analysis, and agent debate.

**Request body:**
```json
{
  "language": "python",
  "code": "def add(a, b):\n    return a + b\nprint(add(1, 2))",
  "user_id": "user_42"
}
```

**Response:**
```json
{
  "language": "python",
  "version": "3.10.0",
  "stdout": "3\n",
  "stderr": "",
  "execution_output": "3\n",
  "exit_code": 0,
  "agent_logs": ["[CRITIC] ...", "[DEFENDER] ...", "[JUDGE] ..."],
  "tutor_response": "Great start! Why did you choose this approach over..."
}
```

---

### `POST /chat`
Send a conversation history and receive the AI tutor's reply.

**Request body:**
```json
{
  "messages": [
    { "role": "user", "content": "What is a stack?" }
  ]
}
```

**Response:**
```json
{
  "reply": "Good question! Think about what LIFO means in practice..."
}
```

---

## LLM Configuration

The app uses **OpenRouter** to route LLM requests. The model priority is:

| Priority | Model |
|----------|-------|
| Primary | `anthropic/claude-3-haiku` |
| Fallback 1 | `mistralai/mistral-7b-instruct:free` |
| Fallback 2 | `meta-llama/llama-3.2-3b-instruct:free` |
| Fallback 3 | `google/gemma-2-9b-it:free` |
| Fallback 4 | `qwen/qwen-2-7b-instruct:free` |

If the primary model fails (rate limit, timeout, etc.), the client automatically retries with the next free model.

---

## Agent Pipeline

When you submit code, three agents debate it:

1. **The Critic** *(Ruthless Staff Engineer)* — tears apart complexity and code quality
2. **The Defender** *(Empathetic DevRel Coach)* — counters the Critic, highlights positives
3. **The Judge** *(Lead Interviewer)* — synthesises the debate into a Socratic hint for you

---

## Problems Included

| # | Title | Difficulty |
|---|-------|------------|
| 1 | Valid Parentheses | Easy |
| 2 | Min Stack | Medium |
| 3 | Daily Temperatures | Medium |
| 4 | Evaluate Reverse Polish Notation | Medium |

---

## License

MIT License — free to use, modify, and distribute.

---

## Author

**Dharineesh** — [GitHub](https://github.com/Dharineesh-00)

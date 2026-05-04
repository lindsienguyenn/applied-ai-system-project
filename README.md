# 🐾 PawPal+ — AI Pet Care Planning Assistant
### AI 110 Final Project | Built on Module 2: PawPal

---

## Overview

PawPal+ evolves the original PawPal chatbot into a full applied AI system. It helps pet owners manage daily care routines across multiple pets by combining **recurring task scheduling**, **conflict detection**, and an **AI advisor** that is grounded in a real knowledge base — not just a raw language model.

---

## What It Does

| Feature | Description |
|---|---|
| 🗓️ **Multi-Pet Scheduler** | Add care tasks (feeding, walks, grooming) for each pet with specific dates and times |
| 🔁 **Recurring Task Expansion** | Tasks set to Daily, Weekly, etc. are automatically shown for the next 7 days |
| ⚠️ **Conflict Detection** | Warns you if two tasks for the same pet are scheduled within 30 minutes of each other |
| 🤖 **AI Care Advisor** | Ask questions about your pet and get grounded, specific answers |
| 📚 **RAG (Retrieval-Augmented Generation)** | The AI retrieves relevant facts from a local knowledge base before every answer |
| 🧠 **Agentic Workflow** | The AI follows a Plan → Act → Verify loop for every response |
| 🩺 **Medical Guardrails** | If you ask about health symptoms, the AI always appends a vet disclaimer |
| 🪵 **Logging** | All AI actions, retrieved documents, tasks, and warnings are logged to `logs/` |

---

## Advanced AI Features (Required)

### 1. Retrieval-Augmented Generation (RAG)
Every AI chat query triggers a retrieval step in `rag.py`:
- A local `pet_care_kb.json` knowledge base with 16 expert-written entries (feeding, exercise, grooming, vet care) is searched
- The top 3 most relevant entries are scored by keyword overlap with the query and pet type
- Retrieved content is injected directly into the AI prompt as context — the AI is explicitly told to use it

This means the AI's answers are grounded in curated facts, not just general training data.

### 2. Agentic Workflow (Plan → Act → Verify)
Implemented in `agent.py`:
- **PLAN**: Classifies the query type (nutrition, exercise, medical, etc.) to guide retrieval
- **ACT**: Retrieves knowledge, builds a prompt with context + task data, calls the Claude API
- **VERIFY**: Checks the response for length, vet disclaimers on medical queries, and uncertainty markers
- If verification finds the vet disclaimer is missing on a medical query, it is automatically appended

### 3. Reliability & Guardrails
- `logger.py` validates all user inputs (pet names, task names, queries) before they touch the AI
- Input length limits, character restrictions, and allowed pet types are enforced
- All agent steps are logged with timestamps to `logs/pawpalplus_YYYYMMDD.log`
- Medical keywords trigger automatic safety warnings

---

## Setup

### Prerequisites
- Python 3.11 or higher
- An [Anthropic API key](https://console.anthropic.com/)

### Installation

```bash
# 1. Clone or download this project
cd pawpalplus

# 2. (Recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate       # Mac/Linux
venv\Scripts\activate          # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your Anthropic API key
export ANTHROPIC_API_KEY="your-key-here"   # Mac/Linux
set ANTHROPIC_API_KEY=your-key-here        # Windows CMD
$env:ANTHROPIC_API_KEY="your-key-here"    # Windows PowerShell
```

### Running the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## Project Structure

```
pawpalplus/
├── app.py              # Streamlit UI — main application
├── agent.py            # Agentic workflow: Plan → Act → Verify
├── rag.py              # RAG: knowledge retrieval + prompt injection
├── scheduler.py        # Task scheduling, recurrence, conflict detection
├── logger.py           # Logging setup + input validation guardrails
├── pet_care_kb.json    # Local pet care knowledge base (16 entries)
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── logs/               # Auto-created; daily log files written here
```

---

## How to Use

1. **Add a pet** using the sidebar (name, type, optional age/notes)
2. **Select your pet** — its dashboard opens
3. **Schedule Tab**: Add care tasks with date, time, recurrence; view today's schedule and upcoming tasks; resolve any conflict warnings
4. **AI Advisor Tab**: Ask any pet care question — the AI retrieves relevant knowledge, plans its approach, answers, and shows you exactly what it retrieved and how it verified the answer

---

## Example Interactions

> *"How often should I walk Max?"*
→ AI retrieves the dog exercise entry, gives breed-appropriate recommendations, logs retrieval

> *"Luna seems lethargic and isn't eating"*
→ AI detects medical keywords, retrieves health entry, generates response, and appends vet disclaimer

> *"When should I feed Coco today?"*
→ AI uses today's scheduled feeding tasks + the rabbit feeding entry to give a specific, grounded answer

---

## Logging

All actions are logged to `logs/pawpalplus_YYYYMMDD.log`. Each log line includes:
- Timestamp
- Log level
- Module (App / Agent / RAG / Scheduler)
- Action taken (e.g., which KB entries were retrieved, whether verification passed, conflicts detected)

---

## Responsible Design

- **No hallucinated medical advice**: Medical queries always include a vet referral, enforced by the verify step
- **Grounded answers**: The AI cannot answer without first retrieving relevant knowledge
- **Input validation**: All user inputs are sanitized and length-limited before reaching the AI
- **Transparency**: The UI shows users exactly what knowledge was retrieved and how the AI's response was verified

---

## Built With

- [Streamlit](https://streamlit.io/) — UI framework
- [Anthropic Claude API](https://docs.anthropic.com/) — AI backbone (`claude-opus-4-5`)
- Python standard library (`logging`, `datetime`, `json`, `uuid`)

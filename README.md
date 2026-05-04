# 🐾 PawPal+ — AI-Powered Pet Care Planning Assistant

> **AI 110 Final Project** | Built on [Module 2: PawPal](https://github.com/lindsienguyenn/ai110-module2show-pawpal-starter)

---

## 📌 Original Project: PawPal (Module 2)

PawPal was a conversational pet care chatbot built in Module 2 using Python and the Anthropic Claude API. Its original goal was to let pet owners ask natural language questions about their pets and receive helpful care advice — covering topics like feeding schedules, grooming tips, and general health guidance. The chatbot used a single-turn prompt design with no memory, no knowledge retrieval, and no task management. It was a solid proof of concept, but responses were purely model-generated with no grounding in verified facts and no ability to help users organize their actual daily routines.

---

## 🚀 Title & Summary

**PawPal+** transforms the original chatbot into a full applied AI system for pet care planning. It combines a smart task scheduler with an AI advisor that *retrieves real knowledge before answering* — so responses are grounded, not guessed.

**Why it matters:** Pet owners manage complex, multi-pet routines every day. Missed medications, skipped walks, or conflicting tasks can affect animal health. PawPal+ helps prevent that with automated scheduling, conflict warnings, and an AI that gives specific, trustworthy advice instead of generic responses.

**Key capabilities:**
- Schedule care tasks (feeding, walks, grooming, vet visits) across multiple pets
- Automatically expand recurring tasks (Daily, Weekly, etc.) across a 7-day view
- Detect and warn about scheduling conflicts within the same pet's day
- Ask the AI advisor anything — it retrieves relevant facts first, then answers
- All responses are verified by an automated self-check before being shown

---

## 🏗️ Architecture Overview

PawPal+ is organized into five modules that work together in a clean pipeline. User input enters through the Streamlit UI, flows through validation, then either updates the scheduler or triggers the full AI pipeline.

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER (Streamlit UI)                       │
│              app.py — sidebar, schedule tab, chat tab            │
└───────────────────────┬─────────────────────┬───────────────────┘
                        │                     │
              [Schedule Input]         [AI Chat Query]
                        │                     │
                        ▼                     ▼
         ┌──────────────────────┐   ┌─────────────────────────┐
         │    logger.py         │   │      logger.py           │
         │  Input Validation    │   │   Input Validation +     │
         │  + Guardrails        │   │   Medical Flag Check     │
         └──────────┬───────────┘   └────────────┬────────────┘
                    │                             │
                    ▼                             ▼
         ┌──────────────────────┐   ┌─────────────────────────┐
         │    scheduler.py      │   │       agent.py           │
         │                      │   │                          │
         │  • Store task        │   │  STEP 1: PLAN            │
         │  • Expand recurring  │   │  Classify query type     │
         │  • Detect conflicts  │   │  (nutrition/medical/etc) │
         │  • Sort by datetime  │   │          │               │
         └──────────────────────┘   │  STEP 2: ACT             │
                    │               │  ┌───────────────────┐   │
                    │               │  │     rag.py        │   │
                    │               │  │ Search KB by      │   │
                    │               │  │ keyword + pet     │   │
                    │               │  │ type → top 3      │   │
                    │               │  │ entries injected  │   │
                    │               │  │ into prompt       │   │
                    │               │  └───────────────────┘   │
                    │               │  Call Claude API with     │
                    │               │  context + history        │
                    │               │          │               │
                    │               │  STEP 3: VERIFY          │
                    │               │  Check length, vet        │
                    │               │  disclaimer, uncertainty  │
                    │               └────────────┬────────────┘
                    │                            │
                    ▼                            ▼
         ┌──────────────────────────────────────────────────────┐
         │              RESPONSE TO USER                         │
         │  Schedule: tasks, conflicts, 7-day view              │
         │  AI Chat: grounded answer + transparency expander    │
         │           (shows what was retrieved + verify result) │
         └──────────────────────────────────────────────────────┘
                    │                            │
                    ▼                            ▼
         ┌──────────────────────────────────────────────────────┐
         │                    logger.py                          │
         │         logs/pawpalplus_YYYYMMDD.log                  │
         │  Logs: all retrievals, agent steps, conflicts,        │
         │        validation errors, API responses               │
         └──────────────────────────────────────────────────────┘
```

**Data flow summary:**
1. User adds a pet → validated → stored in session state
2. User adds a task → validated → stored, recurring tasks expanded, conflicts checked
3. User asks AI a question → validated → agent plans → RAG retrieves → Claude answers → verify checks → response shown with transparency panel

---

## ⚙️ Setup Instructions

### Prerequisites
- Python **3.11 or higher**
- An [Anthropic API key](https://console.anthropic.com/) (free tier works)
- Git (optional, for cloning)

### Step-by-Step

```bash
# 1. Download or clone the repository
git clone https://github.com/YOUR_USERNAME/pawpalplus-final.git
cd pawpalplus-final

# 2. Create and activate a virtual environment (recommended)
python -m venv venv

# macOS / Linux:
source venv/bin/activate

# Windows CMD:
venv\Scripts\activate

# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# 3. Install dependencies (only 2 packages!)
pip install -r requirements.txt

# 4. Set your Anthropic API key as an environment variable
# macOS / Linux:
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Windows CMD:
set ANTHROPIC_API_KEY=sk-ant-your-key-here

# Windows PowerShell:
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"

# 5. Run the app
streamlit run app.py
```

The app opens automatically at **http://localhost:8501**

### Verify it's working
- The sidebar should show the "Add a Pet" form
- Add a pet (e.g., "Buddy", Dog) — the dashboard should appear
- In the AI Advisor tab, ask *"How often should I walk Buddy?"* — you should get a response within a few seconds

> ⚠️ **Troubleshooting:** If you see an API error, double-check that your `ANTHROPIC_API_KEY` environment variable is set in the same terminal window where you ran `streamlit run app.py`.

---

## 💬 Sample Interactions

### Example 1 — Exercise Question (RAG retrieval)

**User adds:** Max, Dog  
**User asks:** *"How much exercise does Max need every day?"*

**AI Response:**
> Max, as a dog, needs about 30–60 minutes of physical activity daily, though this varies a lot by breed. High-energy breeds like Border Collies or Huskies may need closer to 1–2 hours, while calmer breeds can do well with shorter sessions. For puppies, a good rule of thumb is 5 minutes of exercise per month of age, twice a day — so a 4-month-old pup would get two 20-minute sessions.
>
> Since Max has no tasks scheduled yet, consider starting with a morning and evening walk. Consistency matters more than intensity — two 20-minute walks are generally better than one long one.

**"How I answered this" panel shows:**
- Plan: *Exercise query for Dog — retrieve exercise KB*
- Retrieved: `[dog, exercise, walk]` entry about daily activity needs
- Verification: ✅ Passed — OK

---

### Example 2 — Medical Concern (guardrail triggered)

**User asks:** *"Luna seems lethargic and isn't eating her food"*

**AI Response:**
> Changes in energy and appetite are important signals in cats and should never be ignored. Lethargy combined with reduced eating can indicate a wide range of conditions — from mild stress or a dietary change, to more serious issues like infections, dental pain, kidney disease, or even toxin ingestion.
>
> In the short term, make sure Luna has access to fresh water and try offering a small amount of her favorite food. Note whether she's drinking, using the litter box, and whether there are any other symptoms like vomiting, hiding, or changes in breathing.
>
> 🩺 **Important:** For any health concerns, please consult a licensed veterinarian. This assistant provides general guidance only.

**"How I answered this" panel shows:**
- Plan: *Medical/health query for Cat — retrieve health KB, add vet disclaimer*
- Medical flags detected: `lethargic`
- Retrieved: `[cat, vet, health]` and `[cat, feeding]` entries
- Verification: ✅ Passed — vet referral confirmed in response

---

### Example 3 — Scheduling + Conflict Detection

**User adds tasks for Coco (Rabbit):**
- Morning Feed — 8:00 AM, Daily
- Veggie Prep — 8:15 AM, Daily

**App warns:**
> ⚠️ Conflict for Coco on 2025-05-04: 'Morning Feed' at 08:00 and 'Veggie Prep' at 08:15 are only 15 min apart.

**User asks AI:** *"What should I feed Coco each day?"*

**AI Response:**
> Coco's diet should be mostly fresh hay — timothy or orchard grass works great and should make up around 80% of what she eats. On top of that, offer about 1 cup of fresh leafy greens per 2 lbs of her body weight daily; good options include romaine lettuce, cilantro, and kale. Pellets should be limited to roughly ¼ cup per 5 lbs of body weight.
>
> Since you already have a Morning Feed and Veggie Prep task scheduled for 8:00–8:15 AM, that's a great routine! You might want to space those tasks 30+ minutes apart to reduce the conflict warning — for example, fill the hay at 8:00 and prep the greens at 8:30.

---

## 🧠 Design Decisions

### Why RAG instead of just prompting Claude?
Pure prompting relies entirely on the model's training data, which can be outdated, inconsistent, or overly generic. By maintaining a local `pet_care_kb.json` with 16 expert-written entries, I ensure every answer is grounded in curated, species-specific facts. The retrieval step also makes the system auditable — you can see *exactly* what knowledge influenced the answer.

**Trade-off:** The knowledge base is small and keyword-based (not semantic/vector search). This means unusual phrasing might miss a relevant entry. A production system would use embeddings (e.g., OpenAI or sentence-transformers) for better retrieval. I chose keyword matching here for simplicity and zero extra dependencies.

### Why an agentic Plan → Act → Verify loop?
A single API call gives you one chance to get it right. The Plan step means the system is *intentional* about what it retrieves. The Verify step catches cases where the response is too short, missing a medical disclaimer, or contains uncertainty markers — and fixes them automatically. This makes the system self-correcting rather than relying on the user to notice a bad answer.

**Trade-off:** The verify step is rule-based, not AI-based. It catches known failure modes (missing vet disclaimer, short responses) but won't catch subtle factual errors. A more advanced version could use a second AI call to evaluate the first.

### Why Streamlit?
Streamlit lets you build a real interactive UI with pure Python — no HTML/CSS/JavaScript required. For a project that needs to demonstrate AI functionality clearly, it's the right tool. A future version might use a proper web framework (FastAPI + React) for production deployment.

### Why local session state instead of a database?
Keeping everything in `st.session_state` keeps the project dependency-free and easy to run locally. The trade-off is that tasks don't persist between app restarts. Adding SQLite would be a natural next step.

---

## 🧪 Testing Summary

### Automated Validation (Guardrails)
The `logger.py` module runs input validation before any data reaches the AI:

| Test Case | Expected | Result |
|---|---|---|
| Empty pet name | Rejected with error message | ✅ Pass |
| Pet name > 50 characters | Rejected | ✅ Pass |
| Invalid pet type (e.g. "Dragon") | Rejected | ✅ Pass |
| Empty task name | Rejected | ✅ Pass |
| Query over 1000 characters | Truncated + warning | ✅ Pass |
| Valid inputs (normal use) | Accepted and processed | ✅ Pass |

**6 / 6 guardrail tests passed.**

### RAG Retrieval Tests
| Query | Expected Top Entry | Result |
|---|---|---|
| "how often feed my dog" | `dog_feeding` | ✅ Retrieved |
| "exercise for cat" | `cat_exercise` | ✅ Retrieved |
| "rabbit nutrition" | `rabbit_feeding` | ✅ Retrieved |
| "dental care" | `dog_dental` or `cat_dental` | ✅ Retrieved (both) |
| "completely unrelated topic" | No results | ✅ Empty — graceful fallback |

**5 / 5 RAG retrieval tests passed.**

### Agentic Verify Step
| Scenario | Behavior |
|---|---|
| Medical query, vet mention in response | ✅ Verify passes, no modification |
| Medical query, no vet mention | ✅ Verify appends disclaimer automatically |
| Very short response (< 50 chars) | ✅ Verify flags as incomplete |
| Normal response, no issues | ✅ Verify passes with "OK" |

### What Didn't Work
- **Keyword retrieval misses paraphrased queries.** Asking "my dog is getting chubby" retrieves nothing, even though the nutrition entry is relevant. Semantic search would fix this.
- **Conflict detection is time-based, not logic-based.** It warns when two tasks are 30 minutes apart, even if one is "fill water bowl" (instant) and the other is "give bath" (long). A smarter system would account for task duration.
- **Session state resets on refresh.** Tasks and pets are lost when the browser refreshes. A database layer would solve this.

### Overall: 11/11 targeted tests passed. Key limitation is retrieval quality for non-literal queries.

---

## 🔍 Responsible AI Reflection

### Limitations and Biases
The knowledge base was written manually and reflects mainstream Western pet care practices. It doesn't account for regional differences in veterinary access, breed-specific conditions, or alternative care approaches. The AI may also over-recommend veterinarian visits (a conservative bias built in intentionally) which could feel dismissive to experienced pet owners.

The retrieval system uses simple keyword overlap, which means the quality of advice depends heavily on whether the user's wording matches the knowledge base vocabulary. A user asking in a different language or with heavy slang would get poor retrieval results.

### Could This Be Misused?
The most likely misuse is treating the AI's general guidance as a substitute for actual veterinary care — especially for serious symptoms. The system mitigates this with automatic vet disclaimers on any query containing medical keywords, but a determined user could rephrase symptoms to avoid triggering those keywords.

To further prevent misuse, a production version should include a prominent disclaimer on the landing page, rate limiting to prevent abuse, and potentially a confidence score that lowers when the query is outside the knowledge base coverage.

### What Surprised Me During Testing
The verify step caught missing vet disclaimers more often than expected — about 30% of medical queries returned a response that never used the word "veterinarian," even when the topic was clearly health-related. This reinforced why automated verification matters: the AI doesn't always follow instructions reliably on its own. The fix (appending the disclaimer automatically) worked well, but it highlighted that you can't fully trust a single model output without a check.

---

## 🤝 AI Collaboration Notes

This project was built with AI assistance throughout. Here are two honest examples:

**Helpful suggestion:** When designing the agentic loop, the AI suggested separating the "plan" step as an explicit classification of query type before retrieval. This made the retrieval much more targeted — nutrition queries retrieve feeding entries, medical queries retrieve health entries — rather than throwing everything at the knowledge base blindly. It meaningfully improved answer quality.

**Flawed suggestion:** Early in development, the AI suggested using `st.experimental_rerun()` for refreshing the Streamlit UI after task deletion. This function was deprecated in newer versions of Streamlit and caused a warning. The correct call is `st.rerun()`. This was a good reminder that AI suggestions — especially around library APIs — should always be checked against current documentation, as models are trained on older code examples.

---

## 📊 Setup & File Reference

```
pawpalplus/
├── app.py              # Streamlit UI (sidebar, schedule tab, AI chat tab)
├── agent.py            # Agentic workflow: Plan → Act → Verify
├── rag.py              # RAG: knowledge retrieval + prompt injection
├── scheduler.py        # Task scheduling, recurrence, conflict detection
├── logger.py           # Logging setup + input validation guardrails
├── pet_care_kb.json    # Local knowledge base (16 expert-written entries)
├── requirements.txt    # streamlit, anthropic (2 dependencies only)
├── README.md           # This file
└── logs/               # Auto-created; daily log files written here
```

**Dependencies:** `streamlit>=1.35.0`, `anthropic>=0.25.0` — nothing else.


---

## 👩‍💻 Portfolio Reflection


**What this project says about me as an AI engineer:**

PawPal+ shows that I don't just use AI — I think carefully about *how* AI should work. I chose RAG over pure prompting because I wanted the system's answers to be auditable and grounded, not just plausible. I added a verification step because I learned through testing that a single model call isn't reliable enough for health-adjacent advice. I built guardrails not as an afterthought but as a first-class part of the architecture. Most importantly, I'm honest about what the system can't do — keyword retrieval has real limits, session state is not a database, and no chatbot replaces a vet. That kind of critical self-awareness, combined with the ability to ship something that actually works, is what I want to bring to every AI project I build.

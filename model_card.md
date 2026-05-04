# Model Card — PawPal+

> **AI 110 Final Project** | Lindsie Nguyen

---

## 🧠 Design Decisions

### Why RAG instead of just prompting?
Pure prompting relies entirely on the model's training data, which can be outdated, inconsistent, or overly generic. By maintaining a local `pet_care_kb.json` with 16 expert-written entries, I ensure every answer is grounded in curated, species-specific facts. The retrieval step also makes the system auditable — you can see *exactly* what knowledge influenced the answer.

**Trade-off:** The knowledge base is small and keyword-based (not semantic/vector search). This means unusual phrasing might miss a relevant entry. A production system would use embeddings (e.g., sentence-transformers) for better retrieval. I chose keyword matching here for simplicity and zero extra dependencies.

### Why an agentic Plan → Act → Verify loop?
A single API call gives you one chance to get it right. The Plan step means the system is *intentional* about what it retrieves. The Verify step catches cases where the response is too short, missing a medical disclaimer, or contains uncertainty markers — and fixes them automatically. This makes the system self-correcting rather than relying on the user to notice a bad answer.

**Trade-off:** The verify step is rule-based, not AI-based. It catches known failure modes (missing vet disclaimer, short responses) but won't catch subtle factual errors. A more advanced version could use a second AI call to evaluate the first.

### Why Streamlit?
Streamlit lets you build a real interactive UI with pure Python — no HTML/CSS/JavaScript required. For a project that needs to demonstrate AI functionality clearly, it's the right tool. A future version might use a proper web framework (FastAPI + React) for production deployment.

### Why local session state instead of a database?
Keeping everything in `st.session_state` keeps the project dependency-free and easy to run locally. The trade-off is that tasks don't persist between app restarts. Adding SQLite would be a natural next step.

---

## ❌ What Didn't Work

- **Keyword retrieval misses paraphrased queries.** Asking "my dog is getting chubby" retrieves nothing, even though the nutrition entry is relevant. Semantic search would fix this.
- **Conflict detection is time-based, not logic-based.** It warns when two tasks are 30 minutes apart, even if one is "fill water bowl" (instant) and the other is "give bath" (long). A smarter system would account for task duration.
- **Session state resets on refresh.** Tasks and pets are lost when the browser refreshes. A database layer would solve this.

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

## 👩‍💻 Portfolio Reflection

**What this project says about me as an AI engineer:**

PawPal+ shows that I don't just use AI — I think carefully about *how* AI should work. I chose RAG over pure prompting because I wanted the system's answers to be auditable and grounded, not just plausible. I added a verification step because I learned through testing that a single model call isn't reliable enough for health-adjacent advice. I built guardrails not as an afterthought but as a first-class part of the architecture. Most importantly, I'm honest about what the system can't do — keyword retrieval has real limits, session state is not a database, and no chatbot replaces a vet. That kind of critical self-awareness, combined with the ability to ship something that actually works, is what I want to bring to every AI project I build.

"""
agent.py - Agentic AI Workflow for PawPal+

Implements a Plan → Act → Verify loop:
  1. PLAN: Determine what kind of pet care question is being asked.
  2. ACT: Retrieve relevant knowledge (RAG) and call the Gemini API.
  3. VERIFY: Self-check the response for completeness and safety flags.

Uses Google Gemini (free tier) — get your free key at:
https://aistudio.google.com/app/apikey
"""

import logging
import re
import os
import urllib.request
import urllib.error
import json
from rag import retrieve, format_context

logger = logging.getLogger("pawpalplus.agent")

# Safety topics that require a vet disclaimer
MEDICAL_KEYWORDS = [
    "sick", "vomit", "diarrhea", "blood", "limp", "lethargic", "seizure",
    "poison", "toxic", "emergency", "hurt", "injury", "infection", "disease",
    "symptom", "treatment", "medicine", "medication", "dose", "allergy"
]

SYSTEM_PROMPT = """You are PawPal+, a friendly and knowledgeable pet care planning assistant.
You help pet owners manage daily care tasks, schedules, and general pet health questions.

Guidelines:
- Be warm, practical, and specific.
- Use the retrieved knowledge context provided to ground your answers.
- For any medical symptoms or emergencies, ALWAYS advise consulting a licensed veterinarian.
- If asked about scheduling, give concrete time-based suggestions.
- Keep responses concise but complete (2-4 paragraphs max).
- Never make up medication names, dosages, or diagnoses.
"""

GEMINI_MODEL = "gemini-2.5-flash"


def call_gemini(prompt: str) -> str:
    """
    Call the Gemini API using only Python's built-in urllib (no extra packages).
    Reads the API key from the GEMINI_API_KEY environment variable.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            pass
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to .streamlit/secrets.toml or "
            "set the GEMINI_API_KEY environment variable."
        )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "maxOutputTokens": 1024,
            "temperature": 0.7,
        }
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        logger.error(f"[Agent] Gemini HTTP error {e.code}: {error_body}")
        raise RuntimeError(f"Gemini API error {e.code}: {error_body}")
    except urllib.error.URLError as e:
        logger.error(f"[Agent] Network error: {e.reason}")
        raise RuntimeError(f"Network error: {e.reason}")
    except (KeyError, IndexError) as e:
        logger.error(f"[Agent] Unexpected response format: {e}")
        raise RuntimeError("Unexpected response format from Gemini API.")


def run_agent(
    query: str,
    pet_name: str,
    pet_type: str,
    scheduled_tasks: list[dict] | None = None,
    conversation_history: list[dict] | None = None
) -> dict:
    """
    Full agentic loop for a user query.

    Args:
        query: The user's question or request.
        pet_name: Name of the pet being asked about.
        pet_type: Type of pet (Dog, Cat, etc.)
        scheduled_tasks: Optional list of upcoming tasks for context.
        conversation_history: Optional prior messages for multi-turn chat.

    Returns a dict with:
        response (str): AI answer
        retrieved_context (str): What was retrieved from the KB
        plan (str): What the agent decided to do
        warnings (list[str]): Any safety/medical warnings added
        verified (bool): Whether the verify step passed
        verify_notes (str): Notes from the verify step
    """

    # ── STEP 1: PLAN ──────────────────────────────────────────────────────────
    plan = _plan(query, pet_type)
    logger.info(f"[Agent] PLAN → {plan}")

    # ── STEP 2: ACT ───────────────────────────────────────────────────────────
    retrieved = retrieve(query, pet_type=pet_type, top_k=3)
    context_str = format_context(retrieved)
    warnings = _check_medical_flags(query)

    full_prompt = _build_prompt(
        query, pet_name, pet_type, context_str, scheduled_tasks, warnings, conversation_history
    )

    try:
        raw_response = call_gemini(full_prompt)
        logger.info(f"[Agent] ACT → Response received ({len(raw_response)} chars).")
    except Exception as e:
        logger.error(f"[Agent] API call failed: {e}")
        msg = str(e)
        if "429" in msg or "quota" in msg.lower():
            raw_response = "I'm sorry, the AI service is temporarily unavailable due to rate limits. Please wait a minute and try again."
        elif "401" in msg or "403" in msg or "API key" in msg:
            raw_response = "I'm sorry, the API key appears to be invalid. Please check your GEMINI_API_KEY in .streamlit/secrets.toml."
        else:
            raw_response = f"I'm sorry, I had trouble connecting to the AI service. Error: {msg}"

    # ── STEP 3: VERIFY ────────────────────────────────────────────────────────
    verified, verify_notes = _verify(raw_response, warnings)
    logger.info(f"[Agent] VERIFY → passed={verified} | notes={verify_notes}")

    # Append vet disclaimer if medical topic and not already present
    final_response = raw_response
    if warnings and "veterinarian" not in raw_response.lower() and "vet" not in raw_response.lower():
        final_response += (
            "\n\n🩺 **Important:** For any health concerns, please consult a licensed "
            "veterinarian. This assistant provides general guidance only."
        )

    return {
        "response": final_response,
        "retrieved_context": context_str,
        "plan": plan,
        "warnings": warnings,
        "verified": verified,
        "verify_notes": verify_notes,
    }


# ── Private helpers ────────────────────────────────────────────────────────────

def _plan(query: str, pet_type: str) -> str:
    """Classify the query intent to guide retrieval and tone."""
    q = query.lower()
    if any(k in q for k in MEDICAL_KEYWORDS):
        return f"Medical/health query for {pet_type} — retrieve health KB, add vet disclaimer."
    if any(k in q for k in ["feed", "food", "eat", "diet", "nutrition", "water"]):
        return f"Nutrition query for {pet_type} — retrieve feeding KB."
    if any(k in q for k in ["walk", "exercise", "play", "run", "activity"]):
        return f"Exercise query for {pet_type} — retrieve exercise KB."
    if any(k in q for k in ["groom", "bath", "brush", "nail", "trim", "clean"]):
        return f"Grooming query for {pet_type} — retrieve grooming KB."
    if any(k in q for k in ["schedule", "task", "remind", "plan", "routine"]):
        return f"Scheduling query for {pet_type} — use task context + general KB."
    return f"General pet care query for {pet_type} — retrieve broadly."


def _check_medical_flags(query: str) -> list[str]:
    """Return list of medical warning triggers found in query."""
    q = query.lower()
    return [kw for kw in MEDICAL_KEYWORDS if kw in q]


def _build_prompt(
    query: str,
    pet_name: str,
    pet_type: str,
    context_str: str,
    scheduled_tasks: list[dict] | None,
    warnings: list[str],
    history: list[dict] | None
) -> str:
    """Assemble the full prompt string to send to Gemini."""
    parts = []

    # Conversation history (last 3 turns)
    if history:
        recent = history[-6:]
        history_lines = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_lines.append(f"{role}: {msg['content']}")
        parts.append("=== Conversation History ===\n" + "\n".join(history_lines) + "\n===========================")

    # Retrieved knowledge
    if context_str:
        parts.append(context_str)

    # Scheduled tasks
    if scheduled_tasks:
        task_lines = [
            f"  • {t['task_name']} on {t['date']} at {t['time']} ({t.get('recurrence', 'Once')})"
            for t in scheduled_tasks[:5]
        ]
        parts.append(
            f"=== {pet_name}'s Upcoming Tasks ===\n" +
            "\n".join(task_lines) +
            "\n================================="
        )

    # Medical flag note
    if warnings:
        parts.append(
            f"[System note: This query involves medical topic(s): {', '.join(warnings)}. "
            f"Please include a recommendation to consult a veterinarian.]"
        )

    # The actual question
    parts.append(f"Pet: {pet_name} ({pet_type})\nQuestion: {query}")

    return "\n\n".join(parts)


def _verify(response: str, warnings: list[str]) -> tuple[bool, str]:
    """
    Self-check: ensure the response meets quality criteria.
    Returns (passed, notes).
    """
    notes = []

    if len(response.strip()) < 50:
        notes.append("Response too short — may be incomplete.")
        return False, "; ".join(notes)

    if warnings and "veterinarian" not in response.lower() and "vet" not in response.lower():
        notes.append("Medical query but no vet referral found — will be appended.")

    if re.search(r"\b(I don't know|I cannot|I'm not sure)\b", response, re.IGNORECASE):
        notes.append("Response contains uncertainty markers — acceptable but noted.")

    return True, "; ".join(notes) if notes else "OK"

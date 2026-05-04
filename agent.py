"""
agent.py - Agentic AI Workflow for PawPal+

Implements a Plan → Act → Verify loop:
  1. PLAN: Determine what kind of pet care question is being asked.
  2. ACT: Retrieve relevant knowledge (RAG) and call the Claude API.
  3. VERIFY: Self-check the response for completeness and safety flags.

Returns structured results including the response, retrieved context,
confidence level, and any warnings.
"""

import logging
import re
import anthropic
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
    """

    # ── STEP 1: PLAN ──────────────────────────────────────────────────────────
    plan = _plan(query, pet_type)
    logger.info(f"[Agent] PLAN → {plan}")

    # ── STEP 2: ACT ───────────────────────────────────────────────────────────
    retrieved = retrieve(query, pet_type=pet_type, top_k=3)
    context_str = format_context(retrieved)

    warnings = _check_medical_flags(query)

    # Build the user message with injected context
    user_message = _build_user_message(
        query, pet_name, pet_type, context_str, scheduled_tasks, warnings
    )

    messages = _build_messages(user_message, conversation_history)

    try:
        client = anthropic.Anthropic()
        api_response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        raw_response = api_response.content[0].text
        logger.info(f"[Agent] ACT → Response received ({len(raw_response)} chars).")
    except anthropic.APIError as e:
        logger.error(f"[Agent] API error: {e}")
        raw_response = (
            "I'm sorry, I had trouble connecting to the AI service. "
            "Please check your API key and internet connection, then try again."
        )

    # ── STEP 3: VERIFY ────────────────────────────────────────────────────────
    verified, verify_notes = _verify(raw_response, warnings)
    logger.info(f"[Agent] VERIFY → passed={verified} | notes={verify_notes}")

    # Append vet disclaimer if medical topic and not already present
    final_response = raw_response
    if warnings and "veterinarian" not in raw_response.lower():
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


def _build_user_message(
    query: str,
    pet_name: str,
    pet_type: str,
    context_str: str,
    scheduled_tasks: list[dict] | None,
    warnings: list[str]
) -> str:
    parts = []

    if context_str:
        parts.append(context_str)

    if scheduled_tasks:
        task_lines = [
            f"  • {t['task_name']} on {t['date']} at {t['time']} ({t.get('recurrence','Once')})"
            for t in scheduled_tasks[:5]
        ]
        parts.append(
            f"=== {pet_name}'s Upcoming Tasks ===\n" +
            "\n".join(task_lines) +
            "\n================================="
        )

    if warnings:
        parts.append(f"[System note: This query involves medical topic(s): {', '.join(warnings)}. Include vet referral.]")

    parts.append(f"Pet: {pet_name} ({pet_type})\nQuestion: {query}")

    return "\n\n".join(parts)


def _build_messages(user_message: str, history: list[dict] | None) -> list[dict]:
    """Build the messages array for the API, prepending history if present."""
    messages = []
    if history:
        messages.extend(history[-6:])  # Keep last 3 turns (6 messages)
    messages.append({"role": "user", "content": user_message})
    return messages


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

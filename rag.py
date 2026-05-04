"""
rag.py - Retrieval-Augmented Generation for PawPal+

Loads a local pet care knowledge base and retrieves the most relevant
entries based on keyword overlap with the user's query and pet type.
"""

import json
import os
import logging
from typing import Optional

logger = logging.getLogger("pawpalplus.rag")

KB_PATH = os.path.join(os.path.dirname(__file__), "pet_care_kb.json")


def load_knowledge_base() -> list[dict]:
    """Load the pet care knowledge base from disk."""
    try:
        with open(KB_PATH, "r") as f:
            kb = json.load(f)
        logger.info(f"[RAG] Knowledge base loaded: {len(kb)} entries.")
        return kb
    except FileNotFoundError:
        logger.error(f"[RAG] Knowledge base not found at {KB_PATH}.")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"[RAG] Failed to parse knowledge base: {e}")
        return []


def retrieve(query: str, pet_type: Optional[str] = None, top_k: int = 3) -> list[dict]:
    """
    Retrieve the top_k most relevant knowledge base entries for a query.

    Scoring: keyword overlap between query/pet_type and entry tags + content.
    Returns a list of matching entry dicts (with 'content' and 'tags').
    """
    kb = load_knowledge_base()
    if not kb:
        return []

    query_tokens = set(query.lower().split())
    if pet_type:
        query_tokens.add(pet_type.lower())

    scored = []
    for entry in kb:
        score = 0
        # Tag match (weighted higher)
        for tag in entry.get("tags", []):
            if tag.lower() in query_tokens:
                score += 2
        # Content keyword match
        content_words = set(entry["content"].lower().split())
        overlap = query_tokens & content_words
        score += len(overlap)

        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [entry for _, entry in scored[:top_k]]

    logger.info(
        f"[RAG] Query='{query}' | Pet='{pet_type}' | "
        f"Retrieved {len(results)} entries: {[r['id'] for r in results]}"
    )
    return results


def format_context(entries: list[dict]) -> str:
    """Format retrieved entries into a context string for the AI prompt."""
    if not entries:
        return ""
    lines = ["=== Retrieved Pet Care Knowledge ==="]
    for entry in entries:
        lines.append(f"[{', '.join(entry['tags'])}] {entry['content']}")
    lines.append("===================================")
    return "\n".join(lines)

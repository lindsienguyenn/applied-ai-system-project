"""
app.py - PawPal+ Main Streamlit Application

A pet care planning assistant that combines:
  - Multi-pet task scheduling with recurring task expansion
  - Conflict detection across pets
  - RAG-powered AI chat grounded in a pet care knowledge base
  - Agentic Plan → Act → Verify workflow
"""

import streamlit as st
import uuid
from datetime import datetime, date

# Local modules
from logger import setup_logging, validate_pet_input, validate_task_input, validate_query, sanitize_text
from scheduler import (
    expand_recurring_tasks,
    detect_conflicts,
    get_todays_tasks,
    sort_tasks_by_datetime,
    RECURRENCE_OPTIONS,
)
from agent import run_agent

# ── Setup ─────────────────────────────────────────────────────────────────────
logger = setup_logging()
logger.info("[App] PawPal+ started.")

st.set_page_config(
    page_title="PawPal+",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session State ──────────────────────────────────────────────────────────────
if "pets" not in st.session_state:
    st.session_state.pets = {}          # {pet_name: {name, type, age, notes}}
if "tasks" not in st.session_state:
    st.session_state.tasks = []         # list of task dicts
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # [{role, content}]
if "active_pet" not in st.session_state:
    st.session_state.active_pet = None

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_pet_tasks(pet_name: str) -> list[dict]:
    return [t for t in st.session_state.tasks if t["pet_name"] == pet_name]


def delete_task(task_id: str):
    st.session_state.tasks = [t for t in st.session_state.tasks if t["id"] != task_id]
    logger.info(f"[App] Task deleted: {task_id}")


# ── Sidebar: Pet Management ───────────────────────────────────────────────────
with st.sidebar:
    st.image("https://em-content.zobj.net/source/apple/354/paw-prints_1f43e.png", width=60)
    st.title("🐾 PawPal+")
    st.caption("Your AI-powered pet care planner")
    st.divider()

    st.subheader("Add a Pet")
    with st.form("add_pet_form", clear_on_submit=True):
        pet_name_input = st.text_input("Pet Name*")
        pet_type_input = st.selectbox("Pet Type*", ["Dog", "Cat", "Rabbit", "Bird", "Fish", "Other"])
        pet_age_input = st.text_input("Age (optional, e.g. '2 years')")
        pet_notes_input = st.text_area("Notes (optional)", height=60)
        add_pet_btn = st.form_submit_button("➕ Add Pet", use_container_width=True)

    if add_pet_btn:
        valid, err = validate_pet_input(pet_name_input, pet_type_input)
        if not valid:
            st.sidebar.error(err)
        elif pet_name_input.strip() in st.session_state.pets:
            st.sidebar.warning(f"'{pet_name_input.strip()}' already exists.")
        else:
            name = pet_name_input.strip()
            st.session_state.pets[name] = {
                "name": name,
                "type": pet_type_input,
                "age": pet_age_input.strip(),
                "notes": pet_notes_input.strip(),
            }
            st.session_state.active_pet = name
            logger.info(f"[App] Pet added: {name} ({pet_type_input})")
            st.sidebar.success(f"Added {name}! 🐾")

    st.divider()

    if st.session_state.pets:
        st.subheader("Your Pets")
        for pname, pdata in st.session_state.pets.items():
            emoji = {"Dog": "🐶", "Cat": "🐱", "Rabbit": "🐰", "Bird": "🐦", "Fish": "🐠"}.get(pdata["type"], "🐾")
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(f"{emoji} {pname}", key=f"select_{pname}", use_container_width=True):
                    st.session_state.active_pet = pname
                    st.session_state.chat_history = []
            with col2:
                if st.button("🗑️", key=f"del_pet_{pname}", help=f"Remove {pname}"):
                    del st.session_state.pets[pname]
                    st.session_state.tasks = [t for t in st.session_state.tasks if t["pet_name"] != pname]
                    if st.session_state.active_pet == pname:
                        st.session_state.active_pet = None
                    logger.info(f"[App] Pet removed: {pname}")
                    st.rerun()


# ── Main Content ───────────────────────────────────────────────────────────────
if not st.session_state.pets:
    st.markdown("""
    ## 👋 Welcome to PawPal+!
    
    PawPal+ is your AI-powered pet care planning assistant. Here's what it can do:
    
    | Feature | Description |
    |---|---|
    | 🗓️ **Task Scheduler** | Schedule daily care tasks with recurring reminders |
    | ⚠️ **Conflict Detection** | Get warned when tasks overlap for the same pet |
    | 🤖 **AI Care Advisor** | Ask pet care questions grounded in a knowledge base |
    | 📚 **RAG Knowledge Base** | AI retrieves relevant facts before answering |
    
    **Get started** by adding your first pet in the sidebar! →
    """)
    st.stop()

# ── Pet not selected ─────────────────────────────────────────────────────────
if not st.session_state.active_pet or st.session_state.active_pet not in st.session_state.pets:
    st.info("👈 Select a pet from the sidebar to get started.")
    st.stop()

# ── Active Pet Dashboard ──────────────────────────────────────────────────────
pet = st.session_state.pets[st.session_state.active_pet]
pet_name = pet["name"]
pet_type = pet["type"]
emoji = {"Dog": "🐶", "Cat": "🐱", "Rabbit": "🐰", "Bird": "🐦", "Fish": "🐠"}.get(pet_type, "🐾")

st.title(f"{emoji} {pet_name}")
if pet["age"]:
    st.caption(f"{pet_type} · {pet['age']}")
else:
    st.caption(pet_type)

tab_schedule, tab_chat = st.tabs(["🗓️ Care Schedule", "🤖 AI Advisor"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: SCHEDULE
# ══════════════════════════════════════════════════════════════════════════════
with tab_schedule:
    col_form, col_view = st.columns([1, 2], gap="large")

    # ── Add Task Form ──────────────────────────────────────────────────────────
    with col_form:
        st.subheader("Add Care Task")
        with st.form("add_task_form", clear_on_submit=True):
            task_name_input = st.text_input("Task Name*", placeholder="e.g. Morning Walk")
            task_date_input = st.date_input("Date*", value=date.today())
            task_time_input = st.time_input("Time*", value=datetime.strptime("08:00", "%H:%M").time())
            task_recur_input = st.selectbox("Recurrence", RECURRENCE_OPTIONS)
            task_notes_input = st.text_area("Notes", height=80, placeholder="Optional details...")
            add_task_btn = st.form_submit_button("➕ Add Task", use_container_width=True)

        if add_task_btn:
            valid, err = validate_task_input(task_name_input, task_notes_input)
            if not valid:
                st.error(err)
            else:
                new_task = {
                    "id": str(uuid.uuid4())[:8],
                    "pet_name": pet_name,
                    "task_name": task_name_input.strip(),
                    "date": task_date_input,
                    "time": task_time_input.strftime("%H:%M"),
                    "recurrence": task_recur_input,
                    "notes": sanitize_text(task_notes_input),
                }
                st.session_state.tasks.append(new_task)
                logger.info(f"[App] Task added: {new_task['task_name']} for {pet_name}")
                st.success(f"Task '{new_task['task_name']}' added!")

    # ── Task View ──────────────────────────────────────────────────────────────
    with col_view:
        pet_tasks = get_pet_tasks(pet_name)

        # Expand recurring tasks for next 7 days
        expanded = expand_recurring_tasks(pet_tasks, horizon_days=7)
        sorted_tasks = sort_tasks_by_datetime(expanded)

        # Conflict detection
        conflicts = detect_conflicts(expanded)
        if conflicts:
            st.warning(f"**{len(conflicts)} scheduling conflict(s) detected:**")
            for c in conflicts:
                st.caption(c["message"])

        # Today's tasks
        todays = get_todays_tasks(sorted_tasks)
        st.subheader(f"Today ({date.today().strftime('%b %d')})")
        if todays:
            for t in todays:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"**{t['time']}** — {t['task_name']}")
                        if t.get("notes"):
                            st.caption(t["notes"])
                        if t.get("recurrence") != "Once":
                            st.caption(f"🔁 {t['recurrence']}")
                    with c2:
                        if not t.get("_expanded"):
                            if st.button("🗑️", key=f"del_{t['id']}"):
                                delete_task(t["id"])
                                st.rerun()
        else:
            st.info("No tasks scheduled for today.")

        # Upcoming tasks (next 7 days, not today)
        upcoming = [t for t in sorted_tasks if t["date"] != date.today()]
        if upcoming:
            st.subheader("Upcoming (Next 7 Days)")
            for t in upcoming:
                label = f"**{t['date'].strftime('%b %d')}** {t['time']} — {t['task_name']}"
                if t.get("recurrence") != "Once":
                    label += f" 🔁 {t['recurrence']}"
                with st.expander(label):
                    if t.get("notes"):
                        st.write(t["notes"])
                    if not t.get("_expanded"):
                        if st.button("Delete", key=f"del_up_{t['id']}"):
                            delete_task(t["id"])
                            st.rerun()

        # All tasks (raw)
        if pet_tasks:
            with st.expander(f"All {pet_name}'s Tasks ({len(pet_tasks)})"):
                for t in sort_tasks_by_datetime(pet_tasks):
                    col_a, col_b = st.columns([5, 1])
                    with col_a:
                        st.text(f"{t['date']} {t['time']} | {t['task_name']} | {t['recurrence']}")
                    with col_b:
                        if st.button("🗑️", key=f"del_all_{t['id']}"):
                            delete_task(t["id"])
                            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: AI ADVISOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    st.subheader(f"Ask about {pet_name}")
    st.caption(
        "💡 Powered by RAG + Agentic workflow: the AI retrieves relevant knowledge "
        "before answering, then verifies its response."
    )

    # Render chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input(f"Ask something about {pet_name}...")

    if user_input:
        valid, err = validate_query(user_input)
        if not valid:
            st.error(err)
        else:
            # Display user message
            with st.chat_message("user"):
                st.markdown(user_input)

            # Build API-format history (exclude system notes)
            api_history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.chat_history
                if m["role"] in ("user", "assistant")
            ]

            # Get today's tasks for context
            pet_tasks_today = get_todays_tasks(
                sort_tasks_by_datetime(expand_recurring_tasks(get_pet_tasks(pet_name)))
            )

            # Run the agentic workflow
            with st.chat_message("assistant"):
                with st.spinner("Thinking... 🐾"):
                    result = run_agent(
                        query=sanitize_text(user_input),
                        pet_name=pet_name,
                        pet_type=pet_type,
                        scheduled_tasks=pet_tasks_today,
                        conversation_history=api_history,
                    )

                st.markdown(result["response"])

                # Show transparency expander
                with st.expander("🔍 How I answered this", expanded=False):
                    st.markdown(f"**Plan:** {result['plan']}")
                    if result["warnings"]:
                        st.markdown(f"**Medical flags detected:** {', '.join(result['warnings'])}")
                    st.markdown(f"**Verification:** {'✅ Passed' if result['verified'] else '⚠️ Issue'} — {result['verify_notes']}")
                    if result["retrieved_context"]:
                        st.text_area("Retrieved Knowledge", result["retrieved_context"], height=120)

            # Save to history
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.session_state.chat_history.append({"role": "assistant", "content": result["response"]})
            logger.info(f"[App] Chat turn completed for {pet_name}. Verified={result['verified']}")

    # Clear chat
    if st.session_state.chat_history:
        if st.button("🗑️ Clear chat history"):
            st.session_state.chat_history = []
            st.rerun()

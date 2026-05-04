"""
scheduler.py - Task scheduling, recurrence, and conflict detection for PawPal+

Manages care tasks for multiple pets, auto-expands recurring tasks,
and warns about time conflicts across pets.
"""

from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger("pawpalplus.scheduler")

RECURRENCE_OPTIONS = ["Once", "Daily", "Every 2 Days", "Weekly", "Monthly"]

RECURRENCE_DELTAS = {
    "Daily": timedelta(days=1),
    "Every 2 Days": timedelta(days=2),
    "Weekly": timedelta(weeks=1),
    "Monthly": timedelta(days=30),
}


def expand_recurring_tasks(
    tasks: list[dict],
    horizon_days: int = 7
) -> list[dict]:
    """
    Given a list of task dicts, expand recurring tasks into concrete
    instances over the next `horizon_days` days.

    Each task dict has keys:
      - pet_name (str)
      - task_name (str)
      - date (datetime.date)
      - time (str, e.g. "08:00")
      - recurrence (str, one of RECURRENCE_OPTIONS)
      - notes (str)
      - id (str, unique)

    Returns expanded list of task instances (copies with updated dates).
    """
    today = datetime.today().date()
    end_date = today + timedelta(days=horizon_days)
    expanded = []

    for task in tasks:
        recurrence = task.get("recurrence", "Once")
        if recurrence == "Once":
            if today <= task["date"] <= end_date:
                expanded.append(dict(task))
            continue

        delta = RECURRENCE_DELTAS.get(recurrence)
        if not delta:
            expanded.append(dict(task))
            continue

        current = task["date"]
        # Walk backward to find first occurrence on or after today
        while current < today:
            current += delta

        count = 0
        while current <= end_date and count < 30:
            instance = dict(task)
            instance["date"] = current
            instance["_expanded"] = True
            expanded.append(instance)
            current += delta
            count += 1

    logger.info(
        f"[Scheduler] Expanded {len(tasks)} task(s) → "
        f"{len(expanded)} instances over next {horizon_days} days."
    )
    return expanded


def detect_conflicts(tasks: list[dict], window_minutes: int = 30) -> list[dict]:
    """
    Detect scheduling conflicts: two tasks for the SAME pet within
    `window_minutes` of each other on the same day.

    Returns list of conflict dicts with keys: task_a, task_b, message.
    """
    conflicts = []

    # Group by pet_name and date
    from collections import defaultdict
    groups = defaultdict(list)
    for task in tasks:
        key = (task["pet_name"], str(task["date"]))
        groups[key].append(task)

    for (pet, date), pet_tasks in groups.items():
        # Sort by time
        def parse_time(t):
            try:
                return datetime.strptime(t["time"], "%H:%M")
            except Exception:
                return datetime.min

        sorted_tasks = sorted(pet_tasks, key=parse_time)

        for i in range(len(sorted_tasks)):
            for j in range(i + 1, len(sorted_tasks)):
                t1 = parse_time(sorted_tasks[i])
                t2 = parse_time(sorted_tasks[j])
                diff = abs((t2 - t1).total_seconds() / 60)
                if diff < window_minutes:
                    conflicts.append({
                        "task_a": sorted_tasks[i],
                        "task_b": sorted_tasks[j],
                        "message": (
                            f"⚠️ Conflict for {pet} on {date}: "
                            f"'{sorted_tasks[i]['task_name']}' at {sorted_tasks[i]['time']} "
                            f"and '{sorted_tasks[j]['task_name']}' at {sorted_tasks[j]['time']} "
                            f"are only {int(diff)} min apart."
                        )
                    })

    if conflicts:
        logger.warning(f"[Scheduler] {len(conflicts)} conflict(s) detected.")
    else:
        logger.info("[Scheduler] No scheduling conflicts detected.")

    return conflicts


def get_todays_tasks(tasks: list[dict]) -> list[dict]:
    """Return only tasks scheduled for today."""
    today = datetime.today().date()
    return [t for t in tasks if t["date"] == today]


def sort_tasks_by_datetime(tasks: list[dict]) -> list[dict]:
    """Sort tasks by date then time."""
    def sort_key(t):
        try:
            return (t["date"], datetime.strptime(t["time"], "%H:%M").time())
        except Exception:
            return (t["date"], datetime.min.time())
    return sorted(tasks, key=sort_key)

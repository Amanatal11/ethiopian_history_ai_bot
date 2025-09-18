"""
Weekly Themed History Series utilities.

Provides theme subscription management, weekly theme selection,
daily themed fact generation, and weekly summary compilation.
"""

import os
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

from langchain_groq import ChatGroq
from langchain.schema import HumanMessage

logger = logging.getLogger(__name__)


THEMES_FILE = os.path.join(os.path.dirname(__file__), "..", "themes.json")
DEFAULT_THEMES: List[str] = [
    "Ancient Kingdoms of Ethiopia",
    "Influential Leaders",
    "Historic Battles",
    "Freedom Fighters",
    "Cultural Heritage and Traditions",
    "Religious History and Landmarks",
    "Trade, Diplomacy, and Global Influence",
]


def is_themes_enabled() -> bool:
    return os.getenv("ENABLE_THEMES", "false").strip().lower() in {"1", "true", "yes", "on"}


def _week_key(d: Optional[date] = None) -> str:
    d = d or date.today()
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-{iso_week:02d}"


def _load_state() -> Dict:
    try:
        if not os.path.exists(THEMES_FILE):
            return {
                "subscribers": [],
                "current_week_key": "",
                "current_theme": "",
                "facts_log": {},  # week_key -> chat_id -> [facts]
            }
        with open(THEMES_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        logger.exception("Failed to load themes.json; using default empty state")
        return {
            "subscribers": [],
            "current_week_key": "",
            "current_theme": "",
            "facts_log": {},
        }


def _save_state(state: Dict) -> None:
    try:
        os.makedirs(os.path.dirname(THEMES_FILE), exist_ok=True)
        with open(THEMES_FILE, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
    except Exception:
        logger.exception("Failed to save themes.json")


def subscribe(chat_id: int) -> bool:
    state = _load_state()
    subs: List[int] = state.get("subscribers", [])
    if chat_id in subs:
        return False
    subs.append(chat_id)
    state["subscribers"] = subs
    _save_state(state)
    logger.info("Subscribed chat %s to weekly themes", chat_id)
    return True


def unsubscribe(chat_id: int) -> bool:
    state = _load_state()
    subs: List[int] = state.get("subscribers", [])
    if chat_id not in subs:
        return False
    subs.remove(chat_id)
    state["subscribers"] = subs
    _save_state(state)
    logger.info("Unsubscribed chat %s from weekly themes", chat_id)
    return True


def is_subscribed(chat_id: int) -> bool:
    state = _load_state()
    return chat_id in state.get("subscribers", [])


def ensure_current_week_theme(admin_override: Optional[str] = None) -> Tuple[str, str]:
    """
    Ensure the theme for the current ISO week is selected.

    Returns (week_key, theme).
    """
    state = _load_state()
    wk = _week_key()
    if state.get("current_week_key") != wk or not state.get("current_theme"):
        theme = admin_override or _pick_random_theme()
        state["current_week_key"] = wk
        state["current_theme"] = theme
        state.setdefault("facts_log", {}).setdefault(wk, {})
        _save_state(state)
        logger.info("Selected weekly theme '%s' for week %s", theme, wk)
    return state["current_week_key"], state["current_theme"]


def get_current_theme() -> Tuple[str, str]:
    state = _load_state()
    return state.get("current_week_key", ""), state.get("current_theme", "")


def _pick_random_theme() -> str:
    import random

    return random.choice(DEFAULT_THEMES)


def get_day_index_for_week(d: Optional[date] = None) -> int:
    """Return 1..7 for Mon..Sun."""
    d = d or date.today()
    return d.isoweekday()


def generate_themed_fact_sync(theme: str, day_index: int) -> str:
    """
    Generate a themed fact using Groq's LLaMA-3 via LangChain.
    """
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.6, max_tokens=180)
    prompt = (
        f"You are creating a 7-day mini-series about '{theme}'. "
        f"Today is day {day_index}. Provide a concise, engaging fact (2-3 sentences) that fits in the series. "
        f"Avoid repeating previous days and keep it historically accurate."
    )
    resp = llm.invoke([HumanMessage(content=prompt)])
    if hasattr(resp, "content"):
        return resp.content.strip()
    if isinstance(resp, list) and resp and hasattr(resp[0], "content"):
        return resp[0].content.strip()
    return str(resp).strip()


def log_fact_for_chat(chat_id: int, week_key: str, fact: str) -> None:
    state = _load_state()
    facts_log: Dict[str, Dict[str, List[str]]] = state.setdefault("facts_log", {})
    wk_log = facts_log.setdefault(week_key, {})
    chat_log = wk_log.setdefault(str(chat_id), [])
    chat_log.append(fact)
    _save_state(state)


def compile_weekly_summary_sync(theme: str, facts: List[str]) -> str:
    """
    Compile a 1-2 paragraph summary for the week's theme using prior facts.
    Uses LLM for a cohesive summary if possible; falls back to join.
    """
    try:
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.3, max_tokens=220)
        joined = "\n- ".join(facts)
        prompt = (
            f"Summarize this 7-day themed series about '{theme}' into 1-2 cohesive paragraphs. "
            f"Highlight key takeaways and weave a narrative.\n\nFacts:\n- {joined}"
        )
        resp = llm.invoke([HumanMessage(content=prompt)])
        if hasattr(resp, "content"):
            return resp.content.strip()
        if isinstance(resp, list) and resp and hasattr(resp[0], "content"):
            return resp[0].content.strip()
        return str(resp).strip()
    except Exception:
        logger.exception("Failed to compile weekly summary via LLM; falling back to simple summary")
        return (
            f"Weekly Summary for '{theme}':\n\n" + "\n".join(f"- {f}" for f in facts)
        )


async def send_weekly_summaries(app: "telegram.ext.Application") -> None:
    if not is_themes_enabled():
        return
    state = _load_state()
    wk, theme = get_current_theme()
    if not wk or not theme:
        logger.info("No current theme/week; skipping weekly summaries")
        return
    subs: List[int] = state.get("subscribers", [])
    facts_log: Dict[str, Dict[str, List[str]]] = state.get("facts_log", {})
    wk_log = facts_log.get(wk, {})

    logger.info("Sending weekly themed summaries to %d subscribers", len(subs))
    for chat_id in subs:
        facts = wk_log.get(str(chat_id), [])
        if not facts:
            continue
        summary = await _to_thread_compile(theme, facts)
        try:
            await app.bot.send_message(
                chat_id=chat_id,
                text=f"🧭 Weekly Summary: {theme}\n\n{summary}"
            )
        except Exception:
            logger.exception("Failed to send weekly summary to %s", chat_id)


async def _to_thread_compile(theme: str, facts: List[str]) -> str:
    import asyncio

    return await asyncio.to_thread(compile_weekly_summary_sync, theme, facts)



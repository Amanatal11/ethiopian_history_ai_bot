import os
import json
import asyncio
import logging
import threading
from datetime import time as dtime
from typing import Set

from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from langchain_groq import ChatGroq
from langchain.schema import HumanMessage

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ------------------------------
# Simple production-ready Telegram bot
# - Subscriptions stored in subscribers.json (chat_id set)
# - Uses Groq LLaMA-3 (via langchain_groq) for content generation
# - Sends one short Ethiopian history fact daily
#
# How to run:
# 1. Create a .env file in project root with:
#    TELEGRAM_BOT_TOKEN="your_telegram_token"
#    GROQ_API_KEY="your_groq_api_key"
#    (optional) DAILY_SEND_TIME="09:00"   # HH:MM in 24h local time, default 09:00
#
# 2. Install dependencies:
#    pip install python-telegram-bot==20.6 apscheduler langchain-groq python-dotenv
#
# 3. Run:
#    python src/bot.py
#
# Notes:
# - This file uses AsyncIOScheduler so the scheduler runs on the same asyncio loop as the bot.
# - Subscriber storage is a small JSON file. For higher scale use a real DB.
# ------------------------------

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
DAILY_SEND_TIME = os.getenv("DAILY_SEND_TIME", "09:00").strip()  # "HH:MM"

SUBSCRIBERS_FILE = os.path.join(os.path.dirname(__file__), "..", "subscribers.json")
_SUB_LOCK = threading.Lock()


def _require_env_vars() -> None:
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is missing. Set it in .env")
        raise SystemExit(1)
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY is missing. Set it in .env")
        raise SystemExit(1)


def _load_subscribers() -> Set[int]:
    with _SUB_LOCK:
        try:
            if not os.path.exists(SUBSCRIBERS_FILE):
                return set()
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return set(int(x) for x in data.get("subscribers", []))
        except Exception:
            logger.exception("Failed to load subscribers.json; starting with empty set.")
            return set()


def _save_subscribers(subs: Set[int]) -> None:
    with _SUB_LOCK:
        os.makedirs(os.path.dirname(SUBSCRIBERS_FILE), exist_ok=True)
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as fh:
            json.dump({"subscribers": list(subs)}, fh)


async def start_command(update: "telegram.Update", context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    subs = _load_subscribers()
    if chat_id in subs:
        await update.message.reply_text("You are already subscribed to daily Ethiopian history facts.")
        return
    subs.add(chat_id)
    _save_subscribers(subs)
    await update.message.reply_text("Subscribed ✅ You will receive one short Ethiopian history fact daily.")


async def stop_command(update: "telegram.Update", context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    subs = _load_subscribers()
    if chat_id not in subs:
        await update.message.reply_text("You are not subscribed.")
        return
    subs.remove(chat_id)
    _save_subscribers(subs)
    await update.message.reply_text("Unsubscribed ✅ You will no longer receive daily facts.")


async def fact_command(update: "telegram.Update", context: ContextTypes.DEFAULT_TYPE) -> None:
    # On-demand fact generation
    try:
        fact = await asyncio.to_thread(_generate_fact_sync)
        await update.message.reply_text(fact)
    except Exception as exc:
        logger.exception("Failed to generate fact on-demand")
        await update.message.reply_text("Sorry, I couldn't generate a fact right now.")


def _generate_fact_sync() -> str:
    """
    Synchronous Groq call. We run this in a thread via asyncio.to_thread so it
    doesn't block the asyncio loop.
    """
    # ChatGroq reads GROQ_API_KEY from env by default; ensure env var is set.
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.0)
    prompt = "Give a short Ethiopian history fact in 2–3 sentences."
    # Use HumanMessage wrapper to be consistent with langchain schema
    resp = llm.invoke([HumanMessage(content=prompt)])
    # langchain_groq may return an object with .content or similar; handle common shapes
    if hasattr(resp, "content"):
        return resp.content.strip()
    if isinstance(resp, list) and resp and hasattr(resp[0], "content"):
        return resp[0].content.strip()
    # Fallback to string representation
    return str(resp).strip()


async def _send_daily_facts(app: "telegram.ext.Application") -> None:
    """
    Generates one fact and sends it to every subscriber.
    Runs on the asyncio loop (AsyncIOScheduler).
    """
    subs = _load_subscribers()
    if not subs:
        logger.info("No subscribers; skipping daily send.")
        return

    logger.info("Generating daily fact via Groq...")
    try:
        fact = await asyncio.to_thread(_generate_fact_sync)
    except Exception:
        logger.exception("Failed to generate daily fact")
        return

    logger.info("Sending daily fact to %d subscribers", len(subs))
    for chat_id in subs:
        try:
            await app.bot.send_message(chat_id=chat_id, text=fact)
        except Exception:
            logger.exception("Failed to send daily fact to %s", chat_id)


def _parse_daily_time(tstr: str) -> dtime:
    try:
        parts = [int(p) for p in tstr.split(":", 1)]
        hour, minute = parts[0], parts[1] if len(parts) > 1 else 0
        return dtime(hour=hour % 24, minute=minute % 60)
    except Exception:
        logger.warning("Invalid DAILY_SEND_TIME %r, defaulting to 09:00", tstr)
        return dtime(hour=9, minute=0)


async def main() -> None:
    _require_env_vars()

    # Build the bot
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("fact", fact_command))

    # Setup the scheduler (shares the same asyncio loop as this function)
    scheduler = AsyncIOScheduler()
    send_time = _parse_daily_time(DAILY_SEND_TIME)
    scheduler.add_job(
        _send_daily_facts,
        "cron",
        hour=send_time.hour,
        minute=send_time.minute,
        args=(app,),
        id="daily_fact_job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: daily send at %02d:%02d", send_time.hour, send_time.minute)

    # Start the bot within the same asyncio loop using the explicit async lifecycle (PTB v21)
    logger.info("Starting Telegram bot...")
    await app.initialize()
    await app.start()
    try:
        await app.updater.start_polling()
        # Block forever until externally stopped (Ctrl+C)
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
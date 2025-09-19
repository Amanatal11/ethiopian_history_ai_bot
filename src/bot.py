"""
Ethiopian History AI Bot

A sophisticated Telegram bot that delivers daily Ethiopian history facts
powered by AI using Groq's LLaMA-3 model via LangChain.

Author: Ethiopian History AI Bot Team
License: MIT
"""

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
    CallbackQueryHandler,
    ContextTypes,
)
import themes
from . import quiz
from quiz import build_quiz_message, handle_quiz_selection

# ------------------------------
# Configuration and Constants
# ------------------------------

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
DAILY_SEND_TIME = os.getenv("DAILY_SEND_TIME", "09:00").strip()  # "HH:MM"

# File paths and synchronization
SUBSCRIBERS_FILE = os.path.join(os.path.dirname(__file__), "..", "subscribers.json")
_SUB_LOCK = threading.Lock()


def _require_env_vars() -> None:
    """Validate that all required environment variables are set."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is missing. Set it in .env")
        raise SystemExit(1)
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY is missing. Set it in .env")
        raise SystemExit(1)
    logger.info("Environment variables validated successfully")


def _load_subscribers() -> Set[int]:
    """Load subscriber chat IDs from JSON file."""
    with _SUB_LOCK:
        try:
            if not os.path.exists(SUBSCRIBERS_FILE):
                logger.info("No subscribers file found, starting with empty set")
                return set()
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            subscribers = set(int(x) for x in data.get("subscribers", []))
            logger.info(f"Loaded {len(subscribers)} subscribers")
            return subscribers
        except Exception as e:
            logger.exception("Failed to load subscribers.json; starting with empty set.")
            return set()


def _save_subscribers(subs: Set[int]) -> None:
    """Save subscriber chat IDs to JSON file."""
    with _SUB_LOCK:
        try:
            os.makedirs(os.path.dirname(SUBSCRIBERS_FILE), exist_ok=True)
            with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as fh:
                json.dump({"subscribers": list(subs)}, fh, indent=2)
            logger.info(f"Saved {len(subs)} subscribers to file")
        except Exception as e:
            logger.exception("Failed to save subscribers to file")


async def start_command(update: "telegram.Update", context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - subscribe user to daily facts."""
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name or "User"
    
    subs = _load_subscribers()
    if chat_id in subs:
        await update.message.reply_text(
            "You are already subscribed to daily Ethiopian history facts! 📚"
        )
        logger.info(f"User {user_name} (ID: {chat_id}) attempted to subscribe but was already subscribed")
        return
    
    subs.add(chat_id)
    _save_subscribers(subs)
    await update.message.reply_text(
        "Subscribed ✅ You will receive one short Ethiopian history fact daily at 9:00 AM! 🇪🇹"
    )
    logger.info(f"User {user_name} (ID: {chat_id}) successfully subscribed")


async def stop_command(update: "telegram.Update", context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stop command - unsubscribe user from daily facts."""
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name or "User"
    
    subs = _load_subscribers()
    if chat_id not in subs:
        await update.message.reply_text("You are not subscribed to daily facts.")
        logger.info(f"User {user_name} (ID: {chat_id}) attempted to unsubscribe but was not subscribed")
        return
    
    subs.remove(chat_id)
    _save_subscribers(subs)
    await update.message.reply_text("Unsubscribed ✅ You will no longer receive daily facts.")
    logger.info(f"User {user_name} (ID: {chat_id}) successfully unsubscribed")


async def fact_command(update: "telegram.Update", context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /fact command - generate and send an instant history fact."""
    user_name = update.effective_user.first_name or "User"
    logger.info(f"User {user_name} requested an instant fact")
    
    try:
        await update.message.reply_text("Generating a fascinating Ethiopian history fact... 🤔")
        fact = await asyncio.to_thread(_generate_fact_sync)
        await update.message.reply_text(f"📚 **Ethiopian History Fact:**\n\n{fact}")
        logger.info(f"Successfully generated fact for user {user_name}")
    except Exception as exc:
        logger.exception("Failed to generate fact on-demand")
        await update.message.reply_text(
            "Sorry, I couldn't generate a fact right now. Please try again later! 😔"
        )


async def theme_command(update: "telegram.Update", context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manage Weekly Themed History Series subscriptions and admin actions.

    Usage:
      /theme on | subscribe
      /theme off | unsubscribe
      /theme status
      /theme set <theme name>   (admin only)
    """
    if not themes.is_themes_enabled():
        await update.message.reply_text("Themed series is currently disabled by the admin.")
        return

    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name or "User"
    args = context.args or []

    if not args:
        status = "subscribed" if themes.is_subscribed(chat_id) else "not subscribed"
        _, current_theme = themes.get_current_theme()
        await update.message.reply_text(
            "Weekly Themed Series: "
            f"You are currently {status}.\n"
            "Use /theme on to subscribe or /theme off to unsubscribe.\n"
            f"Current theme: {current_theme or 'TBD'}"
        )
        return

    action = args[0].lower()
    if action in {"on", "subscribe"}:
        if themes.subscribe(chat_id):
            await update.message.reply_text("Subscribed to Weekly Themed Series ✅")
            logger.info(f"User {user_name} (ID: {chat_id}) subscribed to themes")
        else:
            await update.message.reply_text("You are already subscribed to themes.")
        return

    if action in {"off", "unsubscribe"}:
        if themes.unsubscribe(chat_id):
            await update.message.reply_text("Unsubscribed from Weekly Themed Series ✅")
            logger.info(f"User {user_name} (ID: {chat_id}) unsubscribed from themes")
        else:
            await update.message.reply_text("You were not subscribed to themes.")
        return

    if action == "status":
        status = "subscribed" if themes.is_subscribed(chat_id) else "not subscribed"
        wk, current_theme = themes.get_current_theme()
        await update.message.reply_text(
            f"You are {status}. Current week: {wk or 'TBD'}, Theme: {current_theme or 'TBD'}."
        )
        return

    if action == "set":
        # Optional admin override using comma-separated IDs in THEME_ADMIN_IDS
        admin_ids_str = os.getenv("THEME_ADMIN_IDS", "").strip()
        admin_ids = {int(x) for x in admin_ids_str.split(",") if x.strip().isdigit()} if admin_ids_str else set()
        if chat_id not in admin_ids:
            await update.message.reply_text("You are not authorized to set the theme.")
            return
        if len(args) < 2:
            await update.message.reply_text("Usage: /theme set <theme name>")
            return
        manual_theme = " ".join(args[1:]).strip()
        wk, th = themes.ensure_current_week_theme(admin_override=manual_theme)
        await update.message.reply_text(f"Set weekly theme to '{th}' for week {wk} ✅")
        logger.info(f"Admin {chat_id} set weekly theme to '{th}' for {wk}")
        return
    
    await update.message.reply_text("Unknown action. Use /theme on|off|status or /theme set <name>.")


def _generate_fact_sync() -> str:
    """
    Generate an Ethiopian history fact using Groq's LLaMA-3 model.
    
    This function runs synchronously in a thread to avoid blocking the asyncio loop.
    Returns a formatted history fact string.
    """
    try:
        # Initialize Groq LLM with LLaMA-3 model
        llm = ChatGroq(
            model="llama-3.1-8b-instant", 
            temperature=0.7,  # Slightly higher for more creative facts
            max_tokens=150    # Limit response length
        )
        
        prompt = (
            "Provide a fascinating and accurate Ethiopian history fact in 2-3 sentences. "
            "Focus on interesting events, cultural aspects, or historical figures. "
            "Make it engaging and educational."
        )
        
        # Generate response using LangChain schema
        response = llm.invoke([HumanMessage(content=prompt)])
        
        # Extract content from response
        if hasattr(response, "content"):
            return response.content.strip()
        if isinstance(response, list) and response and hasattr(response[0], "content"):
            return response[0].content.strip()
        
        # Fallback to string representation
        return str(response).strip()
        
    except Exception as e:
        logger.error(f"Error generating fact: {e}")
        return "I apologize, but I'm having trouble generating a history fact right now. Please try again later."


async def _send_daily_facts(app: "telegram.ext.Application") -> None:
    """
    Generate and send daily Ethiopian history facts to all subscribers.
    
    This function is called by the scheduler and runs on the asyncio loop.
    """
    subs = _load_subscribers()
    if not subs:
        logger.info("No subscribers; skipping daily fact delivery")
        return

    logger.info(f"Starting daily fact generation for {len(subs)} subscribers")
    
    try:
        # For non-themed users, prepare a generic fact once
        generic_fact: Optional[str] = None
        
        # Prepare theme/day context if enabled
        wk = theme_name = None
        day_index = None
        if themes.is_themes_enabled():
            wk, theme_name = themes.ensure_current_week_theme()
            day_index = themes.get_day_index_for_week()

        successful_sends = 0
        failed_sends = 0

        for chat_id in subs:
            try:
                if themes.is_themes_enabled() and themes.is_subscribed(chat_id) and theme_name and day_index:
                    # Themed fact
                    themed_fact = await asyncio.to_thread(themes.generate_themed_fact_sync, theme_name, day_index)
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"🌅 Weekly Theme: {theme_name}\n"
                            f"Day {day_index}/7\n\n{themed_fact}"
                        ),
                    )
                    themes.log_fact_for_chat(chat_id, wk, themed_fact)
                else:
                    # Generic fact
                    if generic_fact is None:
                        generic_fact = await asyncio.to_thread(_generate_fact_sync)
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=f"🌅 **Daily Ethiopian History Fact**\n\n{generic_fact}\n\n🇪🇹 Have a great day!",
                    )
                successful_sends += 1
            except Exception as e:
                logger.warning(f"Failed to send daily fact to {chat_id}: {e}")
                failed_sends += 1

        logger.info(f"Daily fact delivery completed: {successful_sends} successful, {failed_sends} failed")

    except Exception as e:
        logger.exception("Failed during daily fact processing")
        # Optionally send error notification to admin or log to monitoring system


def _parse_daily_time(time_str: str) -> dtime:
    """
    Parse daily send time from string format (HH:MM) to datetime.time object.
    
    Args:
        time_str: Time string in HH:MM format
        
    Returns:
        datetime.time object with parsed time, defaults to 09:00 if invalid
    """
    try:
        parts = [int(p) for p in time_str.split(":", 1)]
        hour, minute = parts[0], parts[1] if len(parts) > 1 else 0
        parsed_time = dtime(hour=hour % 24, minute=minute % 60)
        logger.info(f"Parsed daily send time: {parsed_time}")
        return parsed_time
    except Exception as e:
        logger.warning(f"Invalid DAILY_SEND_TIME '{time_str}', defaulting to 09:00. Error: {e}")
        return dtime(hour=9, minute=0)


async def main() -> None:
    """
    Main application entry point.
    
    Initializes the Telegram bot, sets up the scheduler, and starts both services
    running on the same asyncio event loop.
    """
    logger.info("Starting Ethiopian History AI Bot...")
    
    # Validate environment variables
    _require_env_vars()

    # Build the Telegram bot application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    logger.info("Telegram bot application created")

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("fact", fact_command))
    app.add_handler(CommandHandler("theme", theme_command))
    app.add_handler(CommandHandler("quiz", quiz.quiz_command))
    app.add_handler(CallbackQueryHandler(quiz.quiz_callback))
    app.add_handler(CommandHandler("quiz", quiz_command))
    logger.info("Command handlers registered")

    # Setup the scheduler (shares the same asyncio loop as the bot)
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
    # Weekly themed summaries on Sunday 20:00 if enabled
    if themes.is_themes_enabled():
        scheduler.add_job(
            themes.send_weekly_summaries,
            "cron",
            day_of_week="sun",
            hour=20,
            minute=0,
            args=(app,),
            id="weekly_summary_job",
            replace_existing=True,
        )

    scheduler.start()
    logger.info(f"Scheduler started: daily facts will be sent at {send_time.strftime('%H:%M')}")

    # Start the bot using explicit async lifecycle (PTB v21+)
    logger.info("Initializing Telegram bot...")
    await app.initialize()
    await app.start()
    
    try:
        logger.info("Starting bot polling...")
        await app.updater.start_polling()
        
        # Keep the bot running until interrupted
        logger.info("Bot is now running! Press Ctrl+C to stop.")
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
    except Exception as e:
        logger.exception("Unexpected error in main loop")
    finally:
        # Graceful shutdown
        logger.info("Shutting down bot...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        scheduler.shutdown()
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
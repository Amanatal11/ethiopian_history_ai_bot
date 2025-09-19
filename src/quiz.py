"""
Random History Quiz utilities for the Ethiopian History AI Bot.

Provides a /quiz command that sends one multiple-choice question using
InlineKeyboardMarkup and handles user responses via callback queries.
"""

import json
import logging
import random
from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from .quiz_data import QUIZ_QUESTIONS


logger = logging.getLogger(__name__)


def _build_question_payload(q: Dict) -> str:
    payload = {
        "q": q["question"],
        "a": q["answer"],
    }
    return json.dumps(payload, ensure_ascii=False)


def build_quiz_message() -> Dict:
    """Pick a random question and return dict with text and keyboard."""
    q = random.choice(QUIZ_QUESTIONS)
    options = q["options"][:]
    random.shuffle(options)

    # Use callback_data as JSON with the correct answer and question text
    # For each option, embed the user's chosen text to compare server-side
    keyboard = [
        [InlineKeyboardButton(text=opt, callback_data=_build_option_data(q, opt))]
        for opt in options
    ]
    markup = InlineKeyboardMarkup(keyboard)
    return {"text": q["question"], "reply_markup": markup}


def _build_option_data(q: Dict, chosen: str) -> str:
    payload = {
        "answer": q["answer"],
        "chosen": chosen,
    }
    return json.dumps(payload, ensure_ascii=False)


async def handle_quiz_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback query for a quiz answer selection."""
    if not update.callback_query:
        return
    query = update.callback_query
    try:
        data = json.loads(query.data)
        answer = data.get("answer")
        chosen = data.get("chosen")
        if chosen == answer:
            text = "✅ Correct!"
        else:
            text = f"❌ Incorrect. The correct answer is {answer}."
        await query.answer()
        await query.edit_message_text(text)
    except Exception:
        logger.exception("Failed to process quiz selection")
        await query.answer(text="Error processing your selection.")



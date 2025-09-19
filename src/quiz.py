"""
Quiz feature: /quiz command and answer handling.

Presents a random multiple-choice question using InlineKeyboard buttons
and responds with correctness feedback.
"""

import logging
import random
from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from .quiz_data import QUIZ_QUESTIONS

logger = logging.getLogger(__name__)


def _build_keyboard(options):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text=opt, callback_data=f"quiz|{opt}")]
        for opt in options
    ])


async def quiz_command(update: "Update", context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a random quiz question with multiple-choice buttons."""
    if not QUIZ_QUESTIONS:
        await update.message.reply_text("No quiz questions available right now.")
        return

    q = random.choice(QUIZ_QUESTIONS)

    # Store the correct answer in user_data keyed by chat id for this interaction
    context.user_data["quiz_correct_answer"] = q["answer"]

    await update.message.reply_text(
        text=q["question"],
        reply_markup=_build_keyboard(q["options"]),
    )


async def quiz_callback(update: "Update", context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle quiz answer button presses."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    prefix, _, chosen = data.partition("|")
    if prefix != "quiz":
        return

    correct = context.user_data.get("quiz_correct_answer")
    if not correct:
        await query.edit_message_text("Quiz session expired. Use /quiz to try again.")
        return

    if chosen == correct:
        await query.edit_message_text("✅ Correct!")
    else:
        await query.edit_message_text(f"❌ Incorrect. The correct answer is {correct}.")

    # Clear stored answer
    context.user_data.pop("quiz_correct_answer", None)

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



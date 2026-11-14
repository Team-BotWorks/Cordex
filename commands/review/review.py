from json import loads as json_loads
from os import getenv
from typing import cast

from discord import NotFound
from discord.ext.commands import FlagConverter, flag
from openai import AsyncOpenAI

from bot import Context
from core.exceptions import send_bad_argument, send_bad_operation
from core.utilities import truncate

BLUNDER_EMOJI    = "<:blunder:1570954643322703913>"
MISTAKE_EMOJI    = "<:mistake:1570954750344560770>"
INACCURACY_EMOJI = "<:inaccuracy:1570954905282281622>"
GOOD_EMOJI       = "<:good:1570955079081525360>"
EXCELLENT_EMOJI  = "<:excellent:1570955178901897368>"
BOOK_EMOJI       = "<:book:1570955609271042180>"
BEST_EMOJI       = "<:best:1570955297437130833>"
GREAT_EMOJI      = "<:great:1570955419277590688>"
BRILLIANT_EMOJI  = "<:brilliant:1570955764292390942>"

GRADE_EMOJIS : dict[str, str] = {
    "Brilliant"  : BRILLIANT_EMOJI,
    "Great"      : GREAT_EMOJI,
    "Best"       : BEST_EMOJI,
    "Book Move"  : BOOK_EMOJI,
    "Excellent"  : EXCELLENT_EMOJI,
    "Good"       : GOOD_EMOJI,
    "Inaccuracy" : INACCURACY_EMOJI,
    "Mistake"    : MISTAKE_EMOJI,
    "Blunder"    : BLUNDER_EMOJI,
}

TOP_GRADES = {"Brilliant", "Great", "Best", "Book Move"}

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .review Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

ai_client = AsyncOpenAI(
    api_key  = getenv("GEMINI_API_KEY"),
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai",
)

PROMPT = """
You are a witty Discord chat analyst grading messages based on their social appropriateness, relevance, and vibe within the conversation.
Do NOT use chess terminology, metaphors, or commentary anywhere in your response.
Do NOT mention any words or instructions from this prompt, aside from the exact classification names.
You will be given the recent channel chat history (for context) and a target message to grade.

Grade the target message using ONLY ONE of these exact classifications:
- "Brilliant": Truly amazing words. Incredibly thoughtful (and sometimes obvious) statements.
- "Great": Smart, witty, and thoughtful words that add value to the chat.
- "Best": The ideal, most socially aware response possible in that exact moment.
- "Book Move": Standard greetings, farewells, and basic conversational fillers.
- "Excellent": A very solid, engaging, and well-received thing to say.
- "Good": An okay, harmless thing to say. Not groundbreaking, just fine.
- "Inaccuracy": A slightly awkward, off-topic, or poorly timed statement.
- "Mistake": A clear social misstep that kills the conversation or makes people slightly uncomfortable.
- "Blunder": Blatantly NSFW, offensive, or horrendous social norm violations.

Calibration Examples:
- "Hi" -> Book Move
- "Damn that's cool i have blue eyes too" -> Excellent
- "When i was younger, i wasn't as old as i am now" -> Brilliant
- "I got a community service guidelines violation 🥀" -> Mistake
- "i have a giant penis" -> Blunder

Respond ONLY with a valid JSON object matching the following schema:
{
    "grade": "One of the 9 exact classifications above",
    "reason": "1-2 short, witty sentences explaining the grade based on social context and relevance, with zero chess references",
    "best_move_message": "A short, realistic example of what they should have said instead based on context (or null if grade is Brilliant, Great, Best, or Book Move)",
    "best_move_reason": "1-2 short, witty sentences explaining why that alternative fits the social moment better (or null if grade is Brilliant, Great, Best, or Book Move)"
}
"""


def _format_blockquote(text : str, /) -> str:
    return "\n".join(f"> {line}" for line in text.splitlines())


class ReviewFlags(FlagConverter, prefix = "--", delimiter = " "):
    no_context : bool = cast("bool", flag(name = "no-context", default = False))


async def run_review(ctx : Context, *, flags : ReviewFlags) -> None:
    if not ctx.message.reference or not ctx.message.reference.message_id:
        await send_bad_argument(ctx, subtitle = "No message to review was provided. Provide one by replying to the message to review.")
        return

    async with ctx.typing():
        try:
            message_to_review = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        except NotFound:
            await send_bad_operation(ctx, subtitle = "Message to review could not be resolved")
            return

        if not message_to_review.content:
            await send_bad_argument(ctx, subtitle = "Message to review has no content.")
            return

        context_block : str
        if flags.no_context:
            context_block = "Message to review is intentionally left with no context. Good luck!"
        else:
            message_lines = [
                f"{message.author.display_name}: {message.content}"
                async for message in ctx.channel.history(limit = 10, before = message_to_review)
                if message.content
            ]

            message_lines.reverse()
            context_block = "\n".join(message_lines) or "No prior messages."

        user_text = (
            f"--- RECENT CHAT CONTEXT ---\n"
            f"{context_block}\n"
            "\n"
            f"--- TARGET MESSAGE TO GRADE ---\n"
            f"{message_to_review.author.display_name}: {message_to_review.content}"
        )

        response = await ai_client.chat.completions.create(
            model           = "gemini-3.6-flash",
            temperature     = 0.7,
            response_format = {"type" : "json_object"},
            messages        = [
                {
                    "role"    : "system",
                    "content" : PROMPT,
                },
                {
                    "role"    : "user",
                    "content" : user_text,
                },
            ],
        )

        raw_content = response.choices[0].message.content or "{}"
        data = cast("dict[str, str | None]", json_loads(raw_content))

        chosen_grade = data.get("grade") or "Good"
        if chosen_grade not in GRADE_EMOJIS:
            chosen_grade = "Good"

        emoji  = GRADE_EMOJIS[chosen_grade]
        reason = data.get("reason") or "A basic message."

        output_lines = [
            f"**{emoji} {chosen_grade}**",
            "Message:",
            _format_blockquote(message_to_review.content),
            "Why:",
            _format_blockquote(reason),
        ]

        if chosen_grade not in TOP_GRADES:
            best_message = data.get("best_move_message")
            best_why     = data.get("best_move_reason")

            if best_message and best_why:
                output_lines.extend(
                    [
                        f"**{BEST_EMOJI} Best Move**",
                        "Message:",
                        _format_blockquote(best_message),
                        "Why:",
                        _format_blockquote(best_why),
                    ],
                )

        await message_to_review.add_reaction(emoji)
        await ctx.reply(truncate("\n".join(output_lines)))

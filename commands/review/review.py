from json import loads as json_loads
from os import getenv
from typing import cast

from discord import NotFound
from openai import AsyncOpenAI

from bot import Context
from core.exceptions import send_bad_argument, send_bad_operation

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
    api_key  = getenv("GROQ_API_KEY"),
    base_url = "https://api.groq.com/openai/v1",
)

PROMPT = """
You are a Chess.com Game Review coach analyzing Discord messages as if they were chess moves.
You will be given the recent channel chat history (for context) and a target message to grade.

Grade the target using ONLY ONE of these exact classifications:
- "Brilliant": Truly amazing words. Incredibly thoughtful (and sometimes incredibly obvious) statements.
- "Great": Smart and thoughtful words.
- "Best": The best possible answer or thing to say in the moment.
- "Book Move": Forms of greetings and responses to greetings; basic and common.
- "Excellent": A good thing to say.
- "Good": An okay thing to say. Not great, but just fine.
- "Inaccuracy": An awkward statement.
- "Mistake": A bad social mistake. Might make people slightly uncomfortable.
- "Blunder": Blatantly NSFW or horrendous social norm violations.

Calibration Examples:
- "Hi" -> Book Move
- "Damn that's cool i have blue eyes too" -> Excellent
- "When i was younger, i wasn't as old as i am now" -> Brilliant
- "I got a community service guidelines violation 🥀" -> Mistake
- "i have a giant penis" -> Blunder

Respond ONLY with a valid JSON object matching the following schema:
{
    "grade": "One of the 9 exact classifications above",
    "reason": "1-2 short, witty sentences explaining the grade using chess commentary",
    "best_move_message": "A short, realistic example of what they should have said instead based on context (or null if grade is Brilliant, Great, Best, or Book Move)",
    "best_move_reason": "1-2 short, witty sentences explaining why that alternative would be the best move (or null if grade is Brilliant, Great, Best, or Book Move)"
}
"""


def _format_blockquote(text : str, /) -> str:
    return "\n".join(f"> {line}" for line in text.splitlines())


async def run_review(ctx : Context) -> None:
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
            model           = "llama-3.3-70b-versatile",
            temperature     = 0.7,
            response_format = {"type": "json_object"},
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

        await ctx.reply("\n".join(output_lines))

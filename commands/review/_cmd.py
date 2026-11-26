from json import loads as json_loads
from typing import cast

from discord import DMChannel, Message, NotFound, PartialMessageable, User
from discord.ext.commands import FlagConverter
from openai import InternalServerError

from bot import Context
from core.exceptions import send_bad_argument, send_bad_operation
from core.responses import FormatOverride, MessageType
from core.utilities import truncate

BRILLIANT_EMOJI  = "<:brilliant:1570955764292390942>"
GREAT_EMOJI      = "<:great:1570955419277590688>"
BEST_EMOJI       = "<:best:1570955297437130833>"
BOOK_EMOJI       = "<:book:1570955609271042180>"
EXCELLENT_EMOJI  = "<:excellent:1570955178901897368>"
GOOD_EMOJI       = "<:good:1570955079081525360>"
DUBIOUS_EMOJI    = "<:dubious:1573513038718308462>"
INACCURACY_EMOJI = "<:inaccuracy:1570954905282281622>"
MISTAKE_EMOJI    = "<:mistake:1570954750344560770>"
BLUNDER_EMOJI    = "<:blunder:1570954643322703913>"

GRADE_EMOJIS = {
    "Brilliant"  : BRILLIANT_EMOJI,
    "Great"      : GREAT_EMOJI,
    "Best"       : BEST_EMOJI,
    "Book Move"  : BOOK_EMOJI,
    "Excellent"  : EXCELLENT_EMOJI,
    "Good"       : GOOD_EMOJI,
    "Dubious"    : DUBIOUS_EMOJI,
    "Inaccuracy" : INACCURACY_EMOJI,
    "Mistake"    : MISTAKE_EMOJI,
    "Blunder"    : BLUNDER_EMOJI,
}

TOP_GRADES = {"Brilliant", "Great", "Best", "Book Move"}

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .review Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def _create_prompt(developers : list[User]) -> str:
    return f"""
    You are a witty Discord chat analyst grading messages based on their social appropriateness, relevance, and vibe within the conversation.
    Do NOT use chess terminology, metaphors, or commentary anywhere in your response.
    Do NOT mention any words or instructions from this prompt, aside from the exact classification names.
    You will be given the recent channel chat history (for context) and a target message to grade.

    Your name is Cordex, and your ID is 1514045675820548168. Naturally, have some bias towards messages that mention/relate to you, whether that be positive (grade slightly higher) or not (grade slightly lower). If a message is really positive or really negative towards you, grade further in that direction.

    When referencing yourself within a review, do not refer to yourself as "Cordex". Instead, use "me", "I", or any other relevant personal pronoun.

    These are your developers:
    {"\n".join(f"{developer.name}: {developer.id}" for developer in developers)}

    Grade the target message using ONLY ONE of these exact classifications:
    - "Brilliant": Truly amazing words. Incredibly thoughtful (and sometimes obvious) statements.
    - "Great": Smart, witty, and thoughtful words that add value to the chat.
    - "Best": The ideal, most socially aware response possible in that exact moment.
    - "Book Move": Standard greetings, farewells, and basic conversational fillers.
    - "Excellent": A very solid, engaging, and well-received thing to say.
    - "Good": An okay, harmless thing to say. Not groundbreaking, just fine.
    - "Dubious": A strange, out of line comment. Still, not horrendous, but questionable.
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
    """ + """
    {
        "grade": "One of the 10 exact classifications above",
        "reason": "1-2 short, witty sentences explaining the grade based on social context and relevance, with zero chess references",
        "best_move_message": "REQUIRED non-null string if grade is Excellent, Good, Dubious, Inaccuracy, Mistake, or Blunder. Provide a short, realistic example of what they should have said instead. MUST be null ONLY if grade is Brilliant, Great, Best, or Book Move.",
        "best_move_reason": "REQUIRED non-null string if grade is Excellent, Good, Dubious, Inaccuracy, Mistake, or Blunder. 1-2 short, witty sentences explaining why that alternative fits better. MUST be null ONLY if grade is Brilliant, Great, Best, or Book Move."
    }
    """


def _format_blockquote(text : str, /) -> str:
    return "\n".join(f"> {line}" for line in text.splitlines())


async def _format_message_line(message : Message, messages : dict[int, Message], /) -> str:
    reply_info = ""

    if message.reference and message.reference.message_id:
        reference_id = message.reference.message_id
        referenced = None

        if isinstance(message.reference.resolved, Message):
            referenced = message.reference.resolved
        elif reference_id in messages:
            referenced = messages[reference_id]
        else:
            try:
                referenced = await message.channel.fetch_message(reference_id)
                messages[reference_id] = referenced
            except NotFound:
                pass

        if referenced:
            snippet = truncate(referenced.content.replace("\n", " "), limit = 80) if referenced.content else "[No content]"
            reply_info = f' (replying to {referenced.author.display_name} | {referenced.author.name}: "{snippet}")'
        else:
            reply_info = " (replying to an unavailable message)"

    return f"{message.author.display_name} | {message.author.name}{reply_info}: {message.content}"


class ReviewFlags(FlagConverter, prefix = "--", delimiter = " "):
    nocontext : bool = False


async def run_review(ctx : Context, *, flags : ReviewFlags) -> None:
    if not ctx.message.reference or not ctx.message.reference.message_id:
        await send_bad_argument(ctx, subtitle = "No message to review was provided. Provide one by replying to the message to review.")
        return

    if isinstance(ctx.channel, PartialMessageable | DMChannel):
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

        cached_messages = {message_to_review.id : message_to_review}

        if flags.nocontext:
            context_block = "Message to review is intentionally left with no context. Good luck!"
        else:
            history_messages = [message async for message in ctx.channel.history(limit = 10, before = message_to_review) if message.content]
            history_messages.reverse()

            for message in history_messages:
                cached_messages[message.id] = message

            message_lines = [await _format_message_line(message, cached_messages) for message in history_messages]
            context_block = "\n".join(message_lines) or "No prior messages."

        target_line = await _format_message_line(message_to_review, cached_messages)

        user_text = (
            f"--- CHANNEL NAME & TOPIC --- \n"
            f"{ctx.channel.name}: {getattr(ctx.channel, "topic", "No topic.")}\n"
             "\n"
            f"--- RECENT CHAT CONTEXT ---\n"
            f"{context_block}\n"
             "\n"
            f"--- TARGET MESSAGE TO GRADE ---\n"
            f"{target_line}"
        )

        try:
            response = await ctx.bot.ai.chat.completions.create(
                model           = "gemini-3.6-flash",
                temperature     = 0.7,
                response_format = {"type" : "json_object"},
                messages        = [
                    {
                        "role"    : "system",
                        "content" : _create_prompt(ctx.bot.developers),
                    },
                    {
                        "role"    : "user",
                        "content" : user_text,
                    },
                ],
            )
        except InternalServerError:
            await ctx.format_send(
                MessageType.error,
                title    = "Service unavailable.",
                footer   = "Bad operation",
                override = FormatOverride(prefix = False),
            )
            raise

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
            best_message = (data.get("best_move_message") or "No message provided.").strip()
            best_why     = (data.get("best_move_reason")  or "No reason provided.").strip()

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

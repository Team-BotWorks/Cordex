from bot import Context
from constants import ACCEPTED_EMOJI, DENIED_EMOJI
from core.utilities import codeblock

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .sql Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def _to_table(
    rows   : list[list[object]],
    labels : list[object] | None = None,
    /,
) -> str:
    if not rows:
        return ""

    headers = labels or ["" for _ in rows[0]]

    header_line    = "|" + "|".join(f" {header!s} " for header in headers) + "|\n"
    separator_line = "|" + "|".join(" :---: " for _ in headers) + "|\n"

    body_lines = ""
    for row in rows:
        body_lines += "|" + "|".join(f" {cell!s} " for cell in row) + "|\n"

    return header_line + separator_line + body_lines


async def run_botowner_sql(ctx : Context, body : str) -> None:
    db = ctx.bot.db

    message = ctx.message
    channel = ctx.channel

    query = "\n".join(body.split("\n")[1 : -1]) if body.startswith("```") else body.strip("` \n")

    async with db.base_execute(query) as cursor:
        try:
            if cursor.description and len(cursor.description) > 0:
                await db.commit()
                await ctx.send_file(
                    file_content = _to_table(
                        [list(row) for row in await cursor.fetchall()],
                        [column[0] for column in cursor.description],
                    ),
                    file_name    = "query.md",
                )
            else:
                await db.commit()
        except Exception as e:
            await db.rollback()
            await message.add_reaction(DENIED_EMOJI)
            async with channel.typing():
                await ctx.send(codeblock(f"{e.__class__.__name__}: {e}"), delete_after = 15)
            return

    await message.add_reaction(ACCEPTED_EMOJI)

from discord import AllowedMentions

from bot import Interaction
from commands.moderation._base import build_case_section, send_case_view
from constants import COLOR_GREY
from core.moderation import CasesManager
from core.paginator import Footer, UnnamedPaginator
from core.responses import FormatOverride, MessageType, format_send

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation cases view Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_moderation_cases_view(interaction : Interaction, case_id : int | None = None) -> None:
    """
    View a moderation case.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    case_id : `int | None = None`
        The ID of the case to view. Defaults to all cases.
    """
    guild = interaction.guild
    if not guild:
        return

    cases_manager = CasesManager(interaction.client, guild)

    if case_id is not None:
        await send_case_view(interaction, cases_manager, case_id)
        return

    cases = await cases_manager.get_all_cases()
    if not cases:
        await format_send(
            interaction,
            MessageType.warning,
            title    = "No cases found for this guild",
            override = FormatOverride(prefix = False),
        )
        return

    class CasePaginator(UnnamedPaginator):
        def __init__(self) -> None:
            super().__init__(
                "# Server Cases",
                [build_case_section(case, cases_manager) for case in cases],
                footer    = Footer("Page {smallest_page} of {biggest_page} | {count} Case{s}"),
                per_page  = 10,
                color     = COLOR_GREY,
                container = True,
            )

    await interaction.response.send_message(
        view             = CasePaginator(),
        ephemeral        = True,
        allowed_mentions = AllowedMentions.none(),
    )

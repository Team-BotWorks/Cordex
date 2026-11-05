from typing import final, override

from discord import AllowedMentions, Member, User
from discord.utils import escape_markdown, format_dt

from bot import Cordex, Interaction
from bot.ui import (
    Button,
    ButtonSection,
    Container,
    LayoutView,
    TextDisplay,
    Thumbnail,
    ThumbnailSection,
    VisibleLargeSeparator,
)
from constants import COLOR_GREY
from core.exceptions import send_bad_argument
from core.moderation import Case, CasesManager
from core.utilities import format_table

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Moderation Cases Base
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class _OpenCaseButton[V : LayoutView](Button[V]):
    def __init__(self, manager : CasesManager, case_id : int) -> None:
        super().__init__(label = "View")
        self.manager = manager
        self.case_id = case_id

    @override
    async def callback(self, interaction : Interaction) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        await send_case_view(interaction, self.manager, self.case_id)


def _format_summary(case : Case) -> str:
    subjects : list[str] = []

    if case.target is not None:
        subjects.append(case.target.mention)
    if case.channel is not None:
        subjects.append(case.channel.mention)
    if not subjects:
        subjects.append("Unknown Target")

    subjects.append(case.moderator.mention)

    lines = [
        f"## {case.action_type.readable}",
        f"**{" | ".join(subjects)}**",
        f"*{escape_markdown(case.reason)}*",
    ]

    if case.purge_amount is not None:
        forced = ", forced" if case.purge_force else ""
        lines.append(f"-# Purged {case.purge_amount} messages{forced}.")

    lines.extend((f"-# Occurred at {format_dt(case.created_at, "F")}, {format_dt(case.created_at, "R")}.", f"-# Case ID: #{case.id}"))

    return "\n".join(lines)


def build_case_section[V : LayoutView](case : Case, manager : CasesManager) -> ButtonSection[V]:
    return ButtonSection(_format_summary(case), button = _OpenCaseButton(manager, case.id))


async def build_case_view(bot : Cordex, case : Case, manager : CasesManager) -> LayoutView:
    view      = LayoutView()
    container = Container[view](TextDisplay(f"# {case.action_type.readable} | #{case.id}"), color = COLOR_GREY)

    sections : list[tuple[str, Member | User | None]] = [
        ("Target",    case.target),
        ("Moderator", case.moderator),
    ]

    for heading, user in sections:
        if user is None:
            continue

        user_table : dict[str, object] = {
            heading           : user.mention,
            f"{heading} Name" : user.name,
            f"{heading} ID"   : user.id,
        }
        user_info = (
            f"## {heading}\n"
            f"{format_table(user_table)}"
        )

        container.add_item(VisibleLargeSeparator())

        avatar_url = None
        if isinstance(user, Member) and user.guild_avatar:
            avatar_url = user.guild_avatar.url
        else:
            fetched_user = await bot.fetch_user(user.id)
            if fetched_user.avatar:
                avatar_url = fetched_user.avatar.url

        if avatar_url:
            container.add_item(ThumbnailSection(user_info, thumbnail = Thumbnail[view](avatar_url)))
        else:
            container.add_text(user_info)

    details : dict[str, object] = {"Expired" : case.expired}

    if case.seconds_to_delete is not None:
        details["Message Delete History"] = f"{case.seconds_to_delete} seconds"
    if case.timeout_length is not None:
        details["Duration"] = f"{case.timeout_length} seconds"
    if case.channel is not None:
        details["Channel"] = case.channel.mention
    if case.purge_amount is not None:
        details["Amount"] = case.purge_amount
        details["Forced"] = case.purge_force
    if case.channel is None:
        details["DM Sent"] = case.dm_user

    container.add_items(
        VisibleLargeSeparator(),
        TextDisplay(
            "## Details\n"
           f"{format_table(details)}",
        ),
    )

    related_case_id = case.related_case_id
    if related_case_id is not None:
        container.add_items(
            VisibleLargeSeparator(),
            ButtonSection(
                f"## Related Case\n"
                f"#{related_case_id}",
                button = _OpenCaseButton(manager, related_case_id),
            ),
        )

    container.add_items(
        VisibleLargeSeparator(),
        TextDisplay(
            "## Reason\n"
           f"{case.reason}",
        ),
        VisibleLargeSeparator(),
        TextDisplay(f"-# Occurred at {format_dt(case.created_at, "F")}, {format_dt(case.created_at, "R")}"),
    )

    view.add_item(container)
    return view


async def send_case_view(interaction : Interaction, manager : CasesManager, case_id : int) -> None:
    case = await manager.get_case(case_id)
    if not case:
        await send_bad_argument(interaction, subtitle = {"case-id" : "Case not found."})
        return

    await interaction.response.send_message(
        view             = await build_case_view(interaction.client, case, manager),
        ephemeral        = True,
        allowed_mentions = AllowedMentions.none(),
    )

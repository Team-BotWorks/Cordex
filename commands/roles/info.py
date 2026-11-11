from typing import Self, final

from discord import (
    AllowedMentions,
    Asset,
    Member,
    Message,
    Role,
)
from discord.utils import format_dt

from bot import Interaction
from bot.ui import (
    ActionRow,
    Button,
    Container,
    InteractiveView,
    TextDisplay,
    Thumbnail,
    ThumbnailSection,
    button,
)
from constants import COLOR_GREY
from core.utilities import codeblock, format_table

from .members import run_role_members

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /role info Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_role_info(interaction : Interaction, role : Role) -> None:
    """
    View information for a role.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    role : `Role`
        "The role to view information for.
    """
    await interaction.response.defer()

    guild = interaction.guild
    if not guild or not isinstance(interaction.user, Member):
        return

    roles = sorted(guild.roles, key = lambda r : r.position)

    hierarchy_lines = ""

    for p in range(role.position + 3, role.position - 4, -1):
        if 0 <= p < len(roles):
            prefix = ">" if roles[p] == role else " "
            hierarchy_lines += f"{len(roles) - p:>4}.   {prefix} {roles[p].name}\n"

    top_role = interaction.user.top_role

    diff = "" if guild.default_role == top_role else (
        "This is your highest role."
        if role == top_role else
        f"This role is {"above" if role > top_role else "below"} your highest role."
    )

    # ⸻ Gradient checks.

    enhanced_role = "ENHANCED_ROLE_COLORS" in guild.features and role.secondary_color

    color = (
        f"{role.color}-{role.secondary_color}-{role.tertiary_color} | Holographic"
        if role.tertiary_color else
        f"{role.color}-{role.secondary_color} | Gradient"
    ) if enhanced_role else f"{role.color} | Solid"

    # ⸻ Build the view.

    table = format_table(
        {
            "Appearance"        : color,
            "Hoisted"           :  "Yes" if role.hoist else "No",
            "Mentionable"       :  "Yes" if role.mentionable else "No",
            "Number of Members" : f"{len(role.members)}",
            "Created at"        : f"{format_dt(role.created_at, style = "F")} | {format_dt(role.created_at, style = "R")}",
        },
    )

    hierarchy = (
        "**Relative Hierarchy**\n"
       f"{codeblock(hierarchy_lines, language = None)}"
    )

    icon_url = role.display_icon.url if isinstance(role.display_icon, Asset) else None

    mention = role.mention if not role.is_default() else "@everyone"

    class MemberRow(ActionRow["InfoView"]):
        @button(label = "View Members")
        async def btn_viewmembers(self, interaction : Interaction, _button : Button[InfoView]) -> None:
            await run_role_members(interaction, role, ephemeral = True)

    @final
    class InfoView(InteractiveView):
        def __init__(self) -> None:
            super().__init__()
            self.message : Message | None = None

            container = Container[Self](
                TextDisplay(f"### {mention} | {role.id}"),
                color = role.color if role.color.value else COLOR_GREY,
            )

            if icon_url:
                container.add_item(ThumbnailSection(table, thumbnail = Thumbnail(icon_url)))
            else:
                container.add_text(table)

            if diff:
                container.add_text(diff)

            container.add_text(hierarchy)
            container.add_item(MemberRow())

            self.add_item(container)

    view = InfoView()
    view.user = interaction.user
    view.message = await interaction.followup.send(
        view             = view,
        allowed_mentions = AllowedMentions.none(),
    )

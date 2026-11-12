from typing import Literal

from discord import AllowedMentions, Role

from bot import Interaction
from constants import COLOR_GREY
from core.paginator import Footer, UnnamedPaginator

type PersonFilter = Literal["Both", "Humans", "Bots"]
type RoleFilter   = Literal["In", "Not In"]

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /role members Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def run_role_members(
    interaction   : Interaction,
    role          : Role,
    role_filter   : RoleFilter   = "In",
    person_filter : PersonFilter = "Both",
    *,
    ephemeral     : bool         = False,
) -> None:
    """
    List members based on role possession and human/bot filtering.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    role : `Role`
        The role to view members or the lack thereof for.
    role_filter : `Literal["In", "Not In"]` = "In"
        Whether to check who has or who doesn't have the role selected. Defaults to "In".
    person_filter : `Literal["Both", "Humans", "Bots"]` = "Both"
        Whether to show humans or bots. Defaults to both.
    *
    ephemeral : `bool` = False
        Whether the response should be ephemeral or not. This argument is used specifically for the `/role info` command and it should not be used elsewhere.
    """
    await interaction.response.defer(ephemeral = ephemeral)

    if not interaction.guild:
        return

    # ⸻ Resolve the list.

    not_members = set(interaction.guild.members) - set(role.members)
    members     = role.members

    source = members if role_filter == "In" else not_members

    match person_filter:
        case "Both":
            filtered = list(source)
        case "Humans":
            filtered = [member for member in source if not member.bot]
        case "Bots":
            filtered = [member for member in source if member.bot]

    # ⸻ Labels.

    if person_filter == "Bots":
        person_label = "Bot"
    elif person_filter == "Humans":
        person_label = "Human"
    else:
        person_label = "Member"

    role_label = "not in" if role_filter == "Not In" else "in"

    mention = role.mention if not role.is_default() else "@everyone"

    # ⸻ Build the paginator.

    view = UnnamedPaginator(
        [f"- {member.mention} | {member.id}" for member in filtered] if filtered else ["No members found."],
        title     = f"### {person_label}s {role_label} {mention}",
        footer    = Footer("Page {smallest_page} of {biggest_page} | {count} " + person_label + "{s}"),
        per_page  = 15,
        color     = role.color if role.color.value else COLOR_GREY,
        container = True,
    )
    view.user    = interaction.user
    view.message = await interaction.followup.send(
        view             = view,
        ephemeral        = ephemeral,
        allowed_mentions = AllowedMentions.none(),
    )

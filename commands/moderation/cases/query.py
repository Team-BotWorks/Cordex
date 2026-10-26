from datetime import UTC, datetime

from discord import AllowedMentions, Member, User

from bot import Interaction
from bot.types import GuildMessagable
from commands.moderation._base import build_case_section
from constants import COLOR_GREY
from core.exceptions import send_bad_argument
from core.moderation import ActionType, CasesManager
from core.paginator import Footer, UnnamedPaginator
from core.responses import FormatOverride, MessageType, format_send

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /moderation cases query Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class DateReversalError(ValueError):
    """The exception raised when a date is parsed in DD/MM format instead of MM/DD."""


def _parse_date(date : str) -> datetime | None:
    for date_format in ("%m/%d/%Y", "%m/%d/%y", "%m/%d"):
        try:
            parsed_dt = datetime.strptime(date, date_format).replace(tzinfo = UTC)
            if date_format == "%m/%d":
                parsed_dt = parsed_dt.replace(year = datetime.now(UTC).year)
        except ValueError:
            continue
        else:
            return parsed_dt

    for date_format in ("%d/%m/%Y", "%d/%m/%y", "%d/%m"):
        try:
            datetime.strptime(date, date_format).replace(tzinfo = UTC)
        except ValueError:
            continue
        else:
            raise DateReversalError

    return None


async def run_moderation_cases_query(
    interaction : Interaction,
    *,
    action_type : str             | None = None,
    moderator   : Member          | None = None,
    target      : User            | None = None,
    channel     : GuildMessagable | None = None,
    expired     : bool            | None = None,
    before      : str             | None = None,
    after       : str             | None = None,
) -> None:
    """
    Query moderation cases with various filters.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    action_type : `str | None = None`
        Filter by action type.
    moderator : `Member | None = None`
        Filter by moderator.
    target : `User | None = None`
        Filter by user.
    channel : `GuildMessagable | None = None`
        Filter by channel.
    expired : `bool | None = None`
        Filter by expiration.
    before : `str | None = None`
        Filter cases that occurred before this date. Must be of the form "MM/DD/YYYY", "MM/DD/YY", or "MM/DD".
    after : `str | None = None`
        Filter cases that occurred after this date. Must be of the form "MM/DD/YYYY", "MM/DD/YY", or "MM/DD".
    """
    guild = interaction.guild
    if not guild:
        return

    if all(
        case_filter is None for case_filter in
        (action_type, moderator, target, channel, expired, before, after)
    ):
        await send_bad_argument(
            interaction,
            subtitle = {None : "At least one filter must be chosen."},
        )
        return

    if before:
        try:
            before_datetime = _parse_date(before)
        except DateReversalError:
            await send_bad_argument(
                interaction,
                subtitle = {"before" : "Invalid date passed. A date must be of the form `MM/DD`, not `DD/MM`."},
            )
            return

        if not before_datetime:
            await send_bad_argument(
                interaction,
                subtitle = {"before" : "Invalid date passed. A date must be of the form `MM/DD/YYYY`, `MM/DD/YY`, or `MM/DD`."},
            )
            return
    else:
        before_datetime = None

    if after:
        try:
            after_datetime = _parse_date(after)
        except DateReversalError:
            await send_bad_argument(
                interaction,
                subtitle = {"after" : "Invalid date passed. A date must be of the form `MM/DD`, not `DD/MM`."},
            )
            return

        if not after_datetime:
            await send_bad_argument(
                interaction,
                subtitle = {"after" : "Invalid date passed. A date must be of the form `MM/DD/YYYY`, `MM/DD/YY`, or `MM/DD`."},
            )
            return
    else:
        after_datetime = None

    parsed_action = ActionType(action_type) if action_type is not None else None
    if channel is not None and parsed_action not in {ActionType.lockdown_add, ActionType.lockdown_remove, ActionType.purge}:
        await send_bad_argument(
            interaction,
            subtitle = {("action-type", "channel") : "`channel` cannot be passed if `action-type` is not 'Lockdown Add', 'Lockdown Remove', or 'Purge'."},
        )
        return

    cases_manager = CasesManager(interaction.client, guild)
    try:
        cases = await cases_manager.filter_by(
            action_type  = parsed_action,
            moderator_id = moderator.id if moderator else None,
            target_id    = target.id    if target    else None,
            channel_id   = channel.id   if channel   else None,
            expired      = expired,
            before       = before_datetime,
            after        = after_datetime,
        )
    except ValueError:
        await send_bad_argument(
            interaction,
            subtitle = {("before", "after") : "The `after` filter date must occur strictly before the `before` filter date."},
        )
        return

    if expired is False:
        cases = [
            case for case in cases if
            case.action_type not in {
                ActionType.ban_remove,
                ActionType.quarantine_remove,
                ActionType.timeout_remove,
            }
        ]

    if not cases:
        if not await cases_manager.get_all_cases():
            await format_send(
                interaction,
                MessageType.warning,
                title    = "No cases found for this guild",
                override = FormatOverride(prefix = False),
            )
            return

        await format_send(
            interaction,
            MessageType.warning,
            title    = "No cases found matching this filter",
            override = FormatOverride(prefix = False),
        )
        return

    class CasePaginator(UnnamedPaginator):
        def __init__(self) -> None:
            super().__init__(
                "# Cases Found",
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

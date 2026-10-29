# ruff: file-ignore[private-member-access]

from contextlib import suppress
from typing import Self, final, override

from discord import ButtonStyle, Member, User

from bot import Interaction
from bot.types import GuildMessageable, GuildMessageableChannel
from bot.ui import (
    ActionRow,
    Button,
    Checkbox,
    Item,
    Label,
    LayoutView,
    Modal,
    TextDisplay,
    TextInput,
    VisibleLargeSeparator,
    button,
)
from constants import ACCEPTED_EMOJI, DENIED_EMOJI, WARNING_EMOJI
from core.exceptions import send_bad_argument
from core.moderation import (
    Actions,
    ActionType,
    BanAddPayload,
    BanRemovePayload,
    KickPayload,
    LockdownAddPayload,
    LockdownManager,
    LockdownRemovePayload,
    PurgePayload,
    QuarantineAddPayload,
    QuarantineManager,
    QuarantineRemovePayload,
    TimeoutAddPayload,
    TimeoutRemovePayload,
)
from core.responses import (
    FormatOverride,
    MessageType,
    PunctuationOverride,
    format_message,
)
from core.utilities import format_table

from .utilities import hierarchy

type Targetable = User | Member | GuildMessageable

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Moderation Select Base
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# State
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class _ModerationModal(Modal):
    def __init__(
        self,
        action_type  : ActionType,
        target       : Targetable,
        *,
        purge_target : Member           | None = None,
        edit_view    : LayoutView       | None = None,
        state        : _ModerationModal | None = None,
    ) -> None:
        self.edit_view    : LayoutView | None = edit_view
        self.purge_target : Member     | None = purge_target

        target_name = target.name

        channel_types = {
            ActionType.lockdown_add,
            ActionType.lockdown_remove,
            ActionType.purge,
        }

        person_types  = {
            ActionType.ban_add,
            ActionType.ban_remove,
            ActionType.kick,
            ActionType.quarantine_add,
            ActionType.quarantine_remove,
            ActionType.timeout_add,
            ActionType.timeout_remove,
        }

        # ⸻ Validate that target is the correct type.

        if isinstance(target, GuildMessageable) and action_type not in channel_types:
            error = "target cannot be GuildMessageable if action_type is not a channel type"
            raise ValueError(error)

        if isinstance(target, Member) and action_type not in person_types:
            error = "target cannot be Member if action_type is not a user type"
            raise ValueError(error)

        if isinstance(target, User) and action_type not in person_types:
            error = "target cannot be User if action_type is not a user type"
            raise ValueError(error)

        title : dict[ActionType, str] = {
            ActionType.lockdown_add      : f"Placing {target_name} in Lockdown",
            ActionType.lockdown_remove   : f"Removing {target_name} from Lockdown",
            ActionType.ban_add           : f"Banning {target_name}",
            ActionType.ban_remove        : f"Unbanning {target_name}",
            ActionType.kick              : f"Kicking {target_name}",
            ActionType.quarantine_add    : f"Placing {target_name} in Quarantine",
            ActionType.quarantine_remove : f"Removing {target_name} from Quarantine",
            ActionType.timeout_add       : f"Placing {target_name} in Timeout",
            ActionType.timeout_remove    : f"Removing {target_name} from Timeout",
            ActionType.purge             : f"Purging {target_name}",
        }
        name : dict[ActionType, str] = {
            ActionType.lockdown_add      : "lockdown",
            ActionType.lockdown_remove   : "lockdown removal",
            ActionType.ban_add           : "ban",
            ActionType.ban_remove        : "ban removal",
            ActionType.kick              : "kick",
            ActionType.quarantine_add    : "quarantine",
            ActionType.quarantine_remove : "quarantine removal",
            ActionType.timeout_add       : "timeout",
            ActionType.timeout_remove    : "timeout removal",
            ActionType.purge             : "purge",
        }

        self.action_type : ActionType = action_type
        self.target                   = target
        self.name                     = name[action_type]
        self.has_dm      : bool       = action_type not in channel_types

        super().__init__(title = title[action_type])

        items : list[Item[Self]] = []

        if action_type == ActionType.purge:
            self.text = TextDisplay[Self](
               f"{WARNING_EMOJI} **Use `Amount` alone, `Amount` + `Target`, or `Amount` + `Target` + `Force`.**\n"
                "## Cases\n"
                "### `Force = False (Default)`\n"
                "Finds `n` messages from the channel and purges any from the target.\n"
                "### `Force = True`\n"
                "Finds `n` messages from the target and purges them from the channel.",
            )

            items.append(self.text)

        self._reason = TextInput[Self](
            placeholder = "Enter reason here...",
            default     = state._reason.value if state else None,
        )
        self.reason  = Label[Self](
            text        =  "Reason",
            description = f"Reason for the {self.name}.",
            component   = self._reason,
        )

        items.append(self.reason)

        if action_type == ActionType.timeout_add:
            self._length = TextInput[Self](
                placeholder = "Enter length here...",
                default     = state._length.value if state else None,
            )
            self.length  = Label[Self](
                text        = "Length",
                description = "Length of the timeout.",
                component   = self._length,
            )

            items.append(self.length)

        match action_type:
            case ActionType.ban_add:
                self._dtd = TextInput[Self](
                    placeholder = "Enter number here...",
                    required    = False,
                    min_length  = 1,
                    max_length  = 1,
                    default     = state._dtd.value if state else None,
                )
                self.dtd  = Label[Self](
                    text        = "Days to Delete",
                    description = "Days to delete messages of the user upon ban. Defaults to 7.",
                    component   = self._dtd,
                )

                items.append(self.dtd)
            case ActionType.purge:
                self._amount = TextInput[Self](
                    placeholder = 'ex: "10"',
                    min_length  = 1,
                    max_length  = 3,
                    default     = state._amount.value if state else None,
                )
                self.amount  = Label[Self](
                    text        = "Amount",
                    description = "The amount of messages to purge.",
                    component   = self._amount,
                )

                self._force = Checkbox[Self](default = state._force.value if state else False)
                self.force  = Label[Self](
                    text        = "Force",
                    description = "Whether to force purge messages.",
                    component   = self._force,
                )

                items.extend((self.amount, self.force))
            case _:
                pass

        if self.has_dm:
            self._dm = Checkbox[Self](default = state._dm.value if state else False)
            self.dm  = Label[Self](
                text        =  "DM",
                description = f"Whether to DM the user upon {self.name}. This can fail!",
                component   = self._dm,
            )

            items.append(self.dm)

        self.append_items(items)

    @override
    async def on_submit(self, interaction : Interaction) -> None:
        modal = self

        # ⸻ Update the defaults.

        self._reason.default = self._reason.value

        if self.action_type == ActionType.timeout_add:
            self._length.default = self._length.value

        match self.action_type:
            case ActionType.ban_add:
                self._dtd.default = self._dtd.value
            case ActionType.purge:
                self._amount.default = self._amount.value
                self._force.default  = self._force.value
            case _:
                pass

        if self.has_dm:
            self._dm.default = self._dm.value

        reason = self._reason.value

        length : str | None = None
        dtd    : str | None = None

        purge_member : Member | None = self.purge_target
        amount       : int    | None = None
        force        : bool          = False
        dm           : bool          = False

        if self.action_type == ActionType.timeout_add:
            length = self._length.value

        await interaction.response.defer(ephemeral = True)

        match self.action_type:
            case ActionType.ban_add:
                dtd = self._dtd.value
            case ActionType.purge:
                force = self._force.value

                if not interaction.guild or not isinstance(interaction.user, Member):
                    return

                # ⸻ We already validated that target is a GuildMessageable in __init__.

                if not isinstance(self.target, GuildMessageable):
                    return

                # ⸻ Force requires Target.

                if force and purge_member is None:
                    await send_bad_argument(
                        interaction,
                        subtitle = {"force" : "`force` is dependent on `target`."},
                    )
                    return

                # ⸻ Validate amount.

                try:
                    amount = int(self._amount.value)
                except ValueError, TypeError:
                    await send_bad_argument(
                        interaction,
                        subtitle = {"amount" : "`amount` must be a valid integer."},
                    )
                    return

                match amount:
                    case 0:
                        await send_bad_argument(
                            interaction,
                            subtitle = {"amount" : "Cannot purge zero messages."},
                        )
                        return
                    case 1:
                        await send_bad_argument(
                            interaction,
                            subtitle = {"amount" : "Please delete the message manually."},
                        )
                        return
                    case n if n < 0:
                        await send_bad_argument(
                            interaction,
                            subtitle = {"amount" : "`amount` cannot be a negative number."},
                        )
                        return
                    case _:
                        pass
            case _:
                pass

        if self.has_dm:
            dm = self._dm.value

        action_table : dict[str, object] = {"Reason" : reason}

        if length is not None:
            action_table["Length"] = length

        if dtd is not None:
            action_table["Days to Delete"] = dtd

        if self.action_type == ActionType.purge:
            action_table["Amount"] = amount or "None"
            action_table["Force"]  = force

            sections : list[str] = [
                "### Target Channel",
                format_table(
                    {
                        "Channel"    : self.target.mention,
                        "Name"       : self.target.name,
                        "Channel ID" : self.target.id,
                    },
                ),
            ]

            if purge_member is not None:
                sections.extend(
                    (
                        "### Target Member",
                        format_table(
                            {
                                "User"     : purge_member.mention,
                                "Username" : purge_member.name,
                                "User ID"  : purge_member.id,
                            },
                        ),
                    ),
                )

            sections.extend(
                (
                    "### Action Information",
                    format_table(action_table),
                ),
            )

            summary = "\n".join(sections)
        else:
            if self.has_dm:
                action_table["DM Member"] = dm

            target_table : dict[str, object] = {
                "User"     : self.target.mention,
                "Username" : self.target.name,
                "User ID"  : self.target.id,
            } if isinstance(self.target, Member | User) else {
                "Channel"    : self.target.mention,
                "Name"       : self.target.name,
                "Channel ID" : self.target.id,
            }

            summary = (
                 "### Target\n"
                f"{format_table(target_table)}\n"
                 "### Action Information\n"
                f"{format_table(action_table)}"
            )

        class EditOrExecuteRow(ActionRow["ModerationView"]):
            @button(label = "Edit", style = ButtonStyle.grey)
            async def btn_edit(self, interaction : Interaction, _button : Button[ModerationView]) -> None:
                if not self.view:
                    return

                await interaction.response.send_modal(
                    _ModerationModal(
                        modal.action_type,
                        modal.target,
                        purge_target = modal.purge_target,
                        edit_view    = self.view,
                        state        = modal,
                    ),
                )

            @button(label = "Execute", style = ButtonStyle.red)
            async def btn_execute(self, interaction : Interaction, _button : Button[ModerationView]) -> None:
                client = interaction.client
                moderator = interaction.user

                await interaction.response.defer(ephemeral = True)

                guild = interaction.guild
                if not guild or not isinstance(moderator, Member):
                    return

                actions = Actions(client, guild)

                match modal.action_type:
                    case ActionType.lockdown_add:
                        if not isinstance(modal.target, GuildMessageableChannel):
                            return

                        result = await actions.lockdown_add(
                            LockdownAddPayload(
                                moderator = moderator,
                                channel   = modal.target,
                                reason    = reason,
                            ),
                        )
                    case ActionType.lockdown_remove:
                        if not isinstance(modal.target, GuildMessageableChannel):
                            return

                        result = await actions.lockdown_remove(
                            LockdownRemovePayload(
                                moderator = moderator,
                                channel   = modal.target,
                                reason    = reason,
                            ),
                        )
                    case ActionType.ban_add:
                        if not isinstance(modal.target, Member):
                            return

                        seconds_to_delete = 7 * 86400
                        if dtd is not None:
                            with suppress(ValueError):
                                seconds_to_delete = int(dtd) * 86400

                        result = await actions.ban_add(
                            BanAddPayload(
                                moderator         = moderator,
                                target            = modal.target,
                                reason            = reason,
                                dm_user           = dm,
                                seconds_to_delete = seconds_to_delete,
                            ),
                        )
                    case ActionType.ban_remove:
                        if not isinstance(modal.target, User):
                            return

                        result = await actions.ban_remove(
                            BanRemovePayload(
                                moderator = moderator,
                                target    = modal.target,
                                reason    = reason,
                                dm_user   = dm,
                            ),
                        )
                    case ActionType.kick:
                        if not isinstance(modal.target, Member):
                            return

                        result = await actions.kick(
                            KickPayload(
                                moderator = moderator,
                                target    = modal.target,
                                reason    = reason,
                                dm_user   = dm,
                            ),
                        )
                    case ActionType.quarantine_add:
                        if not isinstance(modal.target, Member):
                            return

                        result = await actions.quarantine_add(
                            QuarantineAddPayload(
                                moderator = moderator,
                                target    = modal.target,
                                reason    = reason,
                                dm_user   = dm,
                            ),
                        )
                    case ActionType.quarantine_remove:
                        if not isinstance(modal.target, Member):
                            return

                        result = await actions.quarantine_remove(
                            QuarantineRemovePayload(
                                moderator = moderator,
                                target    = modal.target,
                                reason    = reason,
                                dm_user   = dm,
                            ),
                        )
                    case ActionType.timeout_add:
                        if not isinstance(modal.target, Member):
                            return

                        try:
                            timeout_length = int(length) if length is not None else 0
                        except ValueError:
                            timeout_length = 0

                        result = await actions.timeout_add(
                            TimeoutAddPayload(
                                moderator = moderator,
                                target    = modal.target,
                                reason    = reason,
                                dm_user   = dm,
                                length    = timeout_length,
                            ),
                        )
                    case ActionType.timeout_remove:
                        if not isinstance(modal.target, Member):
                            return

                        result = await actions.timeout_remove(
                            TimeoutRemovePayload(
                                moderator = moderator,
                                target    = modal.target,
                                reason    = reason,
                                dm_user   = dm,
                            ),
                        )
                    case ActionType.purge:
                        if not isinstance(modal.target, GuildMessageable):
                            return

                        result = await actions.purge(
                            PurgePayload(
                                moderator = moderator,
                                target    = purge_member,
                                reason    = reason,
                                channel   = modal.target,
                                amount    = amount or 0,
                                force     = force,
                            ),
                        )

                table : dict[str, str] = {}
                statuses : list[bool] = []

                notes : list[str] = []
                if not result.failed:
                    table[modal.action_type.readable()] = f"{ACCEPTED_EMOJI} Success."
                    statuses.append(True)
                else:
                    table[modal.action_type.readable()] = f"{DENIED_EMOJI} Failure."
                    statuses.append(False)

                if result.dmed is True:
                    table["DMed Member"] = f"{ACCEPTED_EMOJI} Success."
                    statuses.append(True)
                elif result.dmed is False:
                    table["DMed Member"] = f"{DENIED_EMOJI} Failure."
                    statuses.append(False)
                    notes.append("**DMed Member:** This failed because the target has their DMs closed.")

                if result.logged is True:
                    table["Logged"] = f"{ACCEPTED_EMOJI} Success."
                    statuses.append(True)
                elif result.logged is False:
                    table["Logged"] = f"{DENIED_EMOJI} Failure."
                    statuses.append(False)

                    if not await client.config(guild).get_moderation_logging_channel():
                        notes.append("**Logged:** This server has not set up a logging channel for moderation.")

                if modal.action_type == ActionType.purge and isinstance(result.data, int):
                    purge_line = f"Purged {result.data} message(s).\n"
                else:
                    purge_line = ""

                subtitle = (
                    f"{purge_line}"
                    f"{format_table(table)}"
                )

                footer = "\n-#".join(notes)

                if all(statuses):
                    title    = f"The {modal.name} was successful."
                    msg_type = MessageType.success
                elif any(statuses):
                    title    = f"The {modal.name} was partially successful."
                    msg_type = MessageType.warning
                else:
                    title    = f"The {modal.name} failed."
                    msg_type = MessageType.error

                result_view = LayoutView()
                result_view.add_item(
                    TextDisplay(
                        format_message(
                            msg_type,
                            title    = title,
                            subtitle = subtitle,
                            footer   = footer,
                            override = FormatOverride(
                                prefix      = False,
                                punctuation = PunctuationOverride(
                                    title  = False,
                                    footer = False,
                                ),
                            ),
                        ),
                    ),
                )

                await interaction.edit_original_response(view = result_view)

        class ModerationView(LayoutView):
            def __init__(self) -> None:
                super().__init__()
                self.add_items(
                    TextDisplay(summary),
                    VisibleLargeSeparator(),
                    EditOrExecuteRow(),
                )

        view = ModerationView()

        if self.edit_view:
            await interaction.edit_original_response(view = view)
        else:
            await interaction.followup.send(view = view, ephemeral = True)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# send_moderation_modal
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def send_moderation_modal(
    interaction  : Interaction,
    action_type  : ActionType,
    target       : Targetable,
    purge_target : Member | None = None,
) -> None:
    client = interaction.client
    user   = interaction.user

    guild = interaction.guild
    if not guild or not isinstance(user, Member):
        return

    check_target = purge_target if action_type == ActionType.purge else target

    if isinstance(check_target, Member):

        # ⸻ You cannot moderate yourself.

        if check_target == interaction.user:
            await send_bad_argument(
                interaction,
                subtitle = {"target" : "You cannot moderate yourself."},
            )
            return

        if not hierarchy(user, ">", check_target):
            if hierarchy(user, "=", check_target):
                if check_target == client.user:
                    await send_bad_argument(
                        interaction,
                        subtitle = {"target" : f"{check_target.mention} is equal to you in the hierarchy."},
                        footer   = "Nice try",
                    )
                    return

                await send_bad_argument(
                    interaction,
                    subtitle = {"target" : f"{check_target.mention} is equal to you in the hierarchy."},
                )
                return

            if check_target == client.user:
                await send_bad_argument(
                    interaction,
                    subtitle = {"target" : f"{check_target.mention} is higher in the hierarchy than you."},
                    footer   = "Nice try",
                )
                return

            await send_bad_argument(
                interaction,
                subtitle = {"target" : f"{check_target.mention} is higher in the hierarchy than you."},
            )
            return

        if check_target == client.user:
            await send_bad_argument(
                interaction,
                subtitle = {"target" : f"{check_target.mention} cannot be moderated."},
            )
            return

        quarantined_members = await QuarantineManager(client, guild).get_members()

        if action_type == ActionType.quarantine_remove and check_target not in quarantined_members:
            await send_bad_argument(
                interaction,
                subtitle = {"target" : f"{check_target.mention} is not quarantined."},
            )
            return

        if action_type == ActionType.quarantine_add and check_target in quarantined_members:
            await send_bad_argument(
                interaction,
                subtitle = {"target" : f"{check_target.mention} is already quarantined."},
            )
            return

    if action_type in {ActionType.lockdown_add, ActionType.lockdown_remove} and isinstance(target, GuildMessageable):
        lockdowned_channels = await LockdownManager(client, guild).get_channels()

        if action_type == ActionType.lockdown_add and target in lockdowned_channels:
            await send_bad_argument(
                interaction,
                subtitle = {"target" : f"{target.mention} is already in lockdown."},
            )
            return

        if action_type == ActionType.lockdown_remove and target not in lockdowned_channels:
            await send_bad_argument(
                interaction,
                subtitle = {"target" : f"{target.mention} is not in lockdown."},
            )
            return

    await interaction.response.send_modal(_ModerationModal(action_type, target, purge_target = purge_target))

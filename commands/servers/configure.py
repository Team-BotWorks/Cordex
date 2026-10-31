# pyright: reportIncompatibleMethodOverride = false

from typing import Self, final, override

from discord import ButtonStyle, ChannelType, Guild, Object, TextChannel

from bot import Interaction
from bot.ui import (
    ActionRow,
    Button,
    ButtonSection,
    ChannelSelect,
    Checkbox,
    Label,
    Modal,
    RoleSelect,
    TextDisplay,
)
from constants import (
    ACCEPTED_EMOJI,
    DENIED_EMOJI,
    FORUM_EMOJI,
    MODERATION_EMOJI,
    WARNING_EMOJI,
)
from core.exceptions import send_bad_argument, send_bad_operation
from core.moderation import QuarantineManager
from core.paginator import NamedPaginator, PageData

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /server configure Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class _MessagesEditSelect(ChannelSelect["_ConfigurationView"]):
    def __init__(self) -> None:
        super().__init__(
            placeholder   = "Select a channel...",
            channel_types = [ChannelType.text],
        )

    @override
    async def callback(self, interaction : Interaction) -> None:
        guild = interaction.guild
        if not guild:
            return

        channel = guild.get_channel(self.values[0].id)
        if not isinstance(channel, TextChannel):
            return

        me = guild.me
        if not me:
            return

        permissions = channel.permissions_for(me)
        if not permissions.send_messages:
            await send_bad_argument(
                interaction,
                title    = "set edit channel",
                subtitle = "I don't have permissions to send messages in that channel.",
            )
            return
        if not permissions.view_channel:
            await send_bad_argument(
                interaction,
                title    = "set edit channel",
                subtitle = "I don't have permissions to view that channel.",
            )
            return

        if not self.view:
            return

        previous = self.default_values
        self.default_values = [Object(id = channel.id)]

        try:
            await interaction.client.config(guild).set_messages_edit_logging_channel(channel)
            self.view.edit_id = channel.id
            self.view.update_pages()
            await interaction.response.edit_message(view = self.view)
        except Exception:
            self.default_values = previous
            await send_bad_operation(interaction, title = "update messages edit channel")
            raise


@final
class _MessagesDeleteSelect(ChannelSelect["_ConfigurationView"]):
    def __init__(self) -> None:
        super().__init__(
            placeholder   = "Select a channel...",
            channel_types = [ChannelType.text],
        )

    @override
    async def callback(self, interaction : Interaction) -> None:
        guild = interaction.guild
        if not guild:
            return

        channel = guild.get_channel(self.values[0].id)
        if not isinstance(channel, TextChannel):
            return

        me = guild.me
        if not me:
            return

        permissions = channel.permissions_for(me)
        if not permissions.send_messages:
            await send_bad_argument(
                interaction,
                title    = "set delete channel",
                subtitle = "I don't have permissions to send messages in that channel.",
            )
            return
        if not permissions.view_channel:
            await send_bad_argument(
                interaction,
                title    = "set delete channel",
                subtitle = "I don't have permissions to view that channel.",
            )
            return

        if not self.view:
            return

        previous = self.default_values
        self.default_values = [Object(id = channel.id)]

        try:
            await interaction.client.config(guild).set_messages_delete_logging_channel(channel)
            self.view.delete_id = channel.id
            self.view.update_pages()
            await interaction.response.edit_message(view = self.view)
        except Exception:
            self.default_values = previous
            await send_bad_operation(interaction, title = "update messages delete channel")
            raise


@final
class _MessagesPreviewButton(Button["_ConfigurationView"]):
    def __init__(self, *, enabled : bool) -> None:
        super().__init__(
            label = "Preview Enabled" if enabled else "Preview Disabled",
            style = ButtonStyle.green if enabled else ButtonStyle.red,
        )

    def update_state(self, *, enabled : bool) -> None:
        self.label = "Preview Enabled" if enabled else "Preview Disabled"
        self.style = ButtonStyle.green if enabled else ButtonStyle.red

    @override
    async def callback(self, interaction : Interaction) -> None:
        if not self.view:
            return

        new_state = not self.view.preview

        try:
            await interaction.client.config(self.view.guild).set_whether_messages_preview(new_state)
        except Exception:
            await send_bad_operation(interaction, title = "update messages preview setting")
            raise

        self.view.preview = new_state
        self.update_state(enabled = new_state)
        self.view.update_pages()

        await interaction.response.edit_message(view = self.view)


@final
class _ModerationLoggingSelect(ChannelSelect["_ConfigurationView"]):
    def __init__(self) -> None:
        super().__init__(
            placeholder   = "Select a channel...",
            channel_types = [ChannelType.text],
        )

    @override
    async def callback(self, interaction : Interaction) -> None:
        guild = interaction.guild
        if not guild:
            return

        channel = guild.get_channel(self.values[0].id)
        if not isinstance(channel, TextChannel):
            return

        me = guild.me
        if not me:
            return

        permissions = channel.permissions_for(me)
        if not permissions.send_messages:
            await send_bad_argument(
                interaction,
                title    = "set logging channel",
                subtitle = "I don't have permissions to send messages in that channel.",
            )
            return
        if not permissions.view_channel:
            await send_bad_argument(
                interaction,
                title    = "set logging channel",
                subtitle = "I don't have permissions to view that channel.",
            )
            return

        if not self.view:
            return

        previous = self.default_values
        self.default_values = [Object(id = channel.id)]

        try:
            await interaction.client.config(guild).set_moderation_logging_channel(channel)
            self.view.logging_id = channel.id
            self.view.update_pages()
            await interaction.response.edit_message(view = self.view)
        except Exception:
            self.default_values = previous
            await send_bad_operation(interaction, title = "update logging channel")
            raise


@final
class _ModerationQuarantineRoleSelect(RoleSelect["_ConfigurationView"]):
    def __init__(self) -> None:
        super().__init__(placeholder = "Select a role...")

    @override
    async def callback(self, interaction : Interaction) -> None:
        role     = self.values[0]
        previous = self.default_values

        self.default_values = [Object(id = role.id)]

        guild = interaction.guild
        if not guild:
            return

        if role >= guild.me.top_role:
            await send_bad_argument(
                interaction,
                title    = "set quarantine role",
                subtitle = "That role is above or equal to my highest role, so I can't assign it.",
            )

        if not self.view:
            return

        await interaction.response.defer()

        manager = QuarantineManager(interaction.client, guild)

        try:
            await interaction.client.config(guild).set_moderation_quarantine_role(role)
            await manager.enforce("Channels")
            await manager.enforce("Role")
        except Exception:
            self.default_values = previous
            await send_bad_operation(interaction, title = "update quarantine role")
            raise

        self.view.quarantine_id = role.id
        self.view.update_pages()

        await interaction.edit_original_response(view = self.view)


@final
class _ModerationQuarantineEnforceModal(Modal, title = "Quarantine Enforce"):
    def __init__(self, view : _ConfigurationView) -> None:
        super().__init__()
        self.view = view

        missing : list[str] = []

        if not view.guild.me or not view.guild.me.guild_permissions.manage_channels:
            missing.append("`Manage Channels`")
        if not view.guild.me or not view.guild.me.guild_permissions.manage_roles:
            missing.append("`Manage Roles`")

        self.warning = TextDisplay[Self](
           f"**{WARNING_EMOJI} Warning,**\n"
            "I lack the following permissions:\n"
           f"{"\n".join(f"- {permission}" for permission in missing)}\n"
            "Settings will have no effect and nothing will be enforced!",
        )

        self._channels = Checkbox[Self](default = view.enforce_channels)
        self.channels  = Label[Self](
            text        = "Channels",
            description = "Whether to automatically enforce permissions for the quarantine role on channels.",
            component   = self._channels,
        )

        self._roles = Checkbox[Self](default = view.enforce_roles)
        self.roles  = Label[Self](
            text        = "Roles",
            description = "Whether to automatically enforce permissions for the quarantine role on roles.",
            component   = self._roles,
        )

        if missing:
            self.add_item(self.warning)

        self.add_items(self.channels, self.roles)

    @override
    async def on_submit(self, interaction : Interaction) -> None:
        guild = interaction.guild
        if not guild:
            return

        config = interaction.client.config(guild)

        try:
            await config.set_whether_moderation_quarantine_enforce_channels(self._channels.value)
            await config.set_whether_moderation_quarantine_enforce_roles(self._roles.value)
        except Exception:
            await send_bad_operation(interaction, title = "update quarantine enforcement")
            raise

        await interaction.response.defer()

        channels = self._channels.value
        roles    = self._roles.value

        self.view.enforce_channels = channels
        self.view.enforce_roles    = roles
        self.view.update_pages()

        manager = QuarantineManager(interaction.client, guild)

        if channels:
            await manager.enforce("Channels")
        if roles:
            await manager.enforce("Role")

        await interaction.edit_original_response(view = self.view)


@final
class _ModerationQuarantineEnforceButton(Button["_ConfigurationView"]):
    def __init__(self) -> None:
        super().__init__(label = "Configure Enforcement")

    @override
    async def callback(self, interaction : Interaction) -> None:
        if not self.view:
            return

        await interaction.response.send_modal(_ModerationQuarantineEnforceModal(self.view))


@final
class _ConfigurationView(NamedPaginator):
    def __init__(
        self,
        guild            : Guild,
        *,
        edit_channel     : int | None,
        delete_channel   : int | None,
        logging_channel  : int | None,
        quarantine_role  : int | None,
        enforce_channels : bool,
        enforce_roles    : bool,
        preview          : bool,
    ) -> None:
        self.guild            = guild
        self.edit_id          = edit_channel
        self.delete_id        = delete_channel
        self.logging_id       = logging_channel
        self.quarantine_id    = quarantine_role
        self.enforce_channels = enforce_channels
        self.enforce_roles    = enforce_roles
        self.preview          = preview

        self.edit_select            = _MessagesEditSelect()
        self.delete_select          = _MessagesDeleteSelect()
        self.logging_select         = _ModerationLoggingSelect()
        self.quarantine_select      = _ModerationQuarantineRoleSelect()
        self.quarantine_enforce_btn = _ModerationQuarantineEnforceButton()
        self.preview_button         = _MessagesPreviewButton(enabled = self.preview)

        if self.edit_id:
            self.edit_select.default_values = [Object(id = self.edit_id)]
        if self.delete_id:
            self.delete_select.default_values = [Object(id = self.delete_id)]
        if self.logging_id:
            self.logging_select.default_values = [Object(id = self.logging_id)]
        if self.quarantine_id:
            self.quarantine_select.default_values = [Object(id = self.quarantine_id)]

        initial_pages = [
            PageData(
                name        = "Messages",
                emoji       = FORUM_EMOJI,
                description = "Manage message edit and delete logging as well as message link previews.",
                content     = [],
            ),
            PageData(
                name        = "Moderation",
                emoji       = MODERATION_EMOJI,
                description = "Manage moderation logging and the quarantine role.",
                content     = [],
            ),
        ]

        super().__init__(initial_pages, container = True)
        self.update_pages()

    def update_pages(self) -> None:
        edit = self.guild.get_channel(self.edit_id) if self.edit_id else None
        if edit:
            txt_edit = (
                f"{ACCEPTED_EMOJI} **Messages Edit Channel Set**\n"
                f"Message edits will be sent to {edit.mention}."
            )
        else:
            txt_edit = (
               f"{DENIED_EMOJI} **Messages Edit Channel Unset**\n"
                "Set one with the select below."
            )

        delete = self.guild.get_channel(self.delete_id) if self.delete_id else None
        if delete:
            txt_delete = (
                f"{ACCEPTED_EMOJI} **Messages Delete Channel Set**\n"
                f"Message deletions will be sent to {delete.mention}."
            )
        else:
            txt_delete = (
               f"{DENIED_EMOJI} **Messages Delete Channel Unset**\n"
                "Set one with the select below."
            )

        if self.preview:
            txt_preview = (
               f"{ACCEPTED_EMOJI} **Messages Preview Enabled**\n"
                "Message previews will be displayed for message links."
            )
        else:
            txt_preview = (
               f"{DENIED_EMOJI} **Messages Preview Disabled**\n"
                "Message previews will not be displayed for message links."
            )

        self.preview_button.update_state(enabled = self.preview)

        logging = self.guild.get_channel(self.logging_id) if self.logging_id else None
        if logging:
            txt_logging = (
                f"{ACCEPTED_EMOJI} **Logging Channel Set**\n"
                f"Moderation logs will be sent to {logging.mention}."
            )
        else:
            txt_logging = (
               f"{DENIED_EMOJI} **Logging Channel Unset**\n"
                "Set one with the select below."
            )

        quarantine = self.guild.get_role(self.quarantine_id) if self.quarantine_id else None
        if quarantine:
            issues : list[str] = []
            me = self.guild.me

            if me:
                if self.enforce_channels and not me.guild_permissions.manage_channels:
                    issues.append("I lack the `Manage Channels` permission to enforce channel permissions.")

                if self.enforce_roles and not me.guild_permissions.manage_roles:
                    issues.append("I lack the `Manage Roles` permission to enforce role permissions.")

                if not me.guild_permissions.manage_roles:
                    issues.append("I lack the `Manage Roles` permission to assign the quarantine role to members.")

                roles_by_pos = sorted(self.guild.roles, key = lambda r : r.position, reverse = True)
                top_role = roles_by_pos[0] if roles_by_pos else None

                if me.top_role != top_role:
                    issues.append("My highest role is not at the absolute top of the role hierarchy.")

                if me.top_role.position - quarantine.position != 1:
                    issues.append("The quarantine role is not directly below my highest role.")

            if issues:
                formatted_issues = "\n".join(f"- {issue}" for issue in issues)
                txt_quarantine = (
                    f"{WARNING_EMOJI} **Quarantine Role Misconfigured**\n"
                    f"Quarantined members will receive the {quarantine.mention} role, but issues were detected:\n"
                    f"{formatted_issues}"
                )
            else:
                txt_quarantine = (
                    f"{ACCEPTED_EMOJI} **Quarantine Role Set**\n"
                    f"Quarantined members will receive the {quarantine.mention} role."
                )
        else:
            txt_quarantine = (
                f"{DENIED_EMOJI} **Quarantine Role Unset**\n"
                f"Set one with the select below."
            )

        self.pages = [
            PageData(
                name        = "Messages",
                emoji       = FORUM_EMOJI,
                description = "Manage message edit and delete logging as well as message link previews.",
                content     = [
                    "# Messages",
                    TextDisplay(txt_edit),
                    ActionRow(self.edit_select),
                    TextDisplay(txt_delete),
                    ActionRow(self.delete_select),
                    ButtonSection(txt_preview, button = self.preview_button),
                ],
            ),
            PageData(
                name        = "Moderation",
                emoji       = MODERATION_EMOJI,
                description = "Manage moderation logging and the quarantine role.",
                content     = [
                    "# Moderation",
                    TextDisplay(txt_logging),
                    ActionRow(self.logging_select),
                    ButtonSection(txt_quarantine, button = self.quarantine_enforce_btn),
                    ActionRow(self.quarantine_select),
                ],
            ),
        ]


async def run_server_configure(interaction : Interaction) -> None:
    """
    Configure guild settings.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    """
    guild = interaction.guild
    if not guild:
        return

    config = interaction.client.config(guild)

    edit_channel     = await config.get_messages_edit_logging_channel()
    delete_channel   = await config.get_messages_delete_logging_channel()
    logging_channel  = await config.get_moderation_logging_channel()
    quarantine_role  = await config.get_moderation_quarantine_role()
    enforce_channels = await config.get_whether_moderation_quarantine_enforce_channels()
    enforce_roles    = await config.get_whether_moderation_quarantine_enforce_roles()
    preview          = await config.get_whether_messages_preview()

    view = _ConfigurationView(
        guild,
        edit_channel     = edit_channel.id    if edit_channel    else None,
        delete_channel   = delete_channel.id  if delete_channel  else None,
        logging_channel  = logging_channel.id if logging_channel else None,
        quarantine_role  = quarantine_role.id if quarantine_role else None,
        enforce_channels = enforce_channels,
        enforce_roles    = enforce_roles,
        preview          = preview,
    )
    await interaction.response.send_message(view = view, ephemeral = True)
    view.message = await interaction.original_response()

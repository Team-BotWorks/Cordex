# pyright: reportIncompatibleMethodOverride = false

from typing import Literal, Self, final, override

from discord import ButtonStyle, Color, HTTPException, SelectOption, TextStyle

from bot import Interaction
from bot.types import DisplayNameStyle
from bot.ui import (
    ActionRow,
    Button,
    ButtonSection,
    Confirmation,
    FileUpload,
    Label,
    Modal,
    Select,
    TextDisplay,
    TextInput,
)
from constants import (
    MEDIA_EMOJI,
    MEMBER_EMOJI,
    QUERY_EMOJI,
    DisplayNameEffect,
    DisplayNameFont,
)
from core.exceptions import send_bad_argument, send_bad_operation
from core.paginator import NamedPaginator, PageData
from core.responses import FormatOverride, MessageType, format_message

from ._base import COLOR_PATTERN, find_violation

type _ImageTypes = Literal["avatar", "banner"]
type _Category   = Literal["Name Style", "Avatar & Banner", "Biography"]

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# /server personalize Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class _FontSelect(Select["_PersonalizationView"]):
    def __init__(self) -> None:
        super().__init__(
            placeholder = "Select a font...",
            options     = [
                SelectOption(
                    label       = font.display_name,
                    value       = str(font.value),
                    description = font.description,
                    emoji       = font.emoji,
                ) for font in DisplayNameFont
            ],
        )

    @override
    async def callback(self, interaction : Interaction) -> None:
        if not self.view:
            return

        await self.view.apply(interaction, font = DisplayNameFont(int(self.values[0])))


@final
class _EffectSelect(Select["_PersonalizationView"]):
    def __init__(self) -> None:
        super().__init__(
            placeholder = "Select an effect...",
            options     = [
                SelectOption(
                    label       = effect.display_name,
                    value       = str(effect.value),
                    description = effect.description,
                ) for effect in DisplayNameEffect
            ],
        )

    @override
    async def callback(self, interaction : Interaction) -> None:
        if not self.view:
            return

        await self.view.apply(interaction, effect = DisplayNameEffect(int(self.values[0])))


@final
class _ColorsModal(Modal, title = "Editing Effect Colors"):
    def __init__(self, view : _PersonalizationView) -> None:
        super().__init__()
        self.view = view

        colors = "-".join(f"{color.value:06X}" for color in view.style.colors)

        self._colors = TextInput[Self](
            placeholder = "ABCDEF or ABCDEF-123456-...",
            default     = colors,
            min_length  = 6,
            max_length  = 34,
        )
        self.colors  = Label[Self](
            text        = "Color(s)",
            description = "The display name's color(s), as hex without the #.",
            component   = self._colors,
        )

        self.add_item(self.colors)

    @override
    async def on_submit(self, interaction : Interaction) -> None:
        value       = self._colors.value.strip()
        multi_color = self.view.style.effect in {
            DisplayNameEffect.prism,
            DisplayNameEffect.gradient,
            DisplayNameEffect.gummy,
        }
        color_set   = value.split("-")

        if not COLOR_PATTERN.match(value) or (not multi_color and len(color_set) > 1) or len(color_set) > 5:
            error = (
                "Prism, Gradient, and Gummy must have between 1 and 5 colors of the form `ABCDEF-123456-...`."
                if multi_color else
                "Color must be of the form `ABCDEF`."
            )

            await send_bad_argument(
                interaction,
                title    = "set display name colors",
                subtitle = {"colors" : error},
            )
            return

        await self.view.apply(
            interaction,
            colors = [Color(int(color, 16)) for color in color_set],
        )


@final
class _ColorsButton(Button["_PersonalizationView"]):
    def __init__(self) -> None:
        super().__init__(label = "Edit Effect Colors")

    @override
    async def callback(self, interaction : Interaction) -> None:
        if not self.view:
            return

        await interaction.response.send_modal(_ColorsModal(self.view))


@final
class _ImageModal(Modal):
    def __init__(self, view : _PersonalizationView, target : _ImageTypes) -> None:
        super().__init__(title = f"Editing {target.title()}")
        self.view   = view
        self.target = target

        self._upload = FileUpload[Self]()
        self.upload  = Label[Self](
            text        = target.title(),
            description = f"The new {target} image (PNG, JPG, or GIF).",
            component   = self._upload,
        )

        self.add_item(self.upload)

    @override
    async def on_submit(self, interaction : Interaction) -> None:
        guild = interaction.guild
        if not guild:
            return

        me = guild.me
        if not me:
            return

        attachment = self._upload.values[0]

        try:
            data = await attachment.read()
            if self.target == "avatar":
                member = await me.edit(avatar = data)
            else:
                member = await me.edit(banner = data)
        except HTTPException:
            await send_bad_operation(interaction, title = f"set {self.target}")
            return

        if not member:
            return

        if self.target == "avatar":
            self.view.avatar_url = member.guild_avatar.url if member.guild_avatar else None
        if self.target == "banner":
            self.view.banner_url = member.guild_banner.url if member.guild_banner else None

        self.view.update_pages()

        await interaction.response.edit_message(view = self.view)


@final
class _ImageButton(Button["_PersonalizationView"]):
    def __init__(self, target : _ImageTypes) -> None:
        super().__init__(label = f"Edit {target.title()}")
        self.target : _ImageTypes = target

    @override
    async def callback(self, interaction : Interaction) -> None:
        if not self.view:
            return

        await interaction.response.send_modal(_ImageModal(self.view, self.target))


@final
class _BioModal(Modal, title = "Editing Biography"):
    def __init__(self, view : _PersonalizationView) -> None:
        super().__init__()
        self.view = view

        self._bio = TextInput[Self](
            style       = TextStyle.paragraph,
            placeholder = "Write a short biography...",
            default     = view.biography,
            required    = False,
            max_length  = 300,
        )
        self.bio  = Label[Self](
            text        = "Biography",
            description = "The bot's server biography. Leave blank to remove it.",
            component   = self._bio,
        )

        self.add_item(self.bio)

    @override
    async def on_submit(self, interaction : Interaction) -> None:
        guild = interaction.guild
        if not guild:
            return

        me = guild.me
        if not me:
            return

        biography = self._bio.value.strip() or None

        if biography is not None and (violation := find_violation(biography)):
            await send_bad_argument(
                interaction,
                title    = "set biography",
                subtitle = {"biography" : violation},
            )
            return

        try:
            await me.edit(bio = biography)
        except HTTPException:
            await send_bad_operation(interaction, title = "set biography")
            return

        self.view.biography = biography
        self.view.update_pages()

        await interaction.response.edit_message(view = self.view)


@final
class _BioButton(Button["_PersonalizationView"]):
    def __init__(self) -> None:
        super().__init__(label = "Edit Biography")

    @override
    async def callback(self, interaction : Interaction) -> None:
        if not self.view:
            return

        await interaction.response.send_modal(_BioModal(self.view))


@final
class _ResetModal(Modal):
    def __init__(self, view : _PersonalizationView, category : _Category) -> None:
        super().__init__(title = f"Reset {category}")
        self.view     = view
        self.category = category

        candidates : list[tuple[str, str, bool]]

        match category:
            case "Name Style":
                candidates = [
                    ("font",   "Font",   view.style.font   != DisplayNameFont.default),
                    ("effect", "Effect", view.style.effect != DisplayNameEffect.solid),
                    ("colors", "Colors", bool(view.style.colors)),
                ]
            case "Avatar & Banner":
                candidates = [
                    ("avatar", "Avatar", bool(view.avatar_url)),
                    ("banner", "Banner", bool(view.banner_url)),
                ]
            case "Biography":
                candidates = [
                    ("biography", "Biography", bool(view.biography)),
                ]

        self._options = {key : label for key, label, configured in candidates if configured}

        options = [SelectOption(label = label, value = key) for key, label in self._options.items()]
        if len(options) > 1:
            options.append(
                SelectOption(
                    label       = f"All {category} Settings",
                    value       =  "all",
                    description = f"Reset every configured {category.lower()} setting at once.",
                ),
            )

        self._selection = Select[Self](placeholder = "Select what to reset...", options = options)
        self.selection  = Label[Self](
            text        =  "Setting",
            description = f"Choose which {category.lower()} setting to reset to its default.",
            component   = self._selection,
        )

        self.add_item(self.selection)

    @override
    async def on_submit(self, interaction : Interaction) -> None:
        guild = interaction.guild
        if not guild:
            return

        me = guild.me
        if not me:
            return

        view     = self.view
        category = self.category
        choice   = self._selection.values[0]

        keys   = set(self._options) if choice == "all" else {choice}
        target = f"all {category.lower()} settings" if choice == "all" else self._options[choice].lower()

        async def accept(confirmation_interaction : Interaction) -> None:
            await confirmation_interaction.response.defer()

            client = confirmation_interaction.client

            try:
                if keys & {"font", "effect", "colors"}:
                    font   = DisplayNameFont.default if "font"   in keys else view.style.font
                    effect = DisplayNameEffect.solid if "effect" in keys else view.style.effect
                    colors = []                      if "colors" in keys else list(view.style.colors)

                    if effect not in {
                        DisplayNameEffect.prism,
                        DisplayNameEffect.gradient,
                        DisplayNameEffect.gummy,
                    }:
                        colors = colors[:1]

                    await client.set_name_style(guild, font = font, effect = effect, colors = colors)
                    view.style = await client.get_name_style(guild)
                if "avatar" in keys:
                    await me.edit(avatar = None)
                    view.avatar_url = None
                if "banner" in keys:
                    await me.edit(banner = None)
                    view.banner_url = None
                if "biography" in keys:
                    await me.edit(bio = None)
                    view.biography = None
            except Exception:
                await send_bad_operation(confirmation_interaction, title = f"reset {target}")
                raise
            finally:
                view.update_pages()
                if view.message:
                    await view.message.edit(view = view)

            await confirmation_interaction.delete_original_response()

        async def deny(confirmation_interaction : Interaction) -> None:
            await confirmation_interaction.response.defer()
            await confirmation_interaction.delete_original_response()

        confirmation = Confirmation(
            TextDisplay(
                format_message(
                    MessageType.warning,
                    title    =  "Warning",
                    subtitle = f"This will reset {target} to {"its" if choice != "all" else "their"} default state. This cannot be undone!",
                    override = FormatOverride(prefix = False),
                ),
            ),
            acceptance_label = "Reset",
            denial_label     = "Cancel",
            on_acceptance    = accept,
            on_denial        = deny,
        )

        await interaction.response.send_message(view = confirmation, ephemeral = True)
        confirmation.message = await interaction.original_response()


@final
class _ResetButton(Button["_PersonalizationView"]):
    def __init__(self, category : _Category) -> None:
        super().__init__(label = "Reset", style = ButtonStyle.red)
        self.category : _Category = category

    @override
    async def callback(self, interaction : Interaction) -> None:
        if not self.view:
            return

        await interaction.response.send_modal(_ResetModal(self.view, self.category))


@final
class _PersonalizationView(NamedPaginator):
    def __init__(
        self,
        style      : DisplayNameStyle,
        *,
        avatar_url : str | None,
        banner_url : str | None,
        biography  : str | None,
    ) -> None:
        self.style      = style
        self.avatar_url = avatar_url
        self.banner_url = banner_url
        self.biography  = biography

        self.font_select      = _FontSelect()
        self.effect_select    = _EffectSelect()
        self.color_button     = _ColorsButton()
        self.avatar_button    = _ImageButton("avatar")
        self.banner_button    = _ImageButton("banner")
        self.biography_button = _BioButton()

        self.style_reset_button     = _ResetButton("Name Style")
        self.media_reset_button     = _ResetButton("Avatar & Banner")
        self.biography_reset_button = _ResetButton("Biography")

        initial_pages = [
            PageData(
                name        = "Name Style",
                emoji       = MEMBER_EMOJI,
                description = "Personalize my display name style's font, effect, and colors.",
                content     = [],
            ),
            PageData(
                name        = "Avatar & Banner",
                emoji       = MEDIA_EMOJI,
                description = "Personalize my avatar and banner.",
                content     = [],
            ),
            PageData(
                name        = "Biography",
                emoji       = QUERY_EMOJI,
                description = "Personalize my biography.",
                content     = [],
            ),
        ]

        super().__init__(initial_pages, container = True)
        self.update_pages()

    async def apply(
        self,
        interaction : Interaction,
        *,
        font        : DisplayNameFont   | None = None,
        effect      : DisplayNameEffect | None = None,
        colors      : list[Color]       | None = None,
    ) -> None:
        guild = interaction.guild
        if not guild:
            return

        font       = font   if font   is not None else self.style.font
        effect     = effect if effect is not None else self.style.effect
        color_list = colors if colors is not None else self.style.colors

        multi_color = effect in {
            DisplayNameEffect.prism,
            DisplayNameEffect.gradient,
            DisplayNameEffect.gummy,
        }

        if multi_color:
            if len(color_list) > 5:
                color_list = color_list[:5]
        elif len(color_list) > 1:
            if colors is not None:
                await send_bad_argument(
                    interaction,
                    title    = "set display name style",
                    subtitle = {"colors" : "Only Prism, Gradient, and Gummy accept multiple colors."},
                )
                return

            color_list = color_list[:1]

        try:
            await interaction.client.set_name_style(
                guild,
                font   = font,
                effect = effect,
                colors = color_list,
            )
        except Exception:
            await send_bad_operation(interaction, title = "set display name style")
            return

        self.style = await interaction.client.get_name_style(guild)

        self.update_pages()

        await interaction.response.edit_message(view = self)

    def update_pages(self) -> None:
        colors = "-".join(f"`{color.value:06X}`" for color in self.style.colors) or "None"

        for option in self.font_select.options:
            option.default = option.value == str(self.style.font.value)

        for option in self.effect_select.options:
            option.default = option.value == str(self.style.effect.value)

        s = "s" if len(self.style.colors) > 1 else ""
        txt_colors = (
           f"**Color{s}**\n"
           f"{colors}\n"
            "Set one hex color, or up to five for Prism, Gradient, and Gummy."
        )

        txt_avatar = (
            (
                f"**Avatar**\n"
                f"[View current avatar.]({self.avatar_url})"
            ) if self.avatar_url else (
                "**Avatar**\n"
                "No server avatar is set."
            )
        )

        txt_banner = (
            (
                f"**Banner**\n"
                f"[View current banner.]({self.banner_url})"
            ) if self.banner_url else (
                "**Banner**\n"
                "No server banner is set."
            )
        )

        txt_biography = (
            (
                "**Biography**\n"
                f">>> {self.biography}"
            ) if self.biography else (
                "**Biography**\n"
                "No server biography is set."
            )
        )

        self.style_reset_button.disabled = not (
            self.style.font   != DisplayNameFont.default
            or self.style.effect != DisplayNameEffect.solid
            or self.style.colors
        )
        self.media_reset_button.disabled     = not (self.avatar_url or self.banner_url)
        self.biography_reset_button.disabled = not self.biography

        self.pages = [
            PageData(
                name        = "Name Style",
                emoji       = MEMBER_EMOJI,
                description = "Personalize my display name style's font, effect, and colors.",
                content     = [
                    ButtonSection("# Name Style", button = self.style_reset_button),
                    TextDisplay("**Font**"),
                    ActionRow(self.font_select),
                    TextDisplay("**Effect**"),
                    ActionRow(self.effect_select),
                    ButtonSection(txt_colors, button = self.color_button),
                ],
            ),
            PageData(
                name        = "Avatar & Banner",
                emoji       = MEDIA_EMOJI,
                description = "Personalize my avatar and banner.",
                content     = [
                    ButtonSection("# Avatar & Banner", button = self.media_reset_button),
                    ButtonSection(txt_avatar, button = self.avatar_button),
                    ButtonSection(txt_banner, button = self.banner_button),
                ],
            ),
            PageData(
                name        = "Biography",
                emoji       = QUERY_EMOJI,
                description = "Personalize my biography.",
                content     = [
                    ButtonSection("# Biography", button = self.biography_reset_button),
                    ButtonSection(txt_biography, button = self.biography_button),
                ],
            ),
        ]


async def run_server_personalize(interaction : Interaction) -> None:
    """
    Personalize Cordex's avatar, banner, biography, and display name style.

    Parameters
    ----------
    interaction : `Interaction`
        The interaction context to run the command with.
    """
    guild = interaction.guild
    if not guild:
        return

    style     = await interaction.client.get_name_style(guild)
    biography = await interaction.client.get_biography(guild)

    me = guild.me
    if not me:
        return

    avatar = me.guild_avatar
    banner = me.guild_banner

    view = _PersonalizationView(
        style,
        avatar_url = avatar.url if avatar else None,
        banner_url = banner.url if banner else None,
        biography  = biography,
    )
    await interaction.response.send_message(view = view, ephemeral = True)
    view.message = await interaction.original_response()

# pyright: reportIncompatibleMethodOverride = false

from typing import Literal, Self, final, override

from discord import Color, HTTPException, SelectOption, TextStyle

from bot import Interaction
from bot.types import DisplayNameStyle
from bot.ui import (
    ActionRow,
    Button,
    ButtonSection,
    Checkbox,
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

from ._base import COLOR_PATTERN, find_violation

type _ImageTypes = Literal["avatar", "banner"]

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

        await self.view.apply(interaction, font = DisplayNameFont[self.values[0]])


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

        await self.view.apply(interaction, effect = DisplayNameEffect[self.values[0]])


@final
class _ColorsModal(Modal, title = "Edit Color(s)"):
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

        self.add_items(self.colors)

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
        super().__init__(label = "Edit Colors")

    @override
    async def callback(self, interaction : Interaction) -> None:
        if not self.view:
            return

        await interaction.response.send_modal(_ColorsModal(self.view))


@final
class _ImageModal(Modal):
    def __init__(self, view : _PersonalizationView, target : _ImageTypes) -> None:
        super().__init__(title = f"Edit {target.title()}")
        self.view   = view
        self.target = target

        self._upload = FileUpload[Self](required = False)
        self.upload  = Label[Self](
            text        = target.title(),
            description = f"The new {target} image (PNG, JPG, or GIF).",
            component   = self._upload,
        )

        self._reset = Checkbox[Self]()
        self.reset  = Label[Self](
            text        =  "Reset",
            description = f"Whether to remove the current {target} instead of uploading one.",
            component   = self._reset,
        )

        self.add_items(self.upload, self.reset)

    @override
    async def on_submit(self, interaction : Interaction) -> None:
        guild = interaction.guild
        if not guild:
            return

        me = guild.me
        if not me:
            return

        reset      = self._reset.value
        attachment = self._upload.values[0] if self._upload.values else None

        if not reset and attachment is None:
            await send_bad_argument(
                interaction,
                title    = f"set {self.target}",
                subtitle = f"Upload an image or choose to reset the {self.target}.",
            )
            return

        if not reset and attachment is not None and not (attachment.content_type or "").startswith("image/"):
            await send_bad_argument(
                interaction,
                title    = f"set {self.target}",
                subtitle =  "The file must be an image.",
            )
            return

        try:
            data = await attachment.read() if attachment is not None and not reset else None
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
class _BioModal(Modal, title = "Edit Bio"):
    def __init__(self, view : _PersonalizationView) -> None:
        super().__init__()
        self.view = view

        self._bio = TextInput[Self](
            style       = TextStyle.paragraph,
            placeholder = "Write a short biography...",
            default     = view.bio,
            required    = False,
            max_length  = 300,
        )
        self.bio  = Label[Self](
            text        = "Biography",
            description = "The bot's server biography. Leave blank to remove it.",
            component   = self._bio,
        )

        self.add_items(self.bio)

    @override
    async def on_submit(self, interaction : Interaction) -> None:
        guild = interaction.guild
        if not guild:
            return

        me = guild.me
        if not me:
            return

        bio = self._bio.value.strip() or None

        if bio is not None and (violation := find_violation(bio)):
            await send_bad_argument(
                interaction,
                title    = "set bio",
                subtitle = {"bio" : violation},
            )
            return

        try:
            await me.edit(bio = bio)
        except HTTPException:
            await send_bad_operation(interaction, title = "set bio")
            return

        self.view.bio = bio
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
class _PersonalizationView(NamedPaginator):
    def __init__(
        self,
        style      : DisplayNameStyle,
        *,
        avatar_url : str | None,
        banner_url : str | None,
        bio        : str | None,
    ) -> None:
        self.style      = style
        self.avatar_url = avatar_url
        self.banner_url = banner_url
        self.bio        = bio

        self.font_select   = _FontSelect()
        self.effect_select = _EffectSelect()
        self.color_button  = _ColorsButton()
        self.avatar_button = _ImageButton("avatar")
        self.banner_button = _ImageButton("banner")
        self.bio_button    = _BioButton()

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
            option.default = option.value == self.style.font.name

        for option in self.effect_select.options:
            option.default = option.value == self.style.effect.name

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

        bio = "\n".join(f"> {line}" for line in (self.bio or "").splitlines())

        txt_bio = (
            (
                "**Biography**\n"
                f"{bio}"
            ) if self.bio else (
                "**Biography**\n"
                "No server biography is set."
            )
        )

        self.pages = [
            PageData(
                name        = "Name Style",
                emoji       = MEMBER_EMOJI,
                description = "Personalize my display name style's font, effect, and colors.",
                content     = [
                    "# Name Style",
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
                    "# Avatar & Banner",
                    ButtonSection(txt_avatar, button = self.avatar_button),
                    ButtonSection(txt_banner, button = self.banner_button),
                ],
            ),
            PageData(
                name        = "Biography",
                emoji       = QUERY_EMOJI,
                description = "Personalize my biography.",
                content     = [
                    "# Biography",
                    ButtonSection(txt_bio, button = self.bio_button),
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

    style = await interaction.client.get_name_style(guild)
    bio   = await interaction.client.get_bio(guild)

    me = guild.me
    if not me:
        return

    avatar = me.guild_avatar
    banner = me.guild_banner

    view = _PersonalizationView(
        style,
        avatar_url = avatar.url if avatar else None,
        banner_url = banner.url if banner else None,
        bio        = bio,
    )
    await interaction.response.send_message(view = view, ephemeral = True)
    view.message = await interaction.original_response()

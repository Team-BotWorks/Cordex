# ruff: file-ignore[quoted-annotation]
# pyright: reportIncompatibleMethodOverride = false
from collections.abc import Awaitable, Callable, Iterable
from contextlib import suppress
from typing import TYPE_CHECKING, Self, final, override
from warnings import warn

from discord import (
    ButtonStyle,
    Color,
    HTTPException,
    Member,
    Message,
    NotFound,
    SeparatorSpacing,
    TextStyle,
    User,
)
from discord.ui import (
    ActionRow,
    Button,
    ChannelSelect,
    Checkbox,
    CheckboxGroup,
    File,
    FileUpload,
    Item,
    Label,
    MediaGallery,
    MentionableSelect,
    RadioGroup,
    RoleSelect,
    Section,
    Select,
    Separator,
    Thumbnail,
    UserSelect,
    button,
    select,
)
from discord.ui import Container as BaseContainer
from discord.ui import LayoutView as BaseView
from discord.ui import Modal as BaseModal
from discord.ui import TextDisplay as BaseTextDisplay
from discord.ui import TextInput as BaseTextInput
from discord.ui import View as SimpleView

from constants import ACCEPTED_NOBG_EMOJI, DENIED_NOBG_EMOJI

__all__ = [
    "ActionRow",
    "Button",
    "ChannelSelect",
    "Checkbox",
    "CheckboxGroup",
    "File",
    "FileUpload",
    "Item",
    "Label",
    "MediaGallery",
    "MentionableSelect",
    "Modal",
    "RadioGroup",
    "RoleSelect",
    "Section",
    "Select",
    "Separator",
    "SimpleView",
    "TextInput",
    "Thumbnail",
    "UserSelect",
    "button",
    "select",
]

if TYPE_CHECKING:
    from .context import Interaction

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Bot UI
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

type _OnChoice = Callable[[Interaction], Awaitable[None]]

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# View
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class View(BaseView):
    def __init__(self, *children : Item[View | Self], timeout : float | None = 600) -> None:
        super().__init__(timeout = timeout)
        self.append_items(children)

    @override
    async def interaction_check(self, _interaction : "Interaction") -> bool:
        return True

    def add_text(self, text : str, /) -> Self:
        self.add_item(TextDisplay(text))
        return self

    def add_items(self, *items : Item[View | Self]) -> Self:
        if len(items) == 1:
            warn(
                "Prefer View.add_item over View.add_items if only one item is being added.",
                category   = UserWarning,
                stacklevel = 2,
            )

        for item in items:
            self.add_item(item)

        return self

    def append_items(self, items : Iterable[Item[View | Self]], /) -> Self:
        for item in items:
            self.add_item(item)

        return self

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# InteractiveView
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class InteractiveView(View):
    def __init__(self, *children : Item[View | Self], timeout : float | None = 600) -> None:
        super().__init__(*children, timeout = timeout)
        self.message : Message       | None = None
        self.user    : User | Member | None = None

    async def _expire(self) -> None:
        for item in self.walk_children():
            if isinstance(item, Button):
                if item.style == ButtonStyle.url:
                    continue
                item.disabled = True
            if isinstance(item, Select):
                item.disabled = True

        if self.message:
            try:
                await self.message.edit(view = self)
            except NotFound:
                pass
            except HTTPException:
                with suppress(HTTPException):
                    await self.message.delete()

    @override
    async def on_timeout(self) -> None:
        await self._expire()

    @override
    async def interaction_check(self, interaction : "Interaction") -> bool:
        from core.responses import FormatOverride, MessageType, format_send  # ruff: ignore[import-outside-top-level]

        if self.user is not None and interaction.user != self.user:
            await format_send(
                interaction,
                MessageType.warning,
                title    = "Hey!",
                subtitle = "This view isn't yours!",
                override = FormatOverride(prefix = False),
            )
            return False

        return True

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Confirmation
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class _AcceptButton(Button["Confirmation"]):
    def __init__(self, label : str, on_choice : _OnChoice) -> None:
        super().__init__(label = label, style = ButtonStyle.green, emoji = ACCEPTED_NOBG_EMOJI)
        self.on_choice = on_choice

    @override
    async def callback(self, interaction : "Interaction") -> None:
        await self.on_choice(interaction)
        if self.view:
            await self.view.on_choice()


@final
class _DenyButton(Button["Confirmation"]):
    def __init__(self, label : str, on_choice : _OnChoice) -> None:
        super().__init__(label = label, style = ButtonStyle.red, emoji = DENIED_NOBG_EMOJI)
        self.on_choice = on_choice

    @override
    async def callback(self, interaction : "Interaction") -> None:
        await self.on_choice(interaction)
        if self.view:
            await self.view.on_choice()


class Confirmation(InteractiveView):
    def __init__(
        self,
        *children        : Item[View | Self],
        timeout          : float | None = None,
        acceptance_label : str          = "Continue",
        denial_label     : str          = "Abort",
        on_acceptance    : _OnChoice,
        on_denial        : _OnChoice,
    ) -> None:
        super().__init__(timeout = timeout)

        self.acceptance_button : Button[Confirmation]    = _AcceptButton(acceptance_label, on_acceptance)
        self.denial_button     : Button[Confirmation]    = _DenyButton(denial_label, on_denial)
        self.choice_row        : ActionRow[Confirmation] = ActionRow(self.acceptance_button, self.denial_button)

        self._acceptance_label : str = acceptance_label
        self._denial_label     : str = denial_label

        self._on_acceptance : _OnChoice = on_acceptance
        self._on_denial     : _OnChoice = on_denial

        self.append_items(children)
        self.add_item(self.choice_row)

    async def on_choice(self) -> None:
        await self._expire()


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Modal
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class Modal(BaseModal):
    """
    Represents a Discord modal.

    Parameters
    ----------
    title : `str`
        The title of the modal. This may only be up to 45 characters.

    Attributes
    ----------
    title : `str`
        The title of the modal.
    """

    @override
    async def on_submit(self, interaction : "Interaction", /) -> None:
        pass

    def add_text(self, text : str, /) -> Self:
        """
        Add text to the modal.

        Parameters
        ----------
        text : `str`
            The text to add to the modal.
        /

        Returns
        -------
        `Self`
            The modal.
        """
        self.add_item(TextDisplay(text))
        return self

    def add_items(self, *items : Item[Self]) -> Self:
        """
        Add items to the modal.

        Parameters
        ----------
        *items : `Item[Self]`
            The items to add to the modal.

        Returns
        -------
        `Self`
            The modal.
        """
        if len(items) == 1:
            warn(
                "Prefer Modal.add_item over Modal.add_items if only one item is being added.",
                category   = UserWarning,
                stacklevel = 2,
            )

        for item in items:
            self.add_item(item)

        return self

    def append_items(self, items : Iterable[Item[Self]], /) -> Self:
        """
        Unpack an iterable of items and add them to the modal.

        Parameters
        ----------
        items : `Iterable[Item[Self]]`
            The iterable of items to unpack and add to the modal.
        /

        Returns
        -------
        `Self`
            The modal.
        """
        for item in items:
            self.add_item(item)

        return self

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# TextDisplay
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class TextDisplay[V : View | Modal](BaseTextDisplay[V]):  # pyright: ignore[reportInvalidTypeArguments]
    def __init__(self, content : str, /) -> None:
        super().__init__(content)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Container
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class Container[V : View](BaseContainer[V]):
    def __init__(
        self,
        *children : Item[V],
        color     : Color | None = None,
        spoiler   : bool         = False,
    ) -> None:
        super().__init__(*children, accent_color = color, spoiler = spoiler)

    @property
    def color(self) -> Color | None:
        return self.accent_color

    @color.setter
    def color(self, value : Color | None, /) -> None:
        self.accent_color : Color | None = value

    def add_text(self, text : str, /) -> Self:
        self.add_item(TextDisplay(text))
        return self

    def add_items(self, *items : Item[V]) -> Self:
        if len(items) == 1:
            warn(
                "Prefer Container.add_item over Container.add_items if only one item is being added.",
                category   = UserWarning,
                stacklevel = 2,
            )

        for item in items:
            self.add_item(item)

        return self

    def append_items(self, items : Iterable[Item[V]], /) -> Self:
        for item in items:
            self.add_item(item)

        return self

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# TextInput
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class TextInput[M : Modal](BaseTextInput[M]):
    """
    Represents a Discord text input.

    Parameters
    ----------
    style : `TextStyle`
        The style of the text input.
    placeholder : `str`
        The placeholder text to display when the text input is empty. This may only be up to 100 characters.
    default : `str | None`
        The default value of the text input. This may only be up to 4000 characters.
    required : `bool`
        Whether the text input is required.
    min_length : `int | None`
        The minimum length of the text input. This must be between 0 and 4000.
    max_length : `int | None`
        The maximum length of the text input. This must be between 1 and 4000.
    """

    def __init__(
        self,
        *,
        style       : TextStyle  = TextStyle.short,
        placeholder : str | None = None,
        default     : str | None = None,
        required    : bool       = True,
        min_length  : int | None = None,
        max_length  : int | None = None,
    ) -> None:
        super().__init__(
            style       = style,
            placeholder = placeholder,
            default     = default,
            required    = required,
            min_length  = min_length,
            max_length  = max_length,
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Separator Variants
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


_large = SeparatorSpacing.large
_small = SeparatorSpacing.small


@final
class VisibleLargeSeparator[V : View](Separator[V]):
    def __init__(self) -> None:
        super().__init__(visible = True, spacing = _large)


@final
class VisibleSmallSeparator[V : View](Separator[V]):
    def __init__(self) -> None:
        super().__init__(visible = True, spacing = _small)


@final
class HiddenLargeSeparator[V : View](Separator[V]):
    def __init__(self) -> None:
        super().__init__(visible = False, spacing = _large)


@final
class HiddenSmallSeparator[V : View](Separator[V]):
    def __init__(self) -> None:
        super().__init__(visible = False, spacing = _small)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Section Variants
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class ButtonSection[V : View](Section[V]):
    def __init__(self, *args : str | TextDisplay[V], button : Button[V]) -> None:
        super().__init__(*args, accessory = button)
        self.button : Button[V] = button


class ThumbnailSection[V : View](Section[V]):
    def __init__(self, *args : str | TextDisplay[V], thumbnail : Thumbnail[V]) -> None:
        super().__init__(*args, accessory = thumbnail)
        self.thumbnail : Thumbnail[V] = thumbnail

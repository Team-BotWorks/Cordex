from asyncio import sleep
from secrets import choice, randbelow
from typing import final

from discord import Member, Message, User
from discord.app_commands import Command
from discord.ext.commands import Cog

from bot import Cordex, Interaction
from core.responses import FormatOverride, MessageType, PunctuationOverride, format_send

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Fun
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class Fun(Cog):
    """Who doesn't like a little bit of fun? Responds to messages greeting the bot, and does a rare, joke rejection for some commands."""

    def __init__(self, bot : Cordex) -> None:
        super().__init__()
        self.bot = bot

        self.rejected_members : dict[Member | User, tuple[str, int]] = {}

    @Cog.listener("on_interaction")
    async def _listener_fun_command(self, interaction : Interaction) -> None:
        user    = interaction.user
        command = interaction.command
        if not command:
            return

        if not isinstance(command, Command):
            return

        if command.qualified_name.startswith("moderation"):
            return

        if user in self.rejected_members:
            name, count = self.rejected_members[user]

            if command.qualified_name == name:
                count += 1
                self.rejected_members[user] = name, count

                if count == 2:
                    await format_send(
                        interaction,
                        MessageType.error,
                        title    = "run command",
                        subtitle = "Mmm mmm. 🙂‍↔️",
                        footer   = "Hehe. Okay okay, run the command again",
                        override = FormatOverride(punctuation = PunctuationOverride(subtitle = False)),
                    )
                elif count == 3:
                    await format_send(
                        interaction,
                        MessageType.error,
                        title    = "run command",
                        subtitle = "Nuh uh!",
                        footer   = "Alright I'm done. Bye!",
                    )
                    del self.rejected_members[user]
                return

        if user not in self.rejected_members and randbelow(1000) == 0:
            self.rejected_members[user] = (command.qualified_name, 1)
            await format_send(
                interaction,
                MessageType.error,
                title    = "run command",
                subtitle = "No",
                footer   = "I'm just kidding! Run the command again",
            )
            return

    @Cog.listener("on_message")
    async def _listener_fun_message(self, message : Message) -> None:
        content   = message.content.lower()
        reference = message.reference
        author    = message.author

        # ⸻ Block bots and the bot itself.

        if author.bot or author == self.bot.user:
            return

        # ⸻ Replies.

        if reference and isinstance(
            resolved_reference := reference.resolved,
            Message,
        ) and resolved_reference.author == self.bot.user:
            words = [word.strip(".,!?\"'") for word in content.split()]
            greetings = any(trigger in words for trigger in ["hi", "hello"])

            if greetings:
                responses = ["Hello, human.", "Greetings.", "Hi..?", "Hi... I guess..."]

                async with message.channel.typing():
                    await sleep(1)
                    await message.reply(content = choice(responses))


async def setup(bot : Cordex) -> None:  # ruff: ignore[undocumented-public-function]
    cog = Fun(bot)
    await bot.add_cog(cog)

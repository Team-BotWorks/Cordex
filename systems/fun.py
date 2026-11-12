from asyncio import sleep
from datetime import UTC, date, datetime
from secrets import choice, randbelow
from typing import final, override

from discord import CustomActivity, Member, Message, User
from discord.app_commands import Command
from discord.ext.commands import Cog
from discord.ext.tasks import loop

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

        self._loop_fun.start()

    @override
    async def cog_unload(self) -> None:
        self._loop_fun.cancel()

    @loop(minutes = 10)
    async def _loop_fun(self) -> None:
        today = datetime.now(UTC).date()
        age = today.year - 2026

        november_first_weekday = date(today.year, 11, 1).weekday()
        thanksgiving_day = 22 + (3 - november_first_weekday) % 7

        holidays = {
            (2, 14)                :  "Happy Valentine's Day!",
            (6, 9)                 : f"Happy birthday to me! Today, I am {age} years old.",
            (7, 4)                 :  "Happy 4th of July!",
            (10, 31)               :  "Happy Halloween!",
            (11, thanksgiving_day) :  "Happy Thanksgiving!",
            (12, 25)               :  "Happy Holidays!",
            (12, 31)               :  "Happy New Year's Eve!",
            (1, 1)                 :  "Happy New Year!",
        }

        target_text = holidays.get((today.month, today.day))
        activity = self.bot.activity
        activity_text = (activity.name or activity.state) if isinstance(activity, CustomActivity) else None

        if target_text is not None:
            if activity_text != target_text:
                await self.bot.change_presence(activity = CustomActivity(target_text))
        elif activity is not None:
            await self.bot.change_presence(activity = None)

    @_loop_fun.before_loop
    async def _beforeloop_fun(self) -> None:
        await self.bot.wait_until_ready()

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

        if author.bot:
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
    await bot.add_cog(Fun(bot))

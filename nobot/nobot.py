from cogs.utils.dataIO import dataIO
from discord.ext import commands
from .utils import checks
import os


class NoBots:
    """All bots will be kicked when they join. Toggable per server."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/nobots/settings.json')

    async def _save_settings(self):
        dataIO.save_json('data/nobots/settings.json', self.settings)

    @commands.command(pass_context=True, name='nobots')
    @checks.mod_or_permissions(administrator=True)
    async def _nobots(self, context):
        """NoBots toggle"""
        server = context.message.server
        if server.id not in self.settings:
            self.settings[server.id] = False
        if self.settings[server.id]:
            self.settings[server.id] = False
            message = ':gear: Bot protection disabled.'
        else:
            self.settings[server.id] = True
            message = ':gear: Bot protection enabled.'
        await self._save_settings()
        await self.bot.say(message)

    async def _on_member_join(self, member):
        server = member.server
        if server.id in self.settings and member.bot:
            if self.settings[server.id]:
                await self.bot.kick(member)
                await self.bot.send_message(member, 'The owner of **{}** has bot protection enabled. You are not allowed to enter.'.format(server.name))


def check_folder():
    if not os.path.exists('data/nobots'):
        print('Creating data/nobots folder...')
        os.makedirs('data/nobots')


def check_file():
    if not dataIO.is_valid_json('data/nobots/settings.json'):
        print('Creating default settings.json...')
        dataIO.save_json('data/nobots/settings.json', {})


def setup(bot):
    check_folder()
    check_file()
    cog = NoBots(bot)
    bot.add_listener(cog._on_member_join, "on_member_join")
    bot.add_cog(cog)

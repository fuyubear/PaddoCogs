import os
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO


class Away:
    """Le away cog"""
    def __init__(self, bot):
        self.bot = bot
        self.away_data = 'data/away/away.json'

    async def listener(self, message):
        tmp = {}
        for mention in message.mentions:
            tmp[mention] = True
        if message.author.id != self.bot.user.id:
            data = dataIO.load_json(self.away_data)
            for mention in tmp:
                if mention.mention in data:
                    avatar = mention.avatar_url if mention.avatar else mention.default_avatar_url
                    if data[mention.mention]['MESSAGE']:
                        em = discord.Embed(color=discord.Color.blue())
                        em.set_author(name='{} is currently away'.format(mention.display_name), icon_url=avatar)
                    else:
                        em = discord.Embed(description=data[mention.mention]['MESSAGE'], color=discord.Color.blue())
                        em.set_author(name='{} is currently away'.format(mention.display_name), icon_url=avatar)
                    await self.bot.send_message(message.channel, embed=em)

    @commands.command(pass_context=True, name="away")
    async def _away(self, context, *message: str):
        """Tell the bot you're away or back."""
        data = dataIO.load_json(self.away_data)
        author_mention = context.message.author.mention
        if author_mention in data:
            del data[author_mention]
            msg = 'You\'re now back.'
        else:
            data[context.message.author.mention] = {}
            if len(str(message)) < 256:
                data[context.message.author.mention]['MESSAGE'] = " ".join(context.message.clean_content.split()[1:])
            else:
                data[context.message.author.mention]['MESSAGE'] = True
            msg = 'You\'re now set as away.'
        dataIO.save_json(self.away_data, data)
        await self.bot.say(msg)


def check_folder():
    if not os.path.exists('data/away'):
        print('Creating data/away folder...')
        os.makedirs('data/away')


def check_file():
    away = {}
    f = 'data/away/away.json'
    if not dataIO.is_valid_json(f):
        dataIO.save_json(f, away)
        print('Creating default away.json...')


def setup(bot):
    check_folder()
    check_file()
    n = Away(bot)
    bot.add_listener(n.listener, 'on_message')
    bot.add_cog(n)

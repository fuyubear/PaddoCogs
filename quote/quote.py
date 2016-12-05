import discord
from discord.ext import commands


class Quote:
    """
    Quote someone with the message id
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, name='quote')
    async def _q(self, context, message_id):
        """
        Quote someone with the message id
        """
        channel = context.message.channel
        try:
            message = await self.bot.get_message(channel, message_id)
            content = '\a\n'+message.clean_content
            author = message.author
            timestamp = message.timestamp.strftime('%d-%m-%y %H:%M:%S')
            em = discord.Embed(title='Quoting {} at {}'.format(author.name, timestamp), description=content, color=discord.Color.blue())
            await self.bot.say(embed=em)
        except discord.NotFound:
            em = discord.Embed(description='I\'m sorry, that message doesn\'t exist', color=discord.Color.red())
            await self.bot.say(embed=em)
        except Exception as error:
            await self.bot.say(error)


def setup(bot):
    bot.add_cog(Quote(bot))

from __main__ import send_cmd_help
from cogs.utils.dataIO import dataIO
from discord.ext import commands
from .utils import checks
import aiohttp
import discord
import re
import os


class YouTube:
    """Le YouTube Cog"""
    def __init__(self, bot):
        self.bot = bot
        self.settings = 'data/youtube/settings.json'
        self.youtube_regex = (
          r'(https?://)?(www\.)?'
          '(youtube|youtu|youtube-nocookie)\.(com|be)/'
          '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

    async def listener(self, message):
        if not message.channel.is_private:
            if message.author.id != self.bot.user.id:
                server_id = message.server.id
                data = dataIO.load_json(self.settings)
                if server_id not in data:
                    enable_delete = False
                    enable_meta = False
                    enable_url = False
                else:
                    enable_delete = data[server_id]['ENABLE_DELETE']
                    enable_meta = data[server_id]['ENABLE_META']
                    enable_url = data[server_id]['ENABLE_URL']
                if enable_meta:
                    url = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content)
                    if url:
                        is_youtube_link = re.match(self.youtube_regex, url[0])
                        if is_youtube_link:
                            yt_url = "http://www.youtube.com/oembed?url={0}&format=json".format(url[0])
                            metadata = await self.get_json(yt_url)
                            if enable_url:
                                msg = '**Title:** _{}_\n**Uploader:** _{}_\n_YouTube url by {}_\n\n{}'.format(metadata['title'], metadata['author_name'], message.author.name, url[0])
                                if enable_delete:
                                    try:
                                        await self.bot.delete_message(message)
                                    except:
                                        pass
                            else:
                                if enable_url:
                                    x = '\n_YouTube url by {}_'.format(message.author.name)
                                else:
                                    x = ''
                                msg = '**Title:** _{}_\n**Uploader:** _{}_{}'.format(metadata['title'], metadata['author_name'], x)
                            await self.bot.send_message(message.channel, msg)

    async def get_song_metadata(self, song_url):
        """
        Returns JSON object containing metadata about the song.
        """

        is_youtube_link = re.match(self.youtube_regex, song_url)

        if is_youtube_link:
            url = "http://www.youtube.com/oembed?url={0}&format=json".format(song_url)
            result = await self.get_json(url)
        else:
            result = {"title": "A song "}
        return result

    async def get_json(self, url):
        """
        Returns the JSON from an URL.
        Expects the url to be valid and return a JSON object.
        """
        async with aiohttp.get(url) as r:
            result = await r.json()
        return result

    @commands.command(pass_context=True, name='youtube', no_pm=True)
    async def _youtube(self, context, *, query: str):
        """Search on Youtube"""
        try:
            url = 'https://www.youtube.com/results?'
            payload = {'search_query': " ".join(query), 'hl': 'en'}
            headers = {'user-agent': 'Red-cog/1.0'}
            conn = aiohttp.TCPConnector(verify_ssl=False)
            session = aiohttp.ClientSession(connector=conn)
            async with session.get(url, params=payload, headers=headers) as r:
                result = await r.text()
            session.close()
            yt_find = re.findall(r'href=\"\/watch\?v=(.{11})', result)
            url = 'https://www.youtube.com/watch?v={}'.format(yt_find[0])
            metadata = await self.get_song_metadata(url)
            em = discord.Embed(title=metadata['author_name'], color=discord.Color.red(), url=metadata['author_url'])
            em.set_author(name=metadata['title'], url=url)
            em.set_image(url=metadata['thumbnail_url'])
            # em.video.url = url
            # em.video.width = 480
            # em.video.height = 270
            await self.bot.say(embed=em)
        except Exception as e:
            message = 'Something went terribly wrong! [{}]'.format(e)
            await self.bot.say(message)

    @commands.group(pass_context=True, name='youtubetoggle', aliases=['ytoggle'])
    @checks.mod_or_permissions(administrator=True)
    async def _youtubetoggle(self, context):
        """
        Toggle metadata and preview features
        """
        data = dataIO.load_json(self.settings)
        server_id = context.message.server.id
        if server_id not in data:
            data[server_id] = {}
            data[server_id]['ENABLE_URL'] = False
            data[server_id]['ENABLE_DELETE'] = False
            data[server_id]['ENABLE_META'] = False
            dataIO.save_json(self.settings, data)
        if context.invoked_subcommand is None:
            await send_cmd_help(context)

    @_youtubetoggle.command(pass_context=True, name='url')
    async def _url(self, context):
        """
        Toggle showing url
        """
        data = dataIO.load_json(self.settings)
        server_id = context.message.server.id
        if data[server_id]['ENABLE_URL'] is False:
            data[server_id]['ENABLE_URL'] = True
            message = 'URL now enabled'
        elif data[server_id]['ENABLE_URL'] is True:
            data[server_id]['ENABLE_URL'] = False
            message = 'URL now disabled'
        else:
            pass
        dataIO.save_json(self.settings, data)
        await self.bot.say(message)

    @_youtubetoggle.command(pass_context=True, name='meta')
    async def _meta(self, context):
        """
        Toggle showing metadata
        """
        data = dataIO.load_json(self.settings)
        server_id = context.message.server.id
        if data[server_id]['ENABLE_META'] is False:
            data[server_id]['ENABLE_META'] = True
            message = 'Metadata now enabled'
        elif data[server_id]['ENABLE_META'] is True:
            data[server_id]['ENABLE_META'] = False
            message = 'Metadata now disabled'
        else:
            pass
        dataIO.save_json(self.settings, data)
        await self.bot.say('`{}`'.format(message))

    @_youtubetoggle.command(pass_context=True, name='delete')
    async def _delete(self, context):
        """
        Toggle deleting message
        """
        data = dataIO.load_json(self.settings)
        server_id = context.message.server.id
        if data[server_id]['ENABLE_DELETE'] is False:
            data[server_id]['ENABLE_DELETE'] = True
            message = 'Delete now enabled'
        elif data[server_id]['ENABLE_DELETE'] is True:
            data[server_id]['ENABLE_DELETE'] = False
            message = 'Delete now disabled'
        else:
            pass
        dataIO.save_json(self.settings, data)
        await self.bot.say('`{}`'.format(message))


def check_folder():
    if not os.path.exists("data/youtube"):
        print("Creating data/youtube folder...")
        os.makedirs("data/youtube")


def check_file():
    data = {}
    f = "data/youtube/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default settings.json...")
        dataIO.save_json(f, data)


def setup(bot):
    n = YouTube(bot)
    check_folder()
    check_file()
    bot.add_listener(n.listener, "on_message")
    bot.add_cog(n)

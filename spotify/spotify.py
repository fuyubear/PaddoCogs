import discord
import aiohttp
from discord.ext import commands


class Spotify:
    def __init__(self, bot):
        self.bot = bot

    async def _api_request(self, payload):
        url = 'https://api.spotify.com/v1/search'
        headers = {'user-agent': 'Red-cog/1.0'}
        conn = aiohttp.TCPConnector()
        session = aiohttp.ClientSession(connector=conn)
        async with session.get(url, params=payload, headers=headers) as r:
            data = await r.json()
        session.close()
        return data

    @commands.command(pass_context=True, name='spotify')
    async def _spotify(self, context, *, query: str):
        """Search for a song on Spotify
        """
        payload = {}
        payload['q'] = ''.join(query)
        payload['type'] = 'track'
        payload['limit'] = '1'
        r = await self._api_request(payload)
        if r['tracks']['total'] > 0:
            items = r['tracks']['items']
            item = items[0]
            track = item['name']
            artist = item['artists'][0]['name']
            url = item['external_urls']['spotify']
            image = item['album']['images'][0]['url']
            em = discord.Embed(title='{} - {}'.format(artist, track), url=url)
            em.set_image(url=image)
            await self.bot.say(embed=em)
        else:
            await self.bot.say('**I\'m sorry, but I couldn\'t find anything.**')


def setup(bot):
    n = Spotify(bot)
    bot.add_cog(n)

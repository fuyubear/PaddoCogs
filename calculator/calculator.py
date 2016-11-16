import re
import discord
from math import *
from random import *
from discord.ext import commands


class Calculator:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, name='calculator')
    async def _calc(self, context, *, m):
        m = ''.join(m)
        math_filter = re.findall(r'[\[\]\-()*+/0-9=., ]|random|randint|choice|randrange|True|False|if|and|or|else|is|acos|acosh|asin|asinh|atan|atan2|atanh|ceil|copysign|cos|cosh|degrees|e|erf|erfc|exp|expm1|fabs|factorial|floor|fmod|frexp|fsum|gamma|gcd|hypot|inf|isclose|isfinite|isinf|isnan|ldexp|lgamma|log|log10|log1p|log2|modf|nan|pi|pow|radians|sin|sinh|sqrt|tan|tanh', m)
        calculate_stuff = eval(''.join(math_filter))
        if len(str(calculate_stuff)) > 0:
            em = discord.Embed(color=discord.Color.blue())
            em.add_field(inline=False, name='Input', value=m)
            em.add_field(inline=False, name='\a', value='\a')
            em.add_field(inline=False, name='Result', value=calculate_stuff)
            await self.bot.say(embed=em)
            # await self.bot.say(calculate_stuff)


def setup(bot):
    bot.add_cog(Calculator(bot))
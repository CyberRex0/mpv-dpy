import discord
from discord.ext import commands
import glob
import config

bot = commands.Bot(intents=discord.Intents.all(), command_prefix='t!')

@bot.event
async def on_ready():
    print('Bot ready')
    for file in glob.glob("cogs/*.py"):
        await bot.load_extension(file.replace('/', '.')[:-3])

bot.run(config.TOKEN)
import discord
from discord.ext.commands import Bot
import sqlite3
import builtins

bot = Bot(command_prefix = '/', intents = discord.Intents().all())
connection = sqlite3.connect('./assets/omnibus.db')
cursor = connection.cursor()

builtins.bot = bot
builtins.connection = connection
builtins.cursor = cursor

import commands
import events

bot.run('ODI2OTk1ODEwODMwOTA5NDQw.YGUl3g.E21kdCxubWPzmRfHrcnQZRXP0pE')
connection.close()
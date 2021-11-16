import discord
from discord import FFmpegPCMAudio
from discord.errors import ClientException
from google_translate_py import Translator
from pycountry import languages
from youtube_dl import YoutubeDL
from threading import Thread
from time import sleep
from builtins import bot

import youtube_dl

from image_object import Image
from os import system as exec
from requests import get
from secrets import token_urlsafe as create_token

translator = Translator()
voice_clients = dict()

@bot.event
async def on_ready():
    global voice_clients
    async for guild in bot.fetch_guilds(limit=None):
        voice_clients[str(guild.id)] = None

def download(downloader, url, filename):
    downloader.download([url])
    exec(f"rm {filename}")

@bot.command(name="translate")
async def translate(ctx, tolanguage):
    tolanguage = languages.lookup(tolanguage).alpha_2

    await ctx.channel.trigger_typing()
    history = await ctx.channel.history(limit=5).flatten()
    
    message = None
    i = 1
    while (message == None):
        if i >= len(history):
            history = await ctx.channel.history(limit=len(history) + 5).flatten()
        elif history[i].content:
            message = history[i].content
        i += 1

    translation = translator.translate(message, "", tolanguage)

    # if there are any channel or user @s, google translate adds an
    # untintentional space, which is removed here
    translation = translation.replace("<@! ", "<@!")
    translation = translation.replace("<# ", "<#")
    
    await ctx.send(f"**Translation:** {translation}")

@bot.command(name="caption")
async def caption(ctx, *, input):
    input = input.replace("\"", "\\\"")

    input = input.replace("\\n", chr(10))

    await ctx.channel.trigger_typing()
    history = await ctx.channel.history(limit=5).flatten()

    file = None
    i = 1
    while file == None:
        if i >= len(history):
            history = await ctx.channel.history(limit=len(history) + 5).flatten()

        elif history[i].attachments:
            if history[i].attachments[0].content_type.find("image") != -1:
                file = history[i].attachments[0]
                file = Image(create_token(10) + ".gif", file.url, file.width, file.height)
        elif history[i].embeds:
            if history[i].embeds[0].type.find("image") != -1:
                file = history[i].embeds[0]
                file = Image(create_token(10) + ".gif", file.url, file.thumbnail.width, file.thumbnail.height)
        i += 1

  
    response = get(file.url, allow_redirects=True)
    open(f"image_processing/{file.name}", "wb").write(response.content)
  
    # character"s height is 2 times larger than its width
    # minimum font size is 1/10th of the original image height
    # max font size is 1/4th of the original image height
    # text has 20 pixel padding all around
    font_size = 4
    output = ""
    if len(input) * (file.height / 4) / 2 > file.width - 20:
        while len(input) * (file.height / font_size) / 2 > file.width - 20:
            font_size += 1

        if font_size > 12:
            font_size = 12
            # index 0 is the last break in words that breaks the line properly
            # index 1 is the last character that can break the line properly
            cursors = [0, 0]
            line_start = 0
            for i in range(len(input)):
                if (i - line_start) * (file.height / font_size) / 2 < file.width - 20:
                    if input[i] == " ":
                        cursors[0] = i
                    cursors[1] = i
                    i += 1

                else:
                    # if there were no spaces detected in the line of text
                    if cursors[0] == 0:
                        output += input[line_start:cursors[1] + 1] + chr(10)
                        line_start = cursors[1]
                    else:
                        output += input[line_start:cursors[0] + 1] + chr(10)
                        line_start = cursors[0]

            # because the last line is within the bounds of the image, it is never added to the output
            output += input[line_start:]
        else:
            output = input

    else:
        output = input
  
    line_count = output.count(chr(10)) + 1
    caption_height = int(line_count * (file.height / font_size * 1.45)) + 10
    exec(f'''convert image_processing/{file.name} \
            -gravity south \
            -background white \
            -extent {file.width}x{file.height + caption_height} \
            image_processing/{file.name}''')

    exec(f'''convert image_processing/{file.name} \
            -gravity north \
            -undercolor white \
            -fill black \
            -font assets/caption_font.otf \
            -pointsize {file.height / font_size} \
            -annotate +0+10 "{output}" \
            image_processing/{file.name}''')

    await ctx.send(file = discord.File(f"image_processing/{file.name}"))
    exec(f"rm image_processing/{file.name}")

@bot.command(name="play")
async def play(ctx, *, input):
    if not ctx.author.voice:
        await ctx.send("Please make sure you're in a voice channel before playing music")
        return

    url = ""

    if input.find("https://www.youtube.com/watch?v=") != -1 or input.find("https://youtu.be/") != -1:
        response = get(input)
        if response.text.find("This video isn't available anymore") == -1:
            url = input
        else:
            await ctx.send("Sorry, that is not a valid youtube link, please try another")
            return
    else:
        response = get("https://www.youtube.com/results?search_query=" + input)
        watch_code_pos = response.text.find("/watch?v=") + len("/watch?v=")

        url = response.text[watch_code_pos:]
        url = "https://www.youtube.com/watch?v=" + url[:11]

    filename = "audio_play/" + create_token(10) + ".wav"
    options = {
        "format": "bestaudio",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "192",
        }],
        "outtmpl": filename
    }

    downloader = YoutubeDL(options)
    video_data = downloader.extract_info(url, download=False)
    Thread(target=download, args=(downloader, url, filename,)).start()

    matched = False
    for vc in bot.voice_clients:
        if vc.channel == ctx.author.voice.channel:
            matched = True

    global voice_clients
    if not matched:
        if voice_clients[str(ctx.guild.id)] != None:
            await voice_clients[str(ctx.guild.id)].disconnect()
        voice_clients[str(ctx.guild.id)] = await ctx.message.author.voice.channel.connect()

    # we add the .part exensions because we want to play it before it finishes downloading
    # wait until the file exists to start playing
    while True:
        try:
            open(filename + ".part", "rb").close()
            break
        except:
            continue

    if not voice_clients[str(ctx.guild.id)].is_playing():
        voice_clients[str(ctx.guild.id)].play(FFmpegPCMAudio(filename + ".part"))
        await ctx.send(f"Now playing: `{video_data['title']}`")
    else:
        await ctx.send("Please wait until the current song is finished playing before requesting another one")

@bot.command(name="stop")
async def stop(ctx):
    if (ctx.author.voice.channel == None):
        await ctx.send("Please join a voice channel to control the bot")
        return

    matched = False
    for vc in bot.voice_clients:
        if vc.channel == ctx.author.voice.channel:
            matched = True

    if matched:
        voice_clients[str(ctx.guild.id)].stop()
    else:
        await ctx.send("If you would like the bot to stop playing, you will need to be in the same voice channel")
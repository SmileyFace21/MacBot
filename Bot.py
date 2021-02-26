import asyncio
import datetime
import os
import subprocess
import sys
import time
import pafy
from Song import Song
from discord.ext import commands
from google_images_download import google_images_download
from youtube_dl import YoutubeDL
from requests import get
from discord import FFmpegPCMAudio
from discord.ext import commands
import config
import discord
import giphy_client
import json
import helperMethods

bot = commands.Bot(command_prefix="pp ")
methods = helperMethods

musicQueue = {}

@bot.event
async def on_guild_join(ctx):
    guildInfo = {
                    "guild_id": ctx.id,
                    "totalTimes": {},
                    "startTimes": {},
                    "activeGif": {}
                },

    methods.write(guildInfo, ctx.id)


@bot.command("reset")
async def reset(ctx):
    guildInfo = {
        "guild_id": 762464564498399302,
        "totalTimes": {},
        "startTimes": {},
        "activeMedia": {}
    }

    methods.write(guildInfo, ctx.guild.id)


@bot.command("gif")
async def findGif(ctx):
    message = ctx.message.content[7:]
    try:
        giphy = giphy_client.DefaultApi()
        response = giphy.gifs_search_get(config.giphy_key, message).to_dict().get("data")
        gifLinks = []
        for item in response:
            gifLinks.append(item.get("images").get("fixed_height").get("url"))
        embed = discord.Embed(title="Results for " + message + " (1)", url=gifLinks[0], color=discord.Color.blurple())
        embed.set_image(url=gifLinks[0])

        # send message and save links, count, and message id into json file
        sent = await ctx.message.channel.send(embed=embed)
        await sent.add_reaction("⬅")
        await sent.add_reaction("➡")
        info = methods.read(ctx.guild.id)
        info.get("activeMedia").update({"media": gifLinks, "count": 0, "message_id": sent.id, "title": message})
        methods.write(info, ctx.guild.id)


    except:
        embed = discord.Embed(title="Could not find results", color=discord.Color.blurple())
        await ctx.message.channel.send(embed=embed)


@bot.command("pic")
async def getPic(ctx):
    try:
        links = []
        string = ctx.message.content[7:]

        response = google_images_download.googleimagesdownload()
        arguments = {
            "keywords": string,
            "limit": 25,
            "print_urls": True,
            "no_download": True,
        }
        sub = subprocess.Popen("googleimagesdownload -k \"" + string + "\" -l 25 -nd", shell=True,
                               stdout=subprocess.PIPE)
        output = sub.communicate()[0].decode('utf-8')

        for line in output.split("\r\n"):
            if line.startswith("Image URL: "):
                links.append(line.replace("Image URL: ", ""))

        embed = discord.Embed(title="Results for " + string + " (1)", url=links[0], color=discord.Color.blurple())
        embed.set_image(url=links[0])

        # send message and save links, count, and message id into json file
        sent = await ctx.message.channel.send(embed=embed)
        await sent.add_reaction("⬅")
        await sent.add_reaction("➡")
        info = methods.read(ctx.guild.id)
        info.get("activeMedia").update({"media": links, "count": 0, "message_id": sent.id, "title": string})
        methods.write(info, ctx.guild.id)
    except:
        embed = discord.Embed(title="Could not find results", color=discord.Color.blurple())
        await ctx.message.channel.send(embed=embed)


@bot.event
async def on_reaction_add(reaction, user):
    if user.bot == False:
        info = methods.read(reaction.message.guild.id)
        activeMedia = info.get("activeMedia")
        messageId = info.get("activeMedia").get("message_id")
        if messageId == reaction.message.id:
            if reaction.emoji == "➡":
                message = await reaction.message.channel.fetch_message(messageId)
                count = activeMedia.get("count")
                if count == len(activeMedia.get("media")) - 1:
                    count = 0
                else:
                    count += 1
                embed = discord.Embed(title="Results for " + activeMedia.get("title") + " (" + str(count + 1) + ")",
                                      url=activeMedia.get("media")[count], color=discord.Color.blurple())
                embed.set_image(url=activeMedia.get("media")[count])
                await message.remove_reaction(emoji="➡", member=user)
                await message.edit(embed=embed)
                info.get("activeMedia").update({"count": count})
                methods.write(info, reaction.message.guild.id)
            else:
                message = await reaction.message.channel.fetch_message(messageId)
                count = activeMedia.get("count")
                if count == 0:
                    count = len(activeMedia.get("media")) - 1
                else:
                    count -= 1
                embed = discord.Embed(title="Results for " + activeMedia.get("title") + " (" + str(count + 1) + ")",
                                      url=activeMedia.get("media")[count], color=discord.Color.blurple())
                embed.set_image(url=activeMedia.get("media")[count])
                await message.remove_reaction(emoji="⬅", member=user)
                await message.edit(embed=embed)
                info.get("activeMedia").update({"count": count})
                methods.write(info, reaction.message.guild.id)


songs = asyncio.Queue()
play_next_song = asyncio.Event()

async def sendPlayingMessage(ctx):
    currentSong = musicQueue[ctx.guild.id][0]
    embed = discord.Embed(title="Now Playing " + currentSong.name, url="https://youtube.com/watch?v=" + currentSong.ytId, color=discord.Color.blurple())
    embed.set_thumbnail(url=currentSong.thumbnail)
    await ctx.message.channel.send(embed=embed)

async def audio_player_task(ctx):
    global musicQueue
    while len(musicQueue[ctx.guild.id]) > 0:
        try:
            nextSong = musicQueue[ctx.guild.id][0].url
            musicQueue[ctx.guild.id][0].timestamp = time.time()
            player = await createPlayer(nextSong)
            voice_client = ctx.guild.voice_client
            await sendPlayingMessage(ctx)
            await playSong(voice_client, player, ctx)
        except:
            pass

async def playSong(voice_client, player, ctx):
    voice_client.play(player, after=lambda e: toggle_next(ctx))
    while voice_client.is_playing() or voice_client.is_paused():
        await asyncio.sleep(2)

def toggle_next(ctx):
    musicQueue[ctx.guild.id].pop(0)
    # bot.loop.create_task(audio_player_task(ctx))


@bot.command(aliases=["p"])
async def play(ctx, *, query):
    global musicQueue
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if ctx.message.author.voice is not None:
        channel = ctx.message.author.voice.channel
        if voice_client is None:
            voice = await channel.connect()
        elif not voice_client.is_connected():
            voice = await channel.connect()
        elif channel != voice_client.channel:
            await voice_client.move_to(channel)
        else:
            voice = voice_client

        result = search(query)
        url = result['formats'][0]['url']
        ytId = result['id']
        name = result['title']
        thumbnail = result['thumbnails'][0]['url']
        video = pafy.new("https://youtube.com/watch?v=" + ytId)
        duration = video.length
        songObj = Song(url, name, ytId, thumbnail, duration)
        try:
            musicQueue[ctx.guild.id].append(songObj)
        except:
            musicQueue[ctx.guild.id] = [songObj]

        if not voice.is_playing():
            bot.loop.create_task(audio_player_task(ctx))
        else:
            currentSong = musicQueue[ctx.guild.id][len(musicQueue[ctx.guild.id])-1]
            embed = discord.Embed(title="Queued " + currentSong.name,
                                  url="https://youtube.com/watch?v=" + currentSong.ytId, color=discord.Color.blurple())
            embed.set_thumbnail(url=currentSong.thumbnail)
            await ctx.message.channel.send(embed=embed)
    else:
        embed = discord.Embed(title=":X: You must be connected to a voice channel to use this command", color=discord.Color.blurple())




@bot.command("skip")
async def skip(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    voice_client.stop()
    await ctx.message.add_reaction("👍")

@bot.command("pause")
async def pause(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    voice_client.pause()
    await ctx.message.add_reaction("👍")

@bot.command("resume")
async def pause(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    voice_client.resume()
    await ctx.message.add_reaction("👍")

@bot.command("remove")
async def remove(ctx, message):
    try:
        numQueue = int(message)
        if numQueue > 0:
            currentQueue = musicQueue[ctx.guild.id]
            removed = currentQueue.pop(numQueue)
            embed = discord.Embed(title="Removed " + removed.name, url="https://youtube.com/watch?v=" + removed.ytId, color=discord.Color.blurple())
            embed.set_thumbnail(url=removed.thumbnail)
            await ctx.message.channel.send(embed=embed)
        else:
          raise Exception("can't remove song that is playing")
    except:
        embed = discord.Embed(title=":x: This queue number is invalid", color=discord.Color.blurple())
        await ctx.message.channel.send(embed=embed)

@bot.command(aliases=["q"])
async def queue(ctx):
    currentQueue = musicQueue[ctx.guild.id]
    bodyText = ""
    count = 0
    for item in currentQueue:
        if count == 0:
            bodyText = "Now Playing: **[" + item.name + "](https://youtube.com/watch?v=" + item.ytId + ")**\n\n"
        else:
            bodyText += str(count) + ". **[" + item.name + "](https://youtube.com/watch?v=" + item.ytId + ")**\n\n"
        count += 1
    embed = discord.Embed(title="Music Queue for " + ctx.guild.name, description=bodyText, color=discord.Color.blurple())
    await ctx.message.channel.send(embed=embed)


@bot.command(aliases=["nowplaying", "np", "now-playing"])
async def now_playing(ctx):
    currentTime = time.time()
    currentSong = musicQueue[ctx.guild.id][0]
    secTime = currentTime - currentSong.timestamp
    formatTime = str(datetime.timedelta(seconds=secTime)).split(":")
    formatDuration = str(datetime.timedelta(seconds=currentSong.duration)).split(":")
    bodyText = "`"
    if formatTime[0] != "0":
        bodyText += formatTime[0] + "h "
    if formatTime[1] != "00":
        if formatTime[1][0] == "0":
            bodyText += formatTime[1][1] + "m "
        else:
            bodyText += formatTime[1] + "m "
    bodyText += str(round(float(formatTime[2]))) + "s / "
    if formatDuration[0] != "0":
        bodyText += formatDuration[0] + "h "
    if formatDuration[1] != "00":
        if formatDuration[1][0] == "0":
            bodyText += formatDuration[1][1] + "m "
        else:
            bodyText += formatDuration[1] + "m "
    bodyText += str(round(float(formatDuration[2])))  +"s`"
    embed = discord.Embed(title="Now Playing", description="[" + currentSong.name + "](https://youtube.com/watch?v=" + currentSong.ytId + ") " + bodyText, color=discord.Color.blurple())
    await ctx.message.channel.send(embed=embed)
    print(formatTime)
    print(formatDuration)

def search(query):
    with YoutubeDL({'format': 'bestaudio', 'noplaylist': 'True'}) as ydl:
        try:
            get(query)
            info = ydl.extract_info(url=query, download=False)['entries'][0]
        except:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            print(info)
        else:
            info = ydl.extract_info(query, download=False)
        info['formats'] = [info['formats'][0]]
    return info



async def createPlayer(source):
    FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
    player = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(source, **FFMPEG_OPTS), volume=1)
    return player



bot.run(config.token)

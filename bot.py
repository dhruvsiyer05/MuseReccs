import discord
from discord.ext import commands
import yt_dlp
import os
from dotenv import load_dotenv, dotenv_values
import asyncio
import random
from playlist_manager import playlists_setup

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix = ".", intents=intents) 

music_queue =  {}
voice_clients = {}
current_song = {}

yt_dl_options = {
    "format": "bestaudio/best", 
    "default_search": "ytsearch1",
    'audioformat': 'mp3'
}

ytdl = yt_dlp.YoutubeDL(yt_dl_options)
ffmpeg = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 
    'options': '-vn'
}

bot_commands = [
    {"name": "play <song name>", "description": "Plays a song. If a song is already playing, adds the requested song to the queue. Duplicate songs that already exist in the queue will not be added."},
    {"name": "queue", "description": "Shows the current music queue."},
    {"name": "pause", "description": "Pauses the currently playing song."},
    {"name": "resume", "description": "Resumes the paused song."},
    {"name": "stop", "description": "Stops the music and disconnects the bot from the voice channel."},
    {"name": "skip", "description": "Skips the current song and plays the next one in the queue."},
    {"name": "remove <int>", "description": "Removes a song from the queue at the specified index. For example, '.remove 2' removes the song at position 2 in the queue."},
    {"name": "shuffle", "description": "Shuffles the entire music queue."},
    {"name": "help", "description": "Shows this message."},
]

@bot.event
async def on_ready():
    print("Bot is ready!")

bot.remove_command("help") #Overrides existing help command in discord.py 

@bot.command("help")
async def help_showcase(ctx):
    try:
        help_embed = discord.Embed(
            title="Bot Commands",
            description="Here are all the commands that this bot provides:",
            color=discord.Color.green()
        )

        for command in bot_commands:
            help_embed.add_field(name=f"**.{command['name']}**", value=command['description'], inline=False)

        await ctx.send(embed=help_embed)

    except Exception as e:
            print(e)

@bot.event
async def play_next(ctx):
    if ctx.guild.id in music_queue and music_queue[ctx.guild.id]:
        next_song = music_queue[ctx.guild.id].pop(0)   
        await play(ctx, search = next_song['search'])
    else:
        pass

@bot.command("play")
async def play(ctx, *, search: str):
    try:
        if ctx.author.voice is None:
            await ctx.send("You are not in a voice channel.")
            
        voice_channel = ctx.author.voice.channel
        if ctx.guild.id not in voice_clients or not voice_clients[ctx.guild.id].is_connected():
            voice_clients[ctx.guild.id] = await voice_channel.connect()

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search, download=False))
        song_info = data['entries'][0] if 'entries' in data else data
        song = {
            'title': song_info['title'],
            'url': song_info['url'],
            'webpage_url': song_info['webpage_url'],
            'duration': song_info['duration'],
            'search': search
        }

        if ctx.guild.id not in music_queue:
            music_queue[ctx.guild.id] = []

        if not voice_clients[ctx.guild.id].is_playing():
            songplayer = discord.FFmpegOpusAudio(song['url'], **ffmpeg)
            voice_clients[ctx.guild.id].play(songplayer, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
    
            current_song[ctx.guild.id] = song

            await ctx.send(f"The bot is now playing: **{song['title']}**")
        else:
            if any(song['webpage_url'] == queued_song['webpage_url'] for queued_song in music_queue[ctx.guild.id]):
                await ctx.send(f"This song is already in the queue.")
            else:
                music_queue[ctx.guild.id].append(song)   
                await ctx.send(f"Added the following to the queue: **{song['title']}**")
                
    except Exception as e:
        print(e)

@bot.command("pause")
async def pause(ctx):
    try:
        voice_clients[ctx.guild.id].pause()
        await ctx.send("Music is now paused.")
    except Exception as e:
        print(e)

@bot.command("resume")
async def resume(ctx):
    try:
        voice_clients[ctx.guild.id].resume()
        await ctx.send("Music is now resumed!")
    except Exception as e:
        print(e)

@bot.command("stop")
async def stop(ctx):
    try:
        voice_clients[ctx.guild.id].stop()
        await voice_clients[ctx.guild.id].disconnect()
        await ctx.send("*Music is now stopped, and the bot is disconnected.*")
        del voice_clients[ctx.guild.id]
    except Exception as e:
        print(e)

@bot.command(name="nonmethod")
async def queue(ctx, url):
    pass

@bot.command(name="clear")
async def clear(ctx):
    if ctx.guild.id in music_queue:
        music_queue[ctx.guild.id].clear()
        await ctx.send("The queue has been cleared.")
    else:
        await ctx.send("There is no queue to clear!")

@bot.command(name="skip") # This method is working improperly right now, fix later
async def skip(ctx):
    try:
        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
            voice_clients[ctx.guild.id].stop()
            await ctx.send("Skipped the current song.")
        else:
            await ctx.send("No song is currently playing.")

    except Exception as e:
        print(e)
        await ctx.send("An error occurred while trying to skip the song.")
        
@bot.command(name="queue")
async def show_queue(ctx):
    if ctx.guild.id in music_queue and music_queue[ctx.guild.id]:
        queue_embed = discord.Embed(title="Music Queue", description="Here are your currently queued songs in order:", color=discord.Color.blue())
        for i, song in enumerate(music_queue[ctx.guild.id], start=1):
            queue_embed.add_field(name=f"{i}. {song['title']}", value=song['webpage_url'], inline=False)
        await ctx.send(embed=queue_embed)
    else:
        await ctx.send("The queue is empty!")

@bot.command(name="shuffle")
async def shuffle_queue(ctx):
    if ctx.guild.id in music_queue and len(music_queue[ctx.guild.id]) > 1:
        random.shuffle(music_queue[ctx.guild.id])
        await ctx.send("**The queue has been shuffled.** Here is the shuffled queue:")
        await show_queue(ctx)
    else:
        await ctx.send("There aren't enough songs in the queue to shuffle it!")

@bot.command(name="current")
async def curr_song(ctx):
  try:
        if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
            curr_song = current_song[ctx.guild.id]
            curr_title = curr_song['title']
            updated_duration_secs = curr_song['duration'] % 60
            updated_duration_mins = curr_song['duration'] // 60
            await ctx.send(f"Currently playing: **{curr_title}** | Duration: {updated_duration_mins}m {updated_duration_secs}s")
        else:
            await ctx.send("There's no song currently playing.")
  except Exception as e:
        print(f"An error occurred while getting the current song that's playing: {e}")

@bot.command(name="remove")
async def remove_from_queue(ctx, index: int):
    try:
        if ctx.guild.id in music_queue and music_queue[ctx.guild.id]:
            if 1 <= index <= len(music_queue[ctx.guild.id]):
                removed_song = music_queue[ctx.guild.id].pop(index - 1)  
                await ctx.send(f"Removed the following song from the queue: **{removed_song['title']}**")
            else:
                await ctx.send("You've provided an invalid index, which is not in range of the queue.")
        else:
            await ctx.send("The queue is empty!")
    except Exception as e:
        await ctx.send("An error occurred while trying to remove this song from the queue.")

async def main():
    async with bot:
        await playlists_setup(bot)
        await bot.start(token)

asyncio.run(main())

 
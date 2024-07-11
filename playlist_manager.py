import json
import os
import asyncio
import random
import discord
from discord.ext import commands
from discord.ui import Button, View
import yt_dlp

yt_dl_options = {
    "format": "bestaudio/best",
    "default_search": "ytsearch1",
    'audioformat': 'mp3'
}

ytdl = yt_dlp.YoutubeDL(yt_dl_options)
playlist_file = "all_playlists.json"

def load_playlists():
    if os.path.exists(playlist_file):
        with open(playlist_file, "r") as f:
            return json.load(f)
    return {}

def save_playlists(playlists):
    with open(playlist_file, "w") as f:
        json.dump(playlists, f, indent = 4)

SONG_LIMIT_PER_PLAYLIST = 20
PLAYLIST_LIMIT_PER_USER = 10

class PlaylistManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.playlist_file = "all_playlists.json"
        self.user_playlists = load_playlists()
        self.curr_playlist = {}
        self.voice_clients = {}
        self.curr_song = {}


    def load_playlists(self):
        if os.path.exists(self.playlist_file):
            with open(self.playlist_file, "r") as f:
                self.user_playlists = json.load(f)
        else:
            self.user_playlists = {}


    def save_playlists(self):
        with open(self.playlist_file, "w") as f:
            json.dump(self.user_playlists, f, indent=4)    


    @commands.command(name="playlist_create")
    async def create_playlist(self, ctx, *, playlist_name: str):
        user_id = str(ctx.author.id)
        if user_id not in self.user_playlists:
            self.user_playlists[user_id] = {}
        if len(self.user_playlists[user_id]) >= PLAYLIST_LIMIT_PER_USER:
            await ctx.send(f"You've reached the maximum limit of 10 playlists. If you wish to free up playlist spots, consider using .playlist_remove <playlist name>.")
            return
        if playlist_name in self.user_playlists[user_id]:
            await ctx.send(f"You already have a playlist named **'{playlist_name}'**!")
        else:
            self.user_playlists[user_id][playlist_name] = {"songs": [], "public": False}
            await ctx.send(f"Created a new playlist called **{playlist_name}**.")
            self.save_playlists()


    @commands.command(name="playlist_add")
    async def add_to_playlist(self, ctx, *, args:str):
        user_id = str(ctx.author.id)
        if ',' not in args:
            await ctx.send("Please use the format: `.playlist_add <song name>, <playlist name>`")
            return

        search, playlist_name = map(str.strip, args.split(',', 1))

        if user_id not in self.user_playlists or playlist_name not in self.user_playlists[user_id]:
            await ctx.send(f"You do not currently have a playlist with the name **'{playlist_name}'**.")
        elif len(self.user_playlists[user_id][playlist_name]["songs"]) >= SONG_LIMIT_PER_PLAYLIST:
            await ctx.send(f"The playlist **'{playlist_name}'** has already reached its maximum song limit of 20 songs. If you wish to free up some space to add more preferable songs, consider using .remove_from_playlist <index> <playlist name>.")
        else:
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
            self.user_playlists[user_id][playlist_name]["songs"].append(song)
            await ctx.send(f"Successfully added **{song['title']}** to the playlist: **{playlist_name}**!")
            self.save_playlists()


    @commands.command(name="remove_from_playlist")
    async def remove_from_playlist(self, ctx, index: int, playlist_name: str):
        user_id = str(ctx.author.id)
        if user_id not in self.user_playlists or playlist_name not in self.user_playlists[user_id]:
            await ctx.send(f"You do not currently have a playlist with the name **'{playlist_name}'**.")
        elif 1 <= index <= len(self.user_playlists[user_id][playlist_name]["songs"]):
            removed_song = self.user_playlists[user_id][playlist_name]["songs"].pop(index - 1)
            await ctx.send(f"Succesfully removed **{removed_song['title']}** from the playlist: **{playlist_name}**!")
            self.save_playlists()
        else:
            await ctx.send(f"Invalid index. The playlist '{playlist_name}' has {len(self.user_playlists[user_id][playlist_name]['songs'])} songs.")


    @commands.command(name="playlists")
    async def show_playlists(self, ctx):
        user_id = str(ctx.author.id)
        if user_id in self.user_playlists and self.user_playlists[user_id]:
            playlists = self.user_playlists[user_id]
            embed = discord.Embed(title="Your Playlists", description="Here are your playlists:", color=discord.Color.blue())
            for playlist_name, data in playlists.items():
                embed.add_field(name=playlist_name, value=f"{len(data['songs'])} songs", inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("You don't have any playlists yet.")


    @commands.command(name="playlist_view")
    async def view_playlist(self, ctx, playlist_name: str):
        user_id = str(ctx.author.id)
        if user_id in self.user_playlists and playlist_name in self.user_playlists[user_id]:
            self.load_playlists()
            songs = self.user_playlists[user_id][playlist_name]["songs"]
            embed = discord.Embed(title=f"Playlist: {playlist_name}", description=f"{len(songs)} songs", color=discord.Color.red())
            for i, song in enumerate(songs, start=1):
                embed.add_field(name=f"{i}. {song['title']}", value=song['webpage_url'], inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"No playlist found with the name '{playlist_name}'.")


    @commands.command(name="playlist_play")
    async def play_playlist(self, ctx, *, playlist_name: str):
        user_id = str(ctx.author.id)
        if user_id not in self.user_playlists or playlist_name not in self.user_playlists[user_id]:
            await ctx.send(f"You do not currently have a playlist with the name **'{playlist_name}'**.")
            return
        
        vc = ctx.author.voice.channel
        if not vc:
            await ctx.send("You can't listen to your playlist if you aren't in a voice channel!")
            return

        songlist = self.user_playlists[user_id][playlist_name]["songs"]
        if not songlist:
            await ctx.send("The chosen playlist is empty!")
            return
        
        if ctx.voice_client is None:
            await vc.connect()

        self.curr_playlist[ctx.guild.id] = songlist.copy()

        def play_next_song():
            if self.curr_playlist[ctx.guild.id]:
                song = self.curr_playlist[ctx.guild.id].pop(0)
                self.curr_playlist[ctx.guild.id].append(song)
                ctx.voice_client.play(discord.FFmpegPCMAudio(song['url'], executable="ffmpeg"), after=lambda e: play_next_song())
                ctx.send(f"Now playing: **{song['title']}**")

        self.curr_playlist[ctx.guild.id] = songlist.copy()
        play_next_song()


    @commands.command(name="playlist_skip")
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():            
            ctx.voice_client.stop()
            await ctx.send("**Skipped to the next song in the playlist.**")
        else:
            await ctx.send("*No song is currently playing, or the bot is not connected to a voice channel.*")


    @commands.command(name="playlist_shuffle")
    async def shuffle_playlist(self, ctx, *, playlist_name:str):
        user_id = str(ctx.author.id)
        if user_id not in self.user_playlists or playlist_name not in self.user_playlists[user_id]:
            await ctx.send(f"You do not currently have a playlist with the name **'{playlist_name}'**.")
            return
        
        if len(self.user_playlists[user_id][playlist_name]["songs"]) > 1:
            random.shuffle(self.user_playlists[user_id][playlist_name]["songs"])
            await ctx.send(f"Your playlist **'{playlist_name}'** has been shuffled!")
            self.save_playlists()
        else:
            ctx.send(f"The playlist **'{playlist_name}'** has less than 2 songs, so it can't be shuffled!")


    @commands.command(name="delete_playlist")
    async def delete_playlist(self, ctx, *, playlist_name: str):
        user_id = str(ctx.author.id)
        if user_id not in self.user_playlists or playlist_name not in self.user_playlists[user_id]:
            await ctx.send(f"You do not currently have a playlist with the name **'{playlist_name}'**.")
            return
        
        embed = discord.Embed(title = f"Deleting Playlist **'{playlist_name}'** Confirmation", 
                              description=f"Are you *sure* you want to delete the playlist **'{playlist_name}'**?",
                              color = discord.Color.orange()
                              )
        embed.set_footer(text=f"React with sending 'yes' to confirm deletion or 'no' to cancel deletion.")

        msg = await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']

        try:
            confirmation = await self.bot.wait_for('message', timeout=30.0, check=check)
            if confirmation.content.lower() == 'yes':
                del self.user_playlists[user_id][playlist_name]
                self.save_playlists()
                await ctx.send(f"Playlist **'{playlist_name}'** has been successfully deleted.")
            else:
                await ctx.send("Deletion canceled.")
        except asyncio.TimeoutError:
            await ctx.send("Deletion timed out. Please try again if you wish to delete the playlist.")
       
    @commands.command(name="playlist_pause")
    async def pause_playlist(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Playback has been paused.")
        else:
            await ctx.send("There's no song currently playing to pause!")

    @commands.command(name="playlist_resume")
    async def resume_playlist(self, ctx):
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Playback has been resumed!")
        elif ctx.voice_client.is_playing():
            await ctx.send("The playback is already ongoing.")
        else:
            await ctx.send("There's no song that's currently paused to resume.")

    @commands.command(name="playlist_stop")
    async def stop_playlist(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            self.curr_playlist[ctx.guild.id] = []
            await ctx.send("*Any playlists have been stopped, and the bot has been disconnected from voice channel.*")
        else:
            await ctx.send("The bot is currently not in a voice channel!")

async def playlists_setup(bot):
    await bot.add_cog(PlaylistManager(bot))


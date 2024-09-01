import discord
import os
from discord.ext import commands
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

class SentimentCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.analyzer = SentimentIntensityAnalyzer()
        self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id, client_secret))

    @commands.command(name="recommend")
    async def generate_reccs(self, ctx):
        text = " "
        msg_counter = 0

        async for message in ctx.channel.history():
            if (message.author == ctx.author):
                text += message.content + " " # flattens all recent messages in the channel 
                msg_counter += 1
        
        avg_sent = self.analyzer.polarity_scores(text)['compound']
        avg_energy = self.analyze_energy(text, msg_counter)
        print(avg_sent, avg_energy)
    
        # Determines cutoff for sentiment
        if avg_sent >= 0.35:
            genre = 'happy'
        elif avg_sent <= -0.35:
            genre = 'sad'
        else:
            genre = 'chill'

        song_reccs = self.sp.recommendations(seed_genres=[genre], limit = 3, target_energy = avg_energy, target_valence = avg_sent) # This gets the recommendations using Spotify API and relevant parameters!

        if song_reccs['tracks']:
            embed = discord.Embed(
                title=f"Recommended {genre} Songs",
                description=f"So, based on your recent messages with an energy level of {avg_energy:.2f} and a sentiment value of {avg_sent:.2f}, these are the songs we recommend!",
                color=discord.Color.blue()
            )

            for track in song_reccs['tracks']:
                track_name = track['name']
                artist_name = track['artists'][0]['name']
                track_url = track['external_urls']['spotify']
                embed.add_field(
                    name=track_name,
                    value=f"Artist: {artist_name}\n[Listen on Spotify]({track_url})", # adds a link to listen to embedded song on Spotify for all recommended songs
                    inline=False
                )

            await ctx.send(embed=embed)
        else:
            await ctx.send("Sorry, no song recommendations could be found!")


    def analyze_energy(self, text, count):
        print(count)
        length_score_baseline = count/100.0 #finds out what proportion of scraped messages the user actually sent 
        length_score = len(text)/1000 * length_score_baseline # A longer average message length may indicate more energy
        sentiment = self.analyzer.polarity_scores(text)
        intensity_score = abs(sentiment['compound']) # A higher absolute sentiment marks higher energy
        exclamation_score = text.count('!') / 100 # Exclamation marks show a sign of vigor!
        return min((length_score + intensity_score)/2 + exclamation_score, 1.0) # Ensures score is capped at 1.0
        

async def setup(bot):
    await bot.add_cog(SentimentCog(bot))
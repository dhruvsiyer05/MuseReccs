import discord
from discord.ext import commands
import json

class PublicPlaylists(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.playlist_file = 'all_playlists.json'
    
    def load_playlists(self):
        with open(self.playlist_file, 'r') as f:
            return json.load(f)
    
    def save_playlists(self, playlists):
        with open(self.playlist_file, 'w') as f:
            json.dump(playlists, f, indent=4)
    
    @commands.command(name='viewother_plists')
    async def view_other_playlists(self, ctx, user: discord.User):
        """View public playlists of a specified user."""
        playlists = self.load_playlists()
        user_id = str(user.id)
        
        if user_id not in playlists:
            await ctx.send("This user has no playlists.")
            return
        
        public_playlists = {name: data for name, data in playlists[user_id].items() if data["public"]}
        
        if not public_playlists:
            await ctx.send("This user has no public playlists.")
            return
        
        embed = discord.Embed(title=f"{user.name}'s Public Playlists")
        
        for name, data in public_playlists.items():
            embed.add_field(name=name, value=f"{len(data['songs'])} songs", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='setprivacy')
    async def set_privacy(self, ctx, playlist_name: str, public: bool):
        """Set the privacy of a user's playlist."""
        playlists = self.load_playlists()
        user_id = str(ctx.author.id)
        
        if user_id not in playlists or playlist_name not in playlists[user_id]:
            await ctx.send("Playlist not found.")
            return
        
        playlists[user_id][playlist_name]["public"] = public
        self.save_playlists(playlists)
        
        await ctx.send(f"Playlist '{playlist_name}' privacy set to {'public' if public else 'private'}.")

async def viewing_setup(bot):
    await bot.add_cog(PublicPlaylists(bot))
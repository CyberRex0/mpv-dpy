import discord
from discord.ext import commands

from lib.audiosource import MPVSource

class PlayerUIView(discord.ui.View):

    def __init__(self, ctx: commands.Context, source: MPVSource):
        super().__init__()
        self.ctx: commands.Context = ctx
        self.source: MPVSource = source
        self.loop: bool = False
        self.bassboost: bool = False
        self.eq_param: str = 'equalizer=f=60:t=h:w=50:g=10'
    
    @discord.ui.button(label='<<')
    async def skip_back_2x(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.send_cmd('seek -15')
        await interaction.response.defer()
    
    @discord.ui.button(label='<')
    async def skip_back_1x(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.send_cmd('seek -5')
        await interaction.response.defer()
    
    @discord.ui.button(label='Play/Pause')
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.send_cmd('keypress space')
        await interaction.response.defer()
    
    @discord.ui.button(label='>')
    async def skip_forward_1x(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.send_cmd('seek 5')
        await interaction.response.defer()
    
    @discord.ui.button(label='>>')
    async def skip_forward_2x(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.send_cmd('seek 15')
        await interaction.response.defer()
    
    @discord.ui.button(label='Stop', style=discord.ButtonStyle.red)
    async def stop_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.send_cmd('quit')
        await interaction.response.edit_message(content='[Player has stopped]', view=None)
        self.stop()
    
    @discord.ui.button(label='Vol +')
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.set_volume(self.source.get_volume() + 10240)
        await interaction.response.defer()
    
    @discord.ui.button(label='Vol -')
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.set_volume(self.source.get_volume() - 10240)
        await interaction.response.defer()
    
    @discord.ui.button(label='Spd -')
    async def speed_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.send_cmd('keypress {')
        await interaction.response.defer()
    
    @discord.ui.button(label='Spd +')
    async def speed_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.send_cmd('keypress }')
        await interaction.response.defer()
    
    @discord.ui.button(label='Loop: off')
    async def loop_switch(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.loop = not self.loop
        self.source.send_cmd('set loop-file inf' if self.loop else 'set loop-file no')
        self.loop_switch.label = 'Loop: '+ ('on' if self.loop else 'off')
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label='Bass Boost: off')
    async def bassboost_switch(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bassboost = not self.bassboost
        self.source.send_cmd('af set ' + self.eq_param if self.bassboost else 'af remove ' + self.eq_param)
        self.bassboost_switch.label = 'Bass Boost: '+ ('on' if self.bassboost else 'off')
        await interaction.response.edit_message(view=self)


class VoiceCog(commands.Cog):

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.source: MPVSource = None
    
    @commands.group()
    async def vc(self, ctx: commands.Context):
        pass
    
    @vc.command(name='con')
    async def vc_join(self, ctx: commands.Context):
        await ctx.author.voice.channel.connect()
        await ctx.reply('Connected', mention_author=False)
    
    @vc.command(name='dc')
    async def vc_disconnect(self, ctx: commands.Context):
        await ctx.guild.voice_client.disconnect(force=True)
        await ctx.reply('Disconnected', mention_author=False)
    
    @vc.command(name='stop')
    async def vc_stop(self, ctx: commands.Context):
        if not ctx.guild.voice_client:
            await ctx.reply('Not Connected', mention_author=False)
            return
        
        ctx.guild.voice_client.stop()
    
    @vc.command(name='seek')
    async def vc_seek(self, ctx: commands.Context, sec: int):
        if not ctx.guild.voice_client:
            await ctx.reply('Not Connected', mention_author=False)
            return
        
        self.source.send_cmd(f'seek {sec}')
    
    @vc.command(name='ui')
    async def vc_ui(self, ctx: commands.Context):
        if not ctx.guild.voice_client:
            await ctx.reply('Not Connected', mention_author=False)
            return
        
        await ctx.send(view=PlayerUIView(ctx, ctx.guild.voice_client.source))
    
    @vc.command(name='play')
    async def vc_testplay(self, ctx: commands.Context, path: str):
        if not ctx.guild.voice_client:
            await ctx.reply('Not Connected', mention_author=False)
            return
        
        source = MPVSource(source=path, opus_bitrate=284)
        ctx.guild.voice_client.play(source)
    
    @vc.command(name='cmd')
    async def vc_mpvcmd(self, ctx: commands.Context, cmd: str):
        if not ctx.guild.voice_client:
            await ctx.reply('Not Connected', mention_author=False)
            return
        
        self.source.send_cmd(cmd)

async def setup(bot):
    await bot.add_cog(VoiceCog(bot))

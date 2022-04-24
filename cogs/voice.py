import discord
from discord.ext import commands

from typing import Union
from discord.opus import Encoder as OpusEncoder
import io
import subprocess
import uuid
import socket
class PAConnectException(Exception):
    pass
class PADeviceRegisterException(Exception):
    pass
class PARecordReadException(Exception):
    pass

class MPVSource(discord.AudioSource):

    def __init__(self, source: Union[str, io.BufferedIOBase], opus_bitrate: int = 128, executable_path:str = '/usr/bin/mpv'):
        self.source = source
        self.pa_sink_name = f'discord-{uuid.uuid4()}'
        self._pa_sink_volume: int = 65535

        try:
            ret, module_id, _null = self._run_shell(['pactl', 'load-module', 'module-null-sink', 'sink_name=' + self.pa_sink_name])
        except:
            raise PADeviceRegisterException('Failed to register virtual device')
        
        if ret != 0:
            raise PADeviceRegisterException('Failed to register virtual device')
        
        self._pa_module_id:int = int(module_id.decode())

        self._ipc_sock_path = '/tmp/dpy_mpv_' + str(uuid.uuid4()) + '.sock'
        self._mpv_args = [executable_path,
            '--msg-level=all=error',
            '--no-cache',
            '--no-cache-pause',
            '--demuxer-readahead-secs=0',
            '--no-video',
            '--no-audio-display',
            '--input-ipc-server=' + self._ipc_sock_path,
            '--ao=pulse',
            f'--audio-device=pulse/{self.pa_sink_name}',
            '--audio-format=s16',
            '--audio-samplerate=48000',
            '--audio-channels=stereo',
            source
        ]
        self._parecord_args = ['/usr/bin/parecord',
            '-r',
            '--raw',
            '--rate=48000',
            '--channels=2',
            '--format=s16le',
            f'--device={self.pa_sink_name}.monitor'
        ]
        self._frame_read_count: int = 0
        self._mpv_process = None
        self._parecord_process = None
        self._start_process()

        # Opus Encoder
        self._opus_encoder = OpusEncoder()
        self._opus_encoder.set_bitrate(opus_bitrate)
        self._is_opus = True
    
    def _run_shell(self, args: list):
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        return p.returncode, out, err
    
    def _start_process(self):
        self._mpv_process = subprocess.Popen(self._mpv_args, stdout=subprocess.PIPE)
        self._parecord_process = subprocess.Popen(self._parecord_args, stdout=subprocess.PIPE)

    def read(self) -> bytes:
        self._frame_read_count += 1
        if self._mpv_process.poll() is not None:
            print('MPVSource/read: mpv process exited with code {}'.format(self._mpv_process.returncode))
            return b''
        if self._parecord_process.poll() is not None:
            print('MPVSource/read: parecord process exited with code {}'.format(self._parecord_process.returncode))
            return b''
        # print(f'MPVSource/read: reading frame {self._frame_read_count} (size={OpusEncoder.FRAME_SIZE})')

        frame = self._parecord_process.stdout.read(OpusEncoder.FRAME_SIZE)
        
        if len(frame) != OpusEncoder.FRAME_SIZE:
            return b''
        
        encoded_bytes = self._opus_encoder.encode(frame, OpusEncoder.SAMPLES_PER_FRAME)

        return encoded_bytes
    
    def send_cmd(self, cmd: str):
        _ipc = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        _ipc.connect(self._ipc_sock_path)
        _ipc.send((cmd + '\n').encode())
        _ipc.close()
    
    def set_volume(self, volume: int):
        self._pa_sink_volume = volume
        if self._pa_sink_volume < 0:
            self._pa_sink_volume = 0
        elif self._pa_sink_volume > 65535:
            self._pa_sink_volume = 65535
        self._run_shell(['pactl', 'set-sink-volume', self.pa_sink_name, str(volume)])
    
    def get_volume(self):
        return self._pa_sink_volume
    
    def cleanup(self):
        print('MPVSource/cleanup: cleaning up MPV, parecord, OpusEncoder and virtual device')
        del self._opus_encoder
        self._mpv_process.kill()
        self._parecord_process.kill()
        self._run_shell(['pactl', 'unload-module', str(self._pa_module_id)])
    
    def is_opus(self):
        return self._is_opus

class PlayerUIView(discord.ui.View):

    def __init__(self, ctx: commands.Context, source: MPVSource):
        super().__init__()
        self.ctx: commands.Context = ctx
        self.source: MPVSource = source
    
    @discord.ui.button(label='⏪')
    async def skip_back_2x(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.send_cmd('seek -15')
        await interaction.response.defer()
    
    @discord.ui.button(label='◀️')
    async def skip_back_1x(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.send_cmd('seek -5')
        await interaction.response.defer()
    
    @discord.ui.button(label='Play/Pause')
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.send_cmd('keypress space')
        await interaction.response.defer()
    
    @discord.ui.button(label='▶️')
    async def skip_forward_1x(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.send_cmd('seek 5')
        await interaction.response.defer()
    
    @discord.ui.button(label='⏩')
    async def skip_forward_2x(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.source.send_cmd('seek 15')
        await interaction.response.defer()
    
    @discord.ui.button(label='⏹', style=discord.ButtonStyle.red)
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
        
        await ctx.send(view=PlayerUIView(ctx, self.source))
    
    @vc.command(name='play')
    async def vc_testplay(self, ctx: commands.Context, path: str):
        if not ctx.guild.voice_client:
            await ctx.reply('Not Connected', mention_author=False)
            return
        
        print('Preparing to play...')
        self.source = MPVSource(path)
        print('Playing...')
        ctx.guild.voice_client.play(self.source)
    
    @vc.command(name='cmd')
    async def vc_mpvcmd(self, ctx: commands.Context, cmd: str):
        if not ctx.guild.voice_client:
            await ctx.reply('Not Connected', mention_author=False)
            return
        
        self.source.send_cmd(cmd)

async def setup(bot):
    await bot.add_cog(VoiceCog(bot))

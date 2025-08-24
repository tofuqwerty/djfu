import discord
from discord.ext import commands
import yt_dlp
import shutil
import sys
import asyncio
import os
from collections import deque
import imageio_ffmpeg  # Optional untuk memastikan ffmpeg tersedia

# Cari path ffmpeg
FFMPEG_PATH = shutil.which("ffmpeg")
if FFMPEG_PATH is None:
    if sys.platform.startswith("win"):
        FFMPEG_PATH = "C:\\ffmpeg\\bin\\ffmpeg.exe"
    else:
        FFMPEG_PATH = "/usr/bin/ffmpeg"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="&", intents=intents)

# yt-dlp config
ytdl_opts = {
    'format': 'bestaudio/best',
    'default_search': 'ytsearch1',
    'cookiefile': 'cookies.txt',  # opsional
}
ytdl = yt_dlp.YoutubeDL(ytdl_opts)

song_queue = deque()

def get_audio(query):
    """Cari lagu di YouTube dan kembalikan URL audio + judul"""
    try:
        info = ytdl.extract_info(query, download=False)
        if "entries" in info:
            return info['entries'][0]['url'], info['entries'][0]['title']
        return info['url'], info['title']
    except Exception as e:
        print(f"Error mendapatkan audio: {e}")
        return None, None

# ----------------- Voice Helper -----------------
async def safe_join(ctx, retries=5, delay=2):
    """Join voice channel dengan retry"""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        for attempt in range(retries):
            try:
                if ctx.voice_client is None:
                    await channel.connect()
                await ctx.send(f"✅ Bot bergabung ke **{channel.name}**")
                return True
            except Exception as e:
                print(f"Retry join voice {attempt+1}/{retries} gagal: {e}")
                await asyncio.sleep(delay)
        await ctx.send("❌ Bot gagal join voice channel setelah beberapa percobaan.")
    else:
        await ctx.send("❌ Kamu harus berada di voice channel dulu!")
    return False

# ----------------- Bot Events -----------------
@bot.event
async def on_ready():
    print(f"{bot.user} sudah online!")
    await asyncio.sleep(2)  # Delay kecil biar bot siap

# ----------------- Bot Commands -----------------
@bot.command()
async def join(ctx):
    await safe_join(ctx)

@bot.command()
async def queue(ctx):
    if not song_queue:
        await ctx.send("📭 Antrean kosong!")
    else:
        queue_list = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(song_queue)])
        await ctx.send(f"📜 **Daftar Lagu:**\n{queue_list}")

@bot.command()
async def play(ctx, *, query):
    url, title = get_audio(query)
    if not url:
        await ctx.send("❌ Tidak dapat menemukan lagu!")
        return

    song_queue.append((url, title))

    if ctx.voice_client is None:
        success = await safe_join(ctx)
        if not success:
            return

    voice_client = ctx.voice_client
    print(f"Memutar lagu: {title}, URL: {url}")

    if not voice_client.is_playing():
        await play_next(ctx)
    else:
        await ctx.send(f"🎶 Lagu **{title}** ditambahkan ke antrean!")

async def play_next(ctx):
    """Mainkan lagu berikutnya dari antrean"""
    if song_queue:
        url, title = song_queue.popleft()
        with yt_dlp.YoutubeDL({'format': 'bestaudio'}) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info['url']

        voice_client = ctx.voice_client
        if voice_client:
            source = discord.FFmpegPCMAudio(stream_url, executable=FFMPEG_PATH)
            voice_client.play(
                source,
                after=lambda e: print(f"Error saat play: {e}") or bot.loop.create_task(play_next(ctx))
            )
            await ctx.send(f"🎵 Sedang Memutar: **{title}**")
    else:
        await ctx.send("📭 Semua lagu selesai. Bot akan keluar otomatis dalam 5 menit jika tidak ada aktivitas.")
        bot.loop.create_task(auto_disconnect(ctx))

async def auto_disconnect(ctx):
    """Disconnect otomatis setelah 5 menit jika tidak ada aktivitas"""
    await asyncio.sleep(300)
    if not song_queue and ctx.voice_client and not ctx.voice_client.is_playing():
        if len(ctx.voice_client.channel.members) <= 1:
            await ctx.voice_client.disconnect()
            await ctx.send("Tidak ada aktivitas, bot keluar otomatis.")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Lagu dilewati, memutar lagu selanjutnya...")
        await play_next(ctx)
    else:
        await ctx.send("❌ Tidak ada lagu yang sedang diputar.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        song_queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send("🛑 Bot keluar dari voice channel dan antrean dihapus.")
    else:
        await ctx.send("❌ Bot tidak berada di voice channel.")

# ----------------- Jalankan Bot -----------------
bot.run(os.environ['DISCORD_TOKEN'])

import discord
from discord.ext import commands
import yt_dlp  # Menggunakan yt-dlp
import shutil
import sys
import asyncio
import os
from collections import deque  # Untuk antrean lagu

import imageio_ffmpeg  # Optional, untuk memastikan ffmpeg

# Cari ffmpeg secara otomatis
FFMPEG_PATH = shutil.which("ffmpeg")
if FFMPEG_PATH is None:
    if sys.platform.startswith("win"):
        # Pastikan path berikut sesuai dengan instalasi ffmpeg di Windows kamu
        FFMPEG_PATH = "C:\\ffmpeg\\bin\\ffmpeg.exe"
    else:
        FFMPEG_PATH = "/usr/bin/ffmpeg"  # Fallback untuk Linux

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="&", intents=intents)

# Konfigurasi yt-dlp untuk mendapatkan URL audio
ytdl_opts = {
    'format': 'bestaudio/best',
    'default_search': 'ytsearch1',
    'cookiefile': 'cookies.txt',  # Opsional jika kamu menggunakan cookies
}
ytdl = yt_dlp.YoutubeDL(ytdl_opts)

song_queue = deque()  # Antrean lagu

def get_audio(query):
    """Mencari lagu di YouTube dan mengembalikan URL audio & judul lagu."""
    try:
        info = ytdl.extract_info(query, download=False)  # Hanya ambil info tanpa download
        if "entries" in info:
            return info['entries'][0]['url'], info['entries'][0]['title']
        return info['url'], info['title']
    except Exception as e:
        print(f"Error mendapatkan audio: {e}")
        return None, None

@bot.command()
async def join(ctx):
    """Bot bergabung ke voice channel pengguna."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            await channel.connect()
            await ctx.send(f"✅ Bot bergabung ke **{channel.name}**")
        else:
            await ctx.send("⚠️ Bot sudah berada di voice channel!")
    else:
        await ctx.send("❌ Kamu harus berada di voice channel dulu!")

@bot.command()
async def queue(ctx):
    """Menampilkan antrean lagu."""
    if not song_queue:
        await ctx.send("📭 Antrean kosong!")
    else:
        queue_list = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(song_queue)])
        await ctx.send(f"📜 **Daftar Lagu:**\n{queue_list}")

@bot.command()
async def play(ctx, *, query):
    """Memutar lagu atau menambahkannya ke antrean."""
    url, title = get_audio(query)
    if not url:
        await ctx.send("❌ Tidak dapat menemukan lagu!")
        return

    song_queue.append((url, title))

    if ctx.voice_client is None:
        await ctx.invoke(join)

    voice_client = ctx.voice_client
    print(f"Memutar lagu: {title}, URL: {url}")  # Debugging

    if not voice_client.is_playing():
        await play_next(ctx)
    else:
        await ctx.send(f"🎶 Lagu **{title}** ditambahkan ke antrean!")

async def play_next(ctx):
    """Memainkan lagu berikutnya dari antrean."""
    if song_queue:
        url, title = song_queue.popleft()
        # Menggunakan yt-dlp untuk mendapatkan URL streaming
        with yt_dlp.YoutubeDL({'format': 'bestaudio'}) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info['url']

        voice_client = ctx.voice_client
        if voice_client:
            source = discord.FFmpegPCMAudio(stream_url, executable=FFMPEG_PATH)
            voice_client.play(source, after=lambda e: bot.loop.create_task(play_next(ctx)))
            await ctx.send(f"🎵 Sedang Memutar: **{title}**")
    else:
        await ctx.send("📭 Semua lagu telah selesai. Bot akan keluar otomatis dalam 5 menit jika tidak ada aktivitas.")
        # Buat task untuk auto-disconnect setelah 5 menit jika tidak ada aktivitas
        bot.loop.create_task(auto_disconnect(ctx))

async def auto_disconnect(ctx):
    """Menunggu 5 menit, lalu disconnect jika tidak ada aktivitas."""
    await asyncio.sleep(300)  # Tunggu 5 menit (300 detik)
    # Jika antrean masih kosong, bot tidak sedang memutar, dan bot sendirian di voice channel:
    if not song_queue and ctx.voice_client and not ctx.voice_client.is_playing():
        if len(ctx.voice_client.channel.members) <= 1:
            await ctx.voice_client.disconnect()
            await ctx.send("Tidak ada aktivitas, bot keluar otomatis.")

@bot.command()
async def skip(ctx):
    """Skip lagu saat ini dan lanjut ke antrean berikutnya."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Lagu dilewati, memutar lagu selanjutnya...")
        await play_next(ctx)
    else:
        await ctx.send("❌ Tidak ada lagu yang sedang diputar.")

@bot.command()
async def stop(ctx):
    """Menghentikan musik dan menghapus antrean."""
    if ctx.voice_client:
        song_queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send("🛑 Bot keluar dari voice channel dan antrean dihapus.")
    else:
        await ctx.send("❌ Bot tidak berada di voice channel.")

bot.run(os.environ['DISCORD_TOKEN'])
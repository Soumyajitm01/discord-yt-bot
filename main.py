import os
import json
import asyncio
import feedparser
import aiohttp
import discord
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread

# Load environment variables from Replit's Secrets tab
DISCORD_TOKEN     = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
YT_CHANNEL_ID     = os.getenv("YT_CHANNEL_ID")

# RSS feed URL for the YouTube channel
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={YT_CHANNEL_ID}"
STATE_FILE = "last_video.json"

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Flask web server for UptimeRobot ping
app = Flask('')

@app.route('/')
def home():
    return "YouTube Discord Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# Store/load last announced video
def load_last_video():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f).get("last_video")
    return None

def save_last_video(video_id):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_video": video_id}, f)

# Task: Check the RSS feed every 5 minutes
@tasks.loop(minutes=5.0)
async def check_feed():
    last_video = load_last_video()
    async with aiohttp.ClientSession() as session:
        async with session.get(RSS_URL) as resp:
            raw = await resp.text()
    feed = feedparser.parse(raw)

    if not feed.entries:
        return

    latest = feed.entries[0]
    video_url = latest.link
    video_id  = latest.yt_videoid

    if video_id != last_video:
        # Optional: Only alert if it's a Short
        # if "/shorts/" not in video_url:
        #     return

        channel = bot.get_channel(DISCORD_CHANNEL_ID)
        if channel is None:
            print("Discord channel not found.")
            return

        embed = discord.Embed(
            title=f"🎬 {latest.title}",
            url=video_url,
            description=f"New video posted by **{latest.author}**!",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=latest.media_thumbnail[0]["url"])
        embed.set_footer(text="YouTube Watcher Bot")

        await channel.send(embed=embed)
        save_last_video(video_id)
        print(f"New video announced: {video_url}")

# When the bot is ready
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    if not check_feed.is_running():
        check_feed.start()

# Start the web server and run the bot
keep_alive()
bot.run(DISCORD_TOKEN)

import discord
import os
from discord.ext import commands
from deep_translator import GoogleTranslator

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

FLAG_LANG = {
    "🇲🇽": "es",
    "🇺🇸": "en",
    "🇧🇷": "pt"
}

@bot.event
async def on_ready():
    print(f"✅ Conectado como {bot.user}")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    emoji = str(payload.emoji)
    if emoji not in FLAG_LANG:
        return

    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except:
        return

    if message.author.bot or not message.content:
        return

    target_lang = FLAG_LANG[emoji]

    try:
        translated = GoogleTranslator(
            source="auto",
            target=target_lang
        ).translate(message.content)

        if translated.lower() != message.content.lower():
            await message.reply(f"{emoji} **{translated}**")

    except Exception as e:
        print("❌ Error traduciendo:", e)

bot.run(TOKEN)
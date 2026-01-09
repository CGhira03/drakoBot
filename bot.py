import discord
import os
from deep_translator import GoogleTranslator

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True

client = discord.Client(intents=intents)

FLAG_LANG = {
    "🇪🇸": "es",
    "🇲🇽": "es",
    "🇺🇸": "en",
    "🇬🇧": "en",
    "🇧🇷": "pt"
}

@client.event
async def on_ready():
    print(f"Conectado como {client.user}")

@client.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    emoji = str(reaction.emoji)
    if emoji not in FLAG_LANG:
        return

    message = reaction.message
    if message.author.bot or not message.content:
        return

    target_lang = FLAG_LANG[emoji]

    try:
        translated = GoogleTranslator(
            source="auto",
            target=target_lang
        ).translate(message.content)

        if translated and translated.lower() != message.content.lower():
            await message.reply(f"{emoji} **{translated}**")

    except Exception as e:
        print("Error al traducir:", e)

client.run(TOKEN)

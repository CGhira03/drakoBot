import logging
import os

import discord
from discord.ext import commands
from deep_translator import GoogleTranslator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("discord-translator")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit("❌ Falta la variable de entorno DISCORD_TOKEN")

MAX_REPLY_LENGTH = 1900  # margen por debajo del límite de 2000 de Discord
MAX_CACHE_SIZE = 5000    # evita que la cache crezca sin límite en procesos de larga duración

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

FLAG_LANG = {
    # Español
    "🇲🇽": "es",  # México
    "🇦🇷": "es",  # Argentina
    "🇪🇸": "es",  # España

    # Inglés
    "🇺🇸": "en",  # USA
    "🇨🇦": "en",  # Canadá (inglés)

    # Portugués
    "🇧🇷": "pt",  # Brasil

    # Francés
    "🇫🇷": "fr",  # Francia

    # Alemán
    "🇩🇪": "de",  # Alemania

    # Ruso
    "🇷🇺": "ru",  # Rusia

    # Italiano
    "🇮🇹": "it",  # Italia

    # Japonés
    "🇯🇵": "ja",  # Japón

    # Coreano
    "🇰🇷": "ko",  # Corea del Sur

    # Chino
    "🇨🇳": "zh-CN",  # China

    # Turco
    "🇹🇷": "tr",  # Turquía

    # Árabe
    "🇸🇦": "ar",  # Arabia Saudita

    # Polaco
    "🇵🇱": "pl",  # Polonia

    # Neerlandés
    "🇳🇱": "nl",  # Países Bajos
}

# Evita traducir de nuevo el mismo mensaje al mismo idioma si varias
# personas reaccionan con la misma bandera. Se resetea en cada reinicio
# del proceso; el tope evita que crezca sin límite mientras el bot sigue vivo.
_translated_cache = set()


@bot.event
async def on_ready():
    logger.info("✅ Conectado como %s", bot.user)


@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    emoji = str(payload.emoji)
    target_lang = FLAG_LANG.get(emoji)
    if target_lang is None:
        return

    cache_key = (payload.message_id, target_lang)
    if cache_key in _translated_cache:
        return

    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
        logger.warning("No se pudo obtener el mensaje %s: %s", payload.message_id, e)
        return

    if message.author.bot or not message.content:
        return

    try:
        translated = GoogleTranslator(source="auto", target=target_lang).translate(message.content)
    except Exception as e:
        logger.error("Error traduciendo mensaje %s: %s", payload.message_id, e)
        return

    if not translated or translated.lower() == message.content.lower():
        return

    if len(translated) > MAX_REPLY_LENGTH:
        translated = translated[:MAX_REPLY_LENGTH - 1] + "…"

    if len(_translated_cache) >= MAX_CACHE_SIZE:
        _translated_cache.clear()
    _translated_cache.add(cache_key)

    try:
        await message.reply(f"{emoji} **{translated}**")
    except discord.HTTPException as e:
        logger.error("Error enviando la traducción de %s: %s", payload.message_id, e)


bot.run(TOKEN, log_handler=None)

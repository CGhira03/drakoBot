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
    "🇦🇷": "es",  # Argentina
    "🇲🇽": "es",  # México
    "🇪🇸": "es",  # España
    "🇪🇦": "es", # Ceuta y Melilla
    "🇮🇨": "es", # Islas Canarias
    "🇧🇴": "es",  # Bolivia
    "🇨🇱": "es",  # Chile
    "🇨🇴": "es",  # Colombia
    "🇨🇷": "es",  # Costa Rica
    "🇨🇺": "es",  # Cuba
    "🇩🇴": "es",  # Rep. Dominicana
    "🇪🇨": "es",  # Ecuador
    "🇸🇻": "es",  # El Salvador
    "🇬🇹": "es",  # Guatemala
    "🇭🇳": "es",  # Honduras
    "🇳🇮": "es",  # Nicaragua
    "🇵🇦": "es",  # Panamá
    "🇵🇾": "es",  # Paraguay
    "🇵🇪": "es",  # Perú
    "🇵🇷": "es",  # Puerto Rico
    "🇺🇾": "es",  # Uruguay
    "🇻🇪": "es",  # Venezuela
    "🇬🇶": "es",  # Guinea Ecuatorial

    # Inglés
    "🇺🇸": "en",  # USA
    "UM": "en",  # USA
    "🇨🇦": "en",  # Canadá
    "🇬🇧": "en",  # Reino Unido
    "🇮🇪": "en",  # Irlanda
    "🇦🇺": "en",  # Australia
    "🇳🇿": "en",  # Nueva Zelanda
    "🇿🇦": "en",  # Sudáfrica*
    "🇯🇲": "en",  # Jamaica
    "🇹🇹": "en",  # Trinidad y Tobago
    "🇧🇸": "en",  # Bahamas
    "🇧🇧": "en",  # Barbados
    "🇧🇿": "en",  # Belice
    "🇬🇾": "en",  # Guyana
    "🇦🇬": "en",  # Antigua y Barbuda
    "🇩🇲": "en",  # Dominica
    "🇬🇩": "en",  # Granada
    "🇰🇳": "en",  # San Cristóbal y Nieves
    "🇱🇨": "en",  # Santa Lucía
    "🇻🇨": "en",  # San Vicente y las Granadinas
    "🇳🇬": "en",  # Nigeria
    "🇬🇭": "en",  # Ghana
    "🇸🇱": "en",  # Sierra Leona
    "🇱🇷": "en",  # Liberia
    "🇬🇲": "en",  # Gambia
    "🇳🇦": "en",  # Namibia
    "🇧🇼": "en",  # Botsuana
    "🇿🇲": "en",  # Zambia
    "🇸🇸": "en",  # Sudán del Sur
    "🇸🇿": "en",  # Esuatini
    "🇸🇬": "en",  # Singapur
    "🇵🇬": "en",  # Papúa Nueva Guinea
    "🇫🇯": "en",  # Fiyi
    "🇹🇴": "en",  # Tonga
    "🇻🇺": "en",  # Vanuatu
    "🇸🇧": "en",  # Islas Salomón
    "🇰🇮": "en",  # Kiribati
    "🇹🇻": "en",  # Tuvalu
    "🇳🇷": "en",  # Nauru
    "🇵🇼": "en",  # Palaos
    "🇫🇲": "en",  # Micronesia
    "🇲🇭": "en",  # Islas Marshall

    # Portugués
    "🇧🇷": "pt",  # Brasil
    "🇵🇹": "pt",  # Portugal
    "🇦🇴": "pt",  # Angola
    "🇲🇿": "pt",  # Mozambique
    "🇨🇻": "pt",  # Cabo Verde
    "🇬🇼": "pt",  # Guinea-Bisáu
    "🇸🇹": "pt",  # Santo Tomé y Príncipe
    "🇹🇱": "pt",  # Timor Oriental

    # Francés
    "🇫🇷": "fr",  # Francia
    "🇧🇪": "fr",  # Bélgica*
    "🇲🇨": "fr",  # Mónaco
    "🇨🇩": "fr",  # R.D. Congo
    "🇨🇬": "fr",  # Congo
    "🇨🇮": "fr",  # Costa de Marfil
    "🇸🇳": "fr",  # Senegal
    "🇲🇱": "fr",  # Malí
    "🇨🇲": "fr",  # Camerún*
    "🇬🇦": "fr",  # Gabón
    "🇹🇩": "fr",  # Chad*
    "🇨🇫": "fr",  # Rep. Centroafricana
    "🇳🇪": "fr",  # Níger
    "🇧🇫": "fr",  # Burkina Faso
    "🇹🇬": "fr",  # Togo
    "🇧🇯": "fr",  # Benín
    "🇬🇳": "fr",  # Guinea
    "🇲🇺": "fr",  # Mauricio*
    "🇸🇨": "fr",  # Seychelles
    "🇰🇲": "fr",  # Comoras*
    "🇧🇮": "fr",  # Burundi*

    # Alemán
    "🇩🇪": "de",  # Alemania
    "🇦🇹": "de",  # Austria
    "🇱🇮": "de",  # Liechtenstein
    "🇨🇭": "de",  # Suiza*

    # Ruso
    "🇷🇺": "ru",  # Rusia

    # Italiano
    "🇮🇹": "it",  # Italia
    "🇸🇲": "it",  # San Marino
    "🇻🇦": "it",  # Vaticano

    # Japonés
    "🇯🇵": "ja",  # Japón

    # Coreano
    "🇰🇷": "ko",  # Corea del Sur
    "🇰🇵": "ko",  # Corea del Norte

    # Chino simplificado
    "🇨🇳": "zh-CN",  # China

    # Chino tradicional
    "🇹🇼": "zh-TW",  # Taiwán
    "🇭🇰": "zh-TW",  # Hong Kong
    "🇲🇴": "zh-TW",  # Macao

    # Turco
    "🇹🇷": "tr",  # Turquía

    # Árabe
    "🇸🇦": "ar",  # Arabia Saudita
    "🇪🇬": "ar",  # Egipto
    "🇦🇪": "ar",  # Emiratos Árabes
    "🇶🇦": "ar",  # Qatar
    "🇰🇼": "ar",  # Kuwait
    "🇧🇭": "ar",  # Baréin
    "🇴🇲": "ar",  # Omán
    "🇯🇴": "ar",  # Jordania
    "🇱🇧": "ar",  # Líbano
    "🇸🇾": "ar",  # Siria
    "🇮🇶": "ar",  # Irak
    "🇾🇪": "ar",  # Yemen
    "🇱🇾": "ar",  # Libia
    "🇹🇳": "ar",  # Túnez
    "🇩🇿": "ar",  # Argelia
    "🇲🇦": "ar",  # Marruecos
    "🇸🇩": "ar",  # Sudán
    "🇲🇷": "ar",  # Mauritania
    "🇵🇸": "ar",  # Palestina
    "🇩🇯": "ar",  # Yibuti*

    # Polaco
    "🇵🇱": "pl",  # Polonia

    # Neerlandés
    "🇳🇱": "nl",  # Países Bajos
    "🇸🇷": "nl",  # Surinam

    # Hebreo
    "🇮🇱": "iw",  # Israel

    # Persa
    "🇮🇷": "fa",  # Irán
    "🇦🇫": "fa",  # Afganistán*

    # Griego
    "🇬🇷": "el",  # Grecia
    "🇨🇾": "el",  # Chipre*

    # Ucraniano
    "🇺🇦": "uk",  # Ucrania

    # Bielorruso
    "🇧🇾": "be",  # Bielorrusia*

    # Checo
    "🇨🇿": "cs",  # Rep. Checa

    # Eslovaco
    "🇸🇰": "sk",  # Eslovaquia

    # Húngaro
    "🇭🇺": "hu",  # Hungría

    # Rumano
    "🇷🇴": "ro",  # Rumania
    "🇲🇩": "ro",  # Moldavia

    # Búlgaro
    "🇧🇬": "bg",  # Bulgaria

    # Albanés
    "🇦🇱": "sq",  # Albania
    "🇽🇰": "sq",  # Kosovo*

    # Macedonio
    "🇲🇰": "mk",  # Macedonia del Norte

    # Serbio
    "🇷🇸": "sr",  # Serbia
    "🇲🇪": "sr",  # Montenegro*

    # Croata
    "🇭🇷": "hr",  # Croacia

    # Bosnio
    "🇧🇦": "bs",  # Bosnia y Herzegovina

    # Esloveno
    "🇸🇮": "sl",  # Eslovenia

    # Lituano
    "🇱🇹": "lt",  # Lituania

    # Letón
    "🇱🇻": "lv",  # Letonia

    # Estonio
    "🇪🇪": "et",  # Estonia

    # Finlandés
    "🇫🇮": "fi",  # Finlandia

    # Sueco
    "🇸🇪": "sv",  # Suecia

    # Noruego
    "🇳🇴": "no",  # Noruega

    # Danés
    "🇩🇰": "da",  # Dinamarca

    # Islandés
    "🇮🇸": "is",  # Islandia

    # Maltés
    "🇲🇹": "mt",  # Malta

    # Luxemburgués
    "🇱🇺": "lb",  # Luxemburgo

    # Catalán
    "🇦🇩": "ca",  # Andorra

    # Georgiano
    "🇬🇪": "ka",  # Georgia

    # Armenio
    "🇦🇲": "hy",  # Armenia

    # Azerbaiyano
    "🇦🇿": "az",  # Azerbaiyán

    # Kazajo
    "🇰🇿": "kk",  # Kazajistán

    # Uzbeko
    "🇺🇿": "uz",  # Uzbekistán

    # Turcomano
    "🇹🇲": "tk",  # Turkmenistán

    # Kirguís
    "🇰🇬": "ky",  # Kirguistán

    # Tayiko
    "🇹🇯": "tg",  # Tayikistán

    # Mongol
    "🇲🇳": "mn",  # Mongolia

    # Vietnamita
    "🇻🇳": "vi",  # Vietnam

    # Tailandés
    "🇹🇭": "th",  # Tailandia

    # Jemer
    "🇰🇭": "km",  # Camboya

    # Lao
    "🇱🇦": "lo",  # Laos

    # Birmano
    "🇲🇲": "my",  # Myanmar

    # Filipino
    "🇵🇭": "tl",  # Filipinas

    # Indonesio
    "🇮🇩": "id",  # Indonesia

    # Malayo
    "🇲🇾": "ms",  # Malasia
    "🇧🇳": "ms",  # Brunéi

    # Hindi
    "🇮🇳": "hi",  # India*

    # Urdu
    "🇵🇰": "ur",  # Pakistán

    # Bengalí
    "🇧🇩": "bn",  # Bangladés

    # Cingalés
    "🇱🇰": "si",  # Sri Lanka*

    # Nepalí
    "🇳🇵": "ne",  # Nepal

    # Dhivehi
    "🇲🇻": "dv",  # Maldivas

    # Suajili
    "🇰🇪": "sw",  # Kenia
    "🇹🇿": "sw",  # Tanzania
    "🇺🇬": "sw",  # Uganda*

    # Kinyarwanda
    "🇷🇼": "rw",  # Ruanda

    # Amárico
    "🇪🇹": "am",  # Etiopía

    # Somalí
    "🇸🇴": "so",  # Somalia

    # Tigriña
    "🇪🇷": "ti",  # Eritrea

    # Shona
    "🇿🇼": "sn",  # Zimbabue

    # Chichewa
    "🇲🇼": "ny",  # Malaui

    # Malgache
    "🇲🇬": "mg",  # Madagascar

    # Sesoto
    "🇱🇸": "st",  # Lesoto
}

# Evita traducir de nuevo el mismo mensaje al mismo idioma si varias
# personas reaccionan con la misma bandera. Se resetea en cada reinicio
# del proceso; el tope evita que crezca sin límite mientras el bot sigue vivo.
_translated_cache = set()


@bot.event
async def on_ready():
    logger.info("✅ Conectado como %s (%d banderas soportadas)", bot.user, len(FLAG_LANG))


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

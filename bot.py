import logging
import os
import asyncio
import random
import time
from collections import OrderedDict

import aiohttp
import discord
from discord.ext import commands
from deep_translator import GoogleTranslator
from deep_translator.exceptions import (
    LanguageNotSupportedException,
    TooManyRequests,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("discord-translator")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit("❌ Falta la variable de entorno DISCORD_TOKEN")

# Opcional: email para subir el límite diario de MyMemory (5k -> 50k caracteres)
MYMEMORY_EMAIL = os.getenv("MYMEMORY_EMAIL")
# Poné USE_GOOGLE=0 en Railway si Google te bloquea siempre y querés ir directo a MyMemory
USE_GOOGLE = os.getenv("USE_GOOGLE", "1") != "0"

MAX_REPLY_LENGTH = 1900
MAX_CACHE_SIZE = 5000
TRANSLATION_DELAY = 0.8
MAX_RETRIES = 3
GOOGLE_COOLDOWN = 600  # segundos sin tocar Google tras un bloqueo
MYMEMORY_CHUNK_BYTES = 450  # MyMemory acepta ~500 bytes por petición

_translation_lock = asyncio.Lock()
_translated_cache = OrderedDict()   # (message_id, lang) -> True
_in_progress = set()                # (message_id, lang) en curso
_google_blocked_until = 0.0
_mymemory_blocked_until = 0.0

intents = discord.Intents.default()
intents.message_content = True

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
    "🇺🇸": "en", # USA (U+1F1FA U+1F1F8)
    "🇺🇲": "en", # Islas menores de EE.UU.
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

SUPPORTED_LANGS = set(GoogleTranslator().get_supported_languages(as_dict=True).values())


def remember(key):
    _translated_cache[key] = True
    while len(_translated_cache) > MAX_CACHE_SIZE:
        _translated_cache.popitem(last=False)


# ---------------------------------------------------------------------------
# Respaldo gratuito: MyMemory (API directa, no depende de las IPs de Google)
# ---------------------------------------------------------------------------

def _split_chunks(text, max_bytes=MYMEMORY_CHUNK_BYTES):
    """Parte el texto en trozos de máx. `max_bytes` bytes UTF-8,
    cortando por saltos de línea / espacios cuando se puede."""
    chunks, current = [], ""
    for word in text.split(" "):
        candidate = f"{current} {word}" if current else word
        if len(candidate.encode("utf-8")) <= max_bytes:
            current = candidate
            continue
        if current:
            chunks.append(current)
        # palabra suelta más larga que el límite: se corta por caracteres
        while len(word.encode("utf-8")) > max_bytes:
            cut = len(word)
            while len(word[:cut].encode("utf-8")) > max_bytes:
                cut -= 1
            chunks.append(word[:cut])
            word = word[cut:]
        current = word
    if current:
        chunks.append(current)
    return chunks


async def _mymemory_request(session, text, target_lang):
    target = "he" if target_lang == "iw" else target_lang  # MyMemory usa "he"
    params = {"q": text, "langpair": f"Autodetect|{target}"}
    if MYMEMORY_EMAIL:
        params["de"] = MYMEMORY_EMAIL

    async with session.get(
        "https://api.mymemory.translated.net/get",
        params=params,
        timeout=aiohttp.ClientTimeout(total=15),
    ) as resp:
        data = await resp.json(content_type=None)

    status = int(data.get("responseStatus", 0))
    translated = (data.get("responseData") or {}).get("translatedText", "")

    if status == 429 or "MYMEMORY WARNING" in translated.upper():
        raise TooManyRequests()
    if status != 200 or not translated:
        raise RuntimeError(f"MyMemory {status}: {data.get('responseDetails')}")
    return translated


async def translate_mymemory(text, target_lang):
    global _mymemory_blocked_until

    if time.time() < _mymemory_blocked_until:
        logger.warning("MyMemory en pausa (cuota diaria agotada)")
        return None

    try:
        async with aiohttp.ClientSession() as session:
            parts = []
            for chunk in _split_chunks(text):
                parts.append(await _mymemory_request(session, chunk, target_lang))
                await asyncio.sleep(0.3)
        return " ".join(parts)

    except TooManyRequests:
        _mymemory_blocked_until = time.time() + 3600
        logger.error("MyMemory: cuota diaria agotada; pausa de 1 hora")
        return None
    except Exception as e:
        logger.error("Error con MyMemory: %s", e)
        return None


# ---------------------------------------------------------------------------
# Traducción: Google primero, MyMemory si Google bloquea la IP
# ---------------------------------------------------------------------------

async def translate_google(text, target_lang):
    """Devuelve (resultado, bloqueado). `bloqueado=True` => usar el respaldo."""
    global _google_blocked_until

    async with _translation_lock:
        for attempt in range(MAX_RETRIES):
            try:
                result = await asyncio.to_thread(
                    GoogleTranslator(source="auto", target=target_lang).translate,
                    text,
                )
                await asyncio.sleep(TRANSLATION_DELAY)
                return result, False

            except LanguageNotSupportedException:
                logger.error("Idioma no soportado por Google: %s", target_lang)
                return None, True  # probamos con MyMemory

            except TooManyRequests:
                _google_blocked_until = time.time() + GOOGLE_COOLDOWN
                logger.warning(
                    "Google bloqueó la IP; usando MyMemory por %d min",
                    GOOGLE_COOLDOWN // 60,
                )
                return None, True

            except Exception as e:
                logger.warning(
                    "Error de traducción (intento %s/%s): %s",
                    attempt + 1, MAX_RETRIES, e,
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep((2 ** attempt) + random.uniform(0.5, 1.5))

    return None, True  # agotó reintentos: también probamos el respaldo


async def translate_safely(text, target_lang):
    if USE_GOOGLE and time.time() >= _google_blocked_until:
        result, fallback = await translate_google(text, target_lang)
        if not fallback:
            return result

    return await translate_mymemory(text, target_lang)


@bot.event
async def on_ready():
    logger.info("✅ Conectado como %s (%d banderas soportadas)", bot.user, len(FLAG_LANG))
    invalid = sorted({l for l in FLAG_LANG.values() if l not in SUPPORTED_LANGS})
    if invalid:
        logger.warning("Códigos no soportados por deep-translator: %s", invalid)


@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    emoji = str(payload.emoji)
    target_lang = FLAG_LANG.get(emoji)
    if target_lang is None:
        return

    cache_key = (payload.message_id, target_lang)
    if cache_key in _translated_cache or cache_key in _in_progress:
        return
    _in_progress.add(cache_key)

    try:
        channel = bot.get_channel(payload.channel_id)
        if channel is None:
            try:
                channel = await bot.fetch_channel(payload.channel_id)
            except discord.HTTPException:
                return

        try:
            message = await channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
            logger.warning("No se pudo obtener el mensaje %s: %s", payload.message_id, e)
            return

        if message.author.bot or not message.content:
            return

        translated = await translate_safely(message.content, target_lang)
        if not translated:
            logger.error("No se pudo traducir el mensaje %s", payload.message_id)
            return

        if translated.strip().lower() == message.content.strip().lower():
            return

        if len(translated) > MAX_REPLY_LENGTH:
            translated = translated[:MAX_REPLY_LENGTH - 1] + "…"

        try:
            await message.reply(
                f"{emoji} **{translated}**",
                allowed_mentions=discord.AllowedMentions.none(),
                mention_author=False,
            )
            remember(cache_key)  # solo se marca como hecho si se envió
        except discord.HTTPException as e:
            logger.error("Error enviando la traducción de %s: %s", payload.message_id, e)

    except Exception:
        logger.exception("Error inesperado procesando el mensaje %s", payload.message_id)
    finally:
        _in_progress.discard(cache_key)


bot.run(TOKEN, log_handler=None)
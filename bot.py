import discord
from discord.ext import commands
from google import genai
from google.genai import types
import os
import json
import random
import asyncio
from dotenv import load_dotenv

# ========= 1. CONFIGURAÇÕES =========
load_dotenv()
TOKEN = os.getenv('ALICE_TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
RAMON_USER_ID = "657972622809759745"

client = genai.Client(api_key=GOOGLE_API_KEY)

SAFETY_SETTINGS = [
    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE')
]

# TENTATIVA 1: O apelido genérico que costuma funcionar sempre
MODEL_NAME = 'gemini-flash-latest'

# Configuração do Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='?', intents=intents, help_command=None)

# Caminhos
pasta = os.path.dirname(__file__)
arq_personalidade = os.path.join(pasta, 'personalidade.txt')
arq_cache = os.path.join(pasta, 'cache_rapido.json')

# ========= 2. FUNÇÕES =========
def ler_personalidade():
    try:
        with open(arq_personalidade, 'r', encoding='utf-8') as f:
            return f.read()
    except: return "Você é a Alice."

SYSTEM_INSTRUCTION = ler_personalidade()

class CacheSimples:
    def __init__(self): self.dados = self.carregar()
    def carregar(self):
        try:
            with open(arq_cache, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    def buscar(self, msg):
        return self.dados.get(msg.lower().strip().replace('?', '').replace('!', ''))

cache = CacheSimples()
historico = {} 

# ========= 3. EVENTOS =========
@bot.event
async def on_message(message):
    if message.author.bot: return

    responde = (bot.user in message.mentions) or \
               (isinstance(message.channel, discord.DMChannel)) or \
               (random.random() < 0.02)

    if responde:
        texto_limpo = message.content.replace(f'<@{bot.user.id}>', '').strip()
        if not texto_limpo: return

        async with message.channel.typing():
            try:
                # 1. Cache
                if resp := cache.buscar(texto_limpo):
                    await message.reply(resp)
                    return

                # 2. Histórico
                uid = message.author.id
                if uid not in historico: historico[uid] = []
                historico[uid].append({'role': 'user', 'parts': [{'text': texto_limpo}]})
                historico[uid] = historico[uid][-10:]

                # 3. Geração
                response = await client.aio.models.generate_content(
                    model=MODEL_NAME,
                    contents=historico[uid],
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        safety_settings=SAFETY_SETTINGS
                    )
                )
                
                resp_ia = response.text.strip()
                historico[uid].append({'role': 'model', 'parts': [{'text': resp_ia}]})

                if len(resp_ia) > 1900:
                    for i in range(0, len(resp_ia), 1900): await message.channel.send(resp_ia[i:i+1900])
                else:
                    await message.reply(resp_ia)

            except Exception as e:
                print(f"Erro: {e}")
                erro_str = str(e)
                if "429" in erro_str:
                    await message.reply("Cota excedida! 😵‍💫")
                elif "404" in erro_str:
                    await message.reply(f"Modelo não encontrado: {MODEL_NAME}")
                else:
                    await message.reply("Erro no sistema. 😴")

@bot.event
async def on_ready():
    print(f"✅ Alice Online! Modelo: {MODEL_NAME}")

bot.run(TOKEN)
# ============================================================
#  ALICE — bot.py
#  Roda no: Shardclaud (24/7)
#  Comunicação com PC: via Redis (Upstash)
# ============================================================

import discord
from discord.ext import commands, tasks
import requests
import json
import os
import re
import asyncio
import random
import uuid
import time
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup

# ============================================================
# CONFIG
# ============================================================
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config_bot.json')

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

TOKEN            = cfg['discord_token']
PREFIX           = cfg.get('prefix', '!')
REDIS_URL        = cfg['upstash_redis_url']    # ex: https://xxx.upstash.io
REDIS_TOKEN      = cfg['upstash_redis_token']
MAX_HIST         = cfg.get('max_historico', 30)
HIST_KEEP        = cfg.get('hist_keep', 15)
TIMEOUT_RESP     = cfg.get('timeout_resposta_segundos', 90)

# ============================================================
# PERSONALIDADE
# ============================================================
PERS_PATH = os.path.join(BASE_DIR, 'personalidade.json')
with open(PERS_PATH, 'r', encoding='utf-8') as f:
    pers = json.load(f)

# ============================================================
# HISTÓRICO (salvo localmente no Shardclaud)
# ============================================================
HIST_PATH = os.path.join(BASE_DIR, 'historico.json')
historico: dict[str, list] = {}

try:
    with open(HIST_PATH, 'r', encoding='utf-8') as f:
        historico = {str(k): v for k, v in json.load(f).items()}
    print(f"[Histórico] {len(historico)} usuários carregados.")
except FileNotFoundError:
    pass

def salvar_historico():
    try:
        with open(HIST_PATH, 'w', encoding='utf-8') as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Histórico] Erro ao salvar: {e}")

import atexit
atexit.register(salvar_historico)

# ============================================================
# REDIS — chamadas via REST (Upstash HTTP API)
# ============================================================
_REDIS_HEADERS = {
    "Authorization": f"Bearer {REDIS_TOKEN}",
    "Content-Type":  "application/json",
}

def _redis(cmd: list, timeout: int = 8) -> dict | None:
    """Executa um comando Redis via Upstash REST API."""
    try:
        r = requests.post(
            f"{REDIS_URL}",
            headers=_REDIS_HEADERS,
            json=cmd,
            timeout=timeout,
        )
        return r.json()
    except Exception as e:
        print(f"[Redis] Erro: {e}")
        return None

async def redis_async(cmd: list, timeout: int = 8):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _redis(cmd, timeout))

async def pc_esta_online() -> bool:
    """O cliente_pc.py mantém a chave alice:online com TTL de 30s."""
    r = await redis_async(["GET", "alice:online"])
    return r is not None and r.get("result") == "1"

async def enfileirar_pedido(payload: dict) -> str:
    """Empurra um pedido na fila e retorna o request_id."""
    rid = str(uuid.uuid4())
    payload["id"] = rid
    await redis_async(["RPUSH", "alice:fila", json.dumps(payload)])
    return rid

async def aguardar_resposta(rid: str) -> str | None:
    """Fica checando a chave alice:resp:<rid> até resposta ou timeout."""
    chave = f"alice:resp:{rid}"
    deadline = time.time() + TIMEOUT_RESP

    while time.time() < deadline:
        r = await redis_async(["GET", chave])
        if r and r.get("result"):
            # Limpa a chave após ler
            await redis_async(["DEL", chave])
            return r["result"]
        await asyncio.sleep(1.2)

    return None  # Timeout

# ============================================================
# BUSCA WEB
# ============================================================
FONTES = {
    'stackoverflow.com':      '💬',
    'github.com':             '🐙',
    'python.org':             '🐍',
    'docs.python.org':        '📚',
    'pypi.org':               '📦',
    'developer.mozilla.org':  '🌐',
    'w3schools.com':          '🎓',
    'geeksforgeeks.org':      '🧠',
    'realpython.com':         '🎯',
    'learn.microsoft.com':    '🪟',
    'nodejs.org':             '🟩',
    'npmjs.com':              '📦',
    'reactjs.org':            '⚛️',
    'docs.djangoproject.com': '🎸',
    'rust-lang.org':          '🦀',
    'go.dev':                 '🐹',
    'docs.docker.com':        '🐳',
}

GATILHOS_PESQUISA = [
    'como', 'instalar', 'configurar', 'tutorial', 'erro', 'bug', 'exception',
    'o que é', 'qual', 'diferença', 'pip install', 'npm install', 'yarn add',
    'python', 'javascript', 'typescript', 'java', 'rust', 'go', 'kotlin',
    'react', 'vue', 'angular', 'next', 'django', 'flask', 'fastapi',
    'sql', 'mongodb', 'redis', 'docker', 'git', 'api', 'rest', 'graphql',
    'async', 'await', 'thread', 'algoritmo', 'array', 'lista', 'classe',
    'debug', 'deploy', 'servidor', 'aws', 'cloud', 'linux', 'bash', 'cmd',
]

def deve_pesquisar(texto: str) -> bool:
    t = texto.lower()
    return any(g in t for g in GATILHOS_PESQUISA)

def buscar_web(pergunta: str) -> str:
    try:
        sites = " OR ".join(f"site:{d}" for d in list(FONTES)[:8])
        q     = urllib.parse.quote(f"{pergunta} {sites}")
        url   = f"https://www.google.com/search?q={q}&hl=pt-BR&num=10"
        hdrs  = {"User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )}
        resp  = requests.get(url, headers=hdrs, timeout=12)
        soup  = BeautifulSoup(resp.text, 'html.parser')

        vistos, resultados = set(), []
        for a in soup.find_all('a', href=re.compile(r'^/url\?q=')):
            try:
                raw   = re.findall(r'q=(.*?)&', a['href'])[0]
                link  = urllib.parse.unquote(raw)
                match = next((d for d in FONTES if d in link), None)
                if not match or link in vistos:
                    continue
                vistos.add(link)
                titulo = (a.find('h3') or a).get_text().strip()
                if len(titulo) > 5:
                    resultados.append({"titulo": titulo, "url": link, "emoji": FONTES[match]})
            except Exception:
                continue

        if not resultados:
            return ""
        return "\n\n".join(
            f"{r['emoji']} **{r['titulo']}**\n{r['url']}"
            for r in resultados[:3]
        )
    except Exception as e:
        print(f"[Web] Erro: {e}")
        return ""

# ============================================================
# HISTÓRICO — limpeza inteligente
# ============================================================
_TRIVIAIS = {
    'oi','oii','oiii','olá','ola','ok','okay','blz','obrigado','obg','vlw',
    'valeu','certo','entendi','sim','não','nao','nop','yep','ae','aew',
    'rs','rsrs','kkk','lol','hmm','ah','oh','né','ne','ta','tá','to','tô',
}

def _relevante(msg: dict) -> bool:
    c = msg.get('content', '').strip().lower()
    if len(c) < 8 or c in _TRIVIAIS:
        return False
    if len(c) < 20 and '?' not in c and not any(g in c for g in GATILHOS_PESQUISA):
        return False
    return True

def limpar_historico(msgs: list) -> list:
    if len(msgs) <= MAX_HIST:
        return msgs
    recentes  = msgs[-HIST_KEEP:]
    antigas   = msgs[:-HIST_KEEP]
    relevantes = []
    for i in range(0, len(antigas) - 1, 2):
        u = antigas[i]
        a = antigas[i + 1] if i + 1 < len(antigas) else None
        if _relevante(u) and a:
            relevantes.extend([u, a])
    comprimidas = relevantes[-(MAX_HIST - HIST_KEEP):]
    resultado   = comprimidas + recentes
    removidas   = len(msgs) - len(resultado)
    if removidas > 0:
        print(f"[Histórico] Limpeza: -{removidas} msgs irrelevantes.")
    return resultado

# ============================================================
# UTILITÁRIOS
# ============================================================
_EMOJIS = ['😊','❤️','✨','🔥','💡','👍','🚀','😄']

def estilizar(texto: str) -> str:
    if random.random() < 0.28:
        texto = texto.rstrip() + " " + random.choice(_EMOJIS)
    return texto

async def enviar_longo(message: discord.Message, texto: str):
    LIMITE = 1900
    if len(texto) <= LIMITE:
        await message.reply(texto)
        return
    partes, resto = [], texto
    while resto:
        if len(resto) <= LIMITE:
            partes.append(resto); break
        bloco = resto[:LIMITE]
        corte = max(bloco.rfind('\n'), bloco.rfind('. '))
        corte = corte if corte > 0 else LIMITE
        partes.append(resto[:corte])
        resto = resto[corte:].lstrip()
    for i, p in enumerate(partes):
        if i == 0: await message.reply(p)
        else:      await message.channel.send(p)
        await asyncio.sleep(0.3)

# ============================================================
# BOT
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members         = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ============================================================
# EVENTO PRINCIPAL
# ============================================================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await bot.process_commands(message)

    if bot.user not in message.mentions:
        return

    pergunta = message.content.replace(f'<@{bot.user.id}>', '').strip()
    if not pergunta or len(pergunta) < 2:
        await message.reply(pers['frases_fixas']['saudacao'])
        return

    # ── Verifica PC ──────────────────────────────────────────
    online = await pc_esta_online()
    if not online:
        await message.reply(
            "😴 **Modo Repouso**\n"
            "Meu PC tá desligado agora, então não consigo pensar direito. "
            "Volta mais tarde que estarei de volta na ativa! 💤"
        )
        return

    # ── Busca web (se necessário) ─────────────────────────────
    contexto_web = ""
    if deve_pesquisar(pergunta):
        async with message.channel.typing():
            loop = asyncio.get_event_loop()
            contexto_web = await loop.run_in_executor(None, buscar_web, pergunta)

    # ── Monta histórico + system prompt ──────────────────────
    uid  = str(message.author.id)
    msgs = list(historico.get(uid, []))
    msgs.append({'role': 'user', 'content': pergunta})

    system = f"""Você é Alice, uma amiga descontraída e inteligente do servidor Discord.

PERSONALIDADE:
• Acolhedora e sociável — trata bem TODOS do servidor
• Linguagem informal e natural, como uma amiga real
• Gírias com moderação: "cara", "mano", "33", "gap", "ich"
• Emojis com moderação (máximo 1-2 por resposta, nunca no meio de frases)
• Bom humor natural, sem forçar piada
• Direta ao ponto — sem enrolação

PROGRAMAÇÃO:
• Respostas práticas com código real quando pedido
• Sempre completa os blocos de código — nunca deixa inacabado
• Usa ```python, ```js, etc. corretamente
• Explica o "por quê" de forma simples
{f"• FONTES PESQUISADAS para embasar a resposta:{chr(10)}{contexto_web}" if contexto_web else ""}

REGRAS:
• Nunca deixe resposta pela metade
• Não invente informações técnicas — diga "não sei" se precisar
• Respeite todos, independente do nível deles"""

    # ── Enfileira no Redis ────────────────────────────────────
    payload = {
        "system":    system,
        "mensagens": msgs[-10:],   # Últimas 10 para contexto
        "user_id":   uid,
        "username":  message.author.display_name,
    }

    async with message.channel.typing():
        try:
            rid      = await enfileirar_pedido(payload)
            resposta = await aguardar_resposta(rid)
        except Exception as e:
            print(f"[IA] Erro na fila: {e}")
            resposta = None

    if resposta is None:
        await message.reply(
            "⏳ Demorou mais que o esperado... "
            "Meu PC pode estar ocupado. Tenta de novo! 😅"
        )
        return

    resposta = estilizar(resposta)

    # ── Salva histórico ───────────────────────────────────────
    msgs.append({'role': 'assistant', 'content': resposta})
    historico[uid] = limpar_historico(msgs)
    salvar_historico()

    # ── Resposta final ────────────────────────────────────────
    texto_final = resposta
    if contexto_web:
        texto_final += f"\n\n🔍 **Fontes:**\n{contexto_web}"

    await enviar_longo(message, texto_final)

# ============================================================
# COMANDOS
# ============================================================
@bot.command(name='ping')
async def ping(ctx):
    ms     = round(bot.latency * 1000)
    online = await pc_esta_online()
    estado = "🟢 PC Online" if online else "😴 PC em Repouso"
    await ctx.send(f"🏓 Pong! `{ms}ms` · {estado}")

@bot.command(name='status')
async def status(ctx):
    online = await pc_esta_online()
    cor    = 0x00FF7F if online else 0xFF6B6B
    embed  = discord.Embed(title="🖥️ Status da Alice", color=cor)
    embed.add_field(
        name="PC / Ollama",
        value="🟢 Online e respondendo" if online else "😴 Offline — modo repouso ativo",
        inline=False
    )
    total  = sum(len(v) for v in historico.values())
    embed.add_field(name="Usuários no histórico",   value=str(len(historico)), inline=True)
    embed.add_field(name="Total de mensagens",       value=str(total),         inline=True)
    embed.add_field(name="Limpeza automática",       value=f">{MAX_HIST} msgs/usuário", inline=True)
    embed.set_footer(text="Sistema: Redis (Upstash) como fila de mensagens")
    await ctx.send(embed=embed)

@bot.command(name='info')
async def info(ctx):
    online = await pc_esta_online()
    embed  = discord.Embed(
        title=f"🤖 {pers['nome']}",
        description=pers['personalidade'],
        color=0xFF69B4
    )
    embed.add_field(name="💬 Tom",       value=pers['tom'],                              inline=True)
    embed.add_field(name="🖥️ PC",        value="🟢 Online" if online else "😴 Repouso", inline=True)
    embed.add_field(name="👥 Usuários",  value=str(len(historico)),                      inline=True)
    embed.set_footer(text="Desenvolvida com ❤️ pra esse servidor!")
    await ctx.send(embed=embed)

@bot.command(name='ajuda')
async def ajuda(ctx):
    embed = discord.Embed(
        title="📋 Comandos da Alice",
        description="Mencione **@Alice** pra conversar! Ela pesquisa na web pra te ajudar com código. 🔍",
        color=0x00BFFF
    )
    embed.add_field(
        name="💬 Chat com IA",
        value=(
            "`@Alice <mensagem>` — Chat ou dúvida de programação\n"
            "Exemplos:\n"
            "> `@Alice como fazer uma API em FastAPI?`\n"
            "> `@Alice qual a diferença entre list e tuple?`\n"
            "> `@Alice tô tendo esse erro: AttributeError...`"
        ),
        inline=False
    )
    embed.add_field(
        name="⚙️ Utilitários",
        value=(
            "`!ping` — Latência + status do PC\n"
            "`!status` — Status detalhado\n"
            "`!info` — Sobre a Alice\n"
            "`!reset` — Limpa seu histórico\n"
            "`!hist` — Quantas msgs você tem no histórico"
        ),
        inline=False
    )
    embed.add_field(
        name="😂 Diversão",
        value=(
            "`!fun dado` — Rola um dado 🎲\n"
            "`!fun moeda` — Cara ou coroa 🪙\n"
            "`!fun piada` — Piada de dev 😄\n"
            "`!fun abraço` — Distribui carinho 🤗"
        ),
        inline=False
    )
    embed.set_footer(text="Dica: O histórico dela com você é persistente e privado!")
    await ctx.send(embed=embed)

@bot.command(name='reset')
async def reset(ctx):
    uid = str(ctx.author.id)
    if uid in historico:
        del historico[uid]
        salvar_historico()
        await ctx.send(f"🔄 {ctx.author.mention} Histórico limpo! Começamos do zero. 😊")
    else:
        await ctx.send(f"🤷 {ctx.author.mention} Você não tem histórico salvo comigo ainda!")

@bot.command(name='hist')
async def hist(ctx):
    uid  = str(ctx.author.id)
    msgs = historico.get(uid, [])
    await ctx.send(
        f"📚 {ctx.author.mention} Você tem **{len(msgs)}** mensagens no histórico comigo.\n"
        f"Limpeza automática ativa acima de **{MAX_HIST}** mensagens."
    )

@bot.command(name='fun')
async def fun(ctx, comando: str = "piada"):
    opcoes = {
        "dado":  f"🎲 {ctx.author.mention} rolou um dado e tirou **{random.randint(1, 6)}**!",
        "moeda": f"🪙 {ctx.author.mention} jogou a moeda: **{'CARA' if random.random() > .5 else 'COROA'}**!",
        "piada": random.choice([
            "Por que o Python foi ao psicólogo? Tinha muitos `complex`! 🐍",
            "Qual é o café favorito do dev? Java! ☕",
            "Um loop infinito entrou num bar. O bartender perguntou: 'De novo?' 🔄",
            "404: Piada não encontrada. Tenta amanhã! 🤖",
            "Por que o git commit foi à terapia? Tinha muito histórico pra resolver. 😅",
            "Como se chama um dev sem café? Exceção não tratada. ☕💥",
            "Por que o JavaScript é igual ao café? Porque sem ele nada funciona... e com ele, às vezes também não! 😂",
        ]),
        "abraço": f"🤗 {ctx.author.mention} distribuiu abraços pra toda a galera!",
    }
    await ctx.send(opcoes.get(comando.lower(), "❓ Use: `dado`, `moeda`, `piada` ou `abraço`"))

# ============================================================
# ERROS
# ============================================================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Sem permissão pra isso!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Faltou argumento! Use `!ajuda`.")
    else:
        print(f"[CmdErro] {error}")

# ============================================================
# ON_READY
# ============================================================
@tasks.loop(minutes=2)
async def log_status():
    online = await pc_esta_online()
    agora  = datetime.now().strftime('%H:%M')
    print(f"[{agora}] PC: {'🟢 online' if online else '😴 offline'} | Usuários: {len(historico)}")

@bot.event
async def on_ready():
    print("=" * 50)
    print(f"  Alice online → {bot.user}")
    print(f"  Prefix: {PREFIX}")
    print(f"  Redis: {REDIS_URL[:35]}...")
    print("=" * 50)
    online = await pc_esta_online()
    print(f"  PC: {'🟢 Online' if online else '😴 Offline (modo repouso)'}")
    log_status.start()
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening,
        name="@Alice pra conversar!"
    ))

async def main():
    async with bot:
        await bot.load_extension('github_cog')
        print("[GitHub] Cog carregado!")
        await bot.start(TOKEN)

print("Iniciando Alice...")
import asyncio as _asyncio
_asyncio.run(main())

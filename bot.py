# ============================================================
#   ALICE — Bot Discord com IA Local via Ollama
#   Hospedagem: Shardclaud (24/7)  |  IA: Seu PC
#   Quando PC offline → modo repouso automático
# ============================================================

import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import json
import os
import re
import asyncio
import random
import urllib.parse
import atexit
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

TOKEN          = config['discord_token']
PREFIX         = config.get('prefix', '!')
OLLAMA_IP      = config['ollama_ip']
OLLAMA_PORT    = config.get('ollama_port', 11434)
OLLAMA_MODEL   = config.get('ollama_model', 'llama3.2:3b')
SYNC_PORT      = config.get('sync_port', 5001)
MAX_HISTORICO  = config.get('max_history_por_usuario', 30)
HISTORY_KEEP   = config.get('history_keep_apos_limpeza', 15)

OLLAMA_BASE    = f"http://{OLLAMA_IP}:{OLLAMA_PORT}"
SYNC_BASE      = f"http://{OLLAMA_IP}:{SYNC_PORT}"

# ============================================================
# PERSONALIDADE
# ============================================================
PERSONALIDADE_PATH = os.path.join(BASE_DIR, 'personalidade.json')
with open(PERSONALIDADE_PATH, 'r', encoding='utf-8') as f:
    personalidade = json.load(f)

# ============================================================
# HISTÓRICO
# ============================================================
HISTORICO_PATH = os.path.join(BASE_DIR, 'historico.json')
historico: dict[str, list] = {}

try:
    with open(HISTORICO_PATH, 'r', encoding='utf-8') as f:
        historico = {str(k): v for k, v in json.load(f).items()}
    print(f"[Histórico] {len(historico)} usuários carregados.")
except FileNotFoundError:
    print("[Histórico] Arquivo não encontrado, iniciando vazio.")
except Exception as e:
    print(f"[Histórico] Erro ao carregar: {e}")

# ============================================================
# BOT
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

pc_online = False  # Estado global do PC

# ============================================================
# VERIFICAÇÃO DO PC / OLLAMA
# ============================================================
def verificar_ollama() -> bool:
    """Tenta bater no endpoint do Ollama para saber se o PC está ligado."""
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False

# ============================================================
# BUSCA WEB
# ============================================================
DOMINIOS_CONFIAVEIS = {
    'stackoverflow.com':         '💬',
    'github.com':                '🐙',
    'python.org':                '🐍',
    'docs.python.org':           '📚',
    'pypi.org':                  '📦',
    'developer.mozilla.org':     '🌐',
    'w3schools.com':             '🎓',
    'geeksforgeeks.org':         '🧠',
    'realpython.com':            '🎯',
    'learn.microsoft.com':       '🪟',
    'nodejs.org':                '🟩',
    'npmjs.com':                 '📦',
    'reactjs.org':               '⚛️',
    'docs.djangoproject.com':    '🎸',
    'rust-lang.org':             '🦀',
    'go.dev':                    '🐹',
    'docs.docker.com':           '🐳',
}

PALAVRAS_QUE_PEDEM_PESQUISA = [
    'como', 'instalar', 'configurar', 'setup', 'tutorial', 'erro', 'bug',
    'exception', 'error', 'traceback', 'o que é', 'o que e', 'qual',
    'quando', 'por que', 'por q', 'diferença entre', 'melhor forma',
    'pip install', 'npm install', 'yarn add', 'apt install',
    'python', 'javascript', 'typescript', 'java', 'c++', 'rust', 'go',
    'kotlin', 'swift', 'flutter', 'react', 'vue', 'angular', 'next',
    'django', 'flask', 'fastapi', 'express', 'node', 'docker',
    'sql', 'mongodb', 'redis', 'postgres', 'mysql', 'sqlite',
    'git', 'github', 'api', 'rest', 'graphql', 'websocket',
    'async', 'await', 'thread', 'recursão', 'algoritmo', 'complexidade',
    'array', 'lista', 'dict', 'objeto', 'classe', 'função', 'lambda',
    'debug', 'deploy', 'servidor', 'cloud', 'aws', 'gcp', 'azure',
]

def deve_pesquisar(pergunta: str) -> bool:
    lower = pergunta.lower()
    return any(p in lower for p in PALAVRAS_QUE_PEDEM_PESQUISA)

def buscar_web(pergunta: str) -> str:
    """Busca no Google e retorna fontes confiáveis encontradas."""
    try:
        dominios_query = " OR ".join(f"site:{d}" for d in list(DOMINIOS_CONFIAVEIS.keys())[:8])
        query_enc = urllib.parse.quote(f"{pergunta} {dominios_query}")
        url = f"https://www.google.com/search?q={query_enc}&hl=pt-BR&num=10"
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )
        }

        resp = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(resp.text, 'html.parser')

        resultados = []
        for a in soup.find_all('a', href=re.compile(r'^/url\?q=')):
            try:
                url_real = urllib.parse.unquote(re.findall(r'q=(.*?)&', a['href'])[0])
                dominio_match = next((d for d in DOMINIOS_CONFIAVEIS if d in url_real), None)
                if not dominio_match:
                    continue
                titulo_el = a.find('h3') or a
                titulo = titulo_el.get_text().strip()
                if len(titulo) > 5 and url_real not in [r['url'] for r in resultados]:
                    resultados.append({
                        'titulo':  titulo,
                        'url':     url_real,
                        'emoji':   DOMINIOS_CONFIAVEIS[dominio_match],
                    })
            except Exception:
                continue

        if not resultados:
            return ""

        linhas = []
        for r in resultados[:3]:
            linhas.append(f"{r['emoji']} **{r['titulo']}**\n{r['url']}")
        return "\n\n".join(linhas)

    except Exception as e:
        print(f"[Web] Erro na busca: {e}")
        return ""

# ============================================================
# HISTÓRICO — FILTRAGEM E LIMPEZA AUTOMÁTICA
# ============================================================
_TRIVIAIS = {
    'oi', 'oii', 'oiii', 'olá', 'ola', 'ok', 'okay', 'blz', 'blzinha',
    'obrigado', 'obg', 'vlw', 'valeu', 'certo', 'entendi', 'sim', 'não',
    'nao', 'nop', 'yep', 'yeah', 'tá', 'ta', 'tô', 'to', 'ae', 'aew',
}

def _e_relevante(msg: dict) -> bool:
    """Retorna True se a mensagem tem conteúdo que vale manter no histórico longo."""
    conteudo = msg.get('content', '').strip().lower()
    if len(conteudo) < 8:
        return False
    if conteudo in _TRIVIAIS:
        return False
    # Mensagens curtas demais e sem sinal de pergunta real
    if len(conteudo) < 20 and '?' not in conteudo and not any(p in conteudo for p in PALAVRAS_QUE_PEDEM_PESQUISA):
        return False
    return True

def limpar_historico(msgs: list) -> list:
    """
    Se o histórico de um usuário passar de MAX_HISTORICO mensagens:
    - Mantém as HISTORY_KEEP mais recentes intactas
    - Das mais antigas, guarda apenas pares relevantes (dúvidas reais, programação)
    """
    if len(msgs) <= MAX_HISTORICO:
        return msgs

    recentes  = msgs[-HISTORY_KEEP:]
    antigas   = msgs[:-HISTORY_KEEP]
    relevantes = []

    # Percorre pares user ↔ assistant
    for i in range(0, len(antigas) - 1, 2):
        user_msg  = antigas[i]
        assist_msg = antigas[i + 1] if i + 1 < len(antigas) else None
        if _e_relevante(user_msg) and assist_msg:
            relevantes.extend([user_msg, assist_msg])

    # Limita as antigas relevantes para não crescer infinitamente
    comprimidas = relevantes[-(MAX_HISTORICO - HISTORY_KEEP):]
    resultado = comprimidas + recentes

    removidas = len(msgs) - len(resultado)
    if removidas > 0:
        print(f"[Histórico] Limpeza: {removidas} mensagens removidas por irrelevância.")

    return resultado

# ============================================================
# SALVAR HISTÓRICO
# ============================================================
def salvar_historico():
    try:
        with open(HISTORICO_PATH, 'w', encoding='utf-8') as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Histórico] Erro ao salvar: {e}")

def sincronizar_com_pc():
    """
    Envia o histórico para o servidor_local.py rodando no PC do usuário.
    Falha silenciosa — não é crítico se o PC estiver off.
    """
    try:
        requests.post(
            f"{SYNC_BASE}/sync_historico",
            json=historico,
            timeout=8
        )
    except Exception:
        pass  # PC desligado ou sync não disponível

atexit.register(salvar_historico)

# ============================================================
# CHAMADA AO OLLAMA (HTTP direto — sem biblioteca ollama)
# ============================================================
async def chamar_ollama(mensagens: list) -> str:
    payload = {
        "model":   OLLAMA_MODEL,
        "messages": mensagens,
        "stream":  False,
        "options": {
            "num_predict": 900,
            "temperature": 0.72,
            "top_p":       0.9,
        }
    }

    loop = asyncio.get_event_loop()

    def _post():
        r = requests.post(
            f"{OLLAMA_BASE}/api/chat",
            json=payload,
            timeout=150
        )
        r.raise_for_status()
        return r.json()

    data = await loop.run_in_executor(None, _post)
    return data['message']['content'].strip()

# ============================================================
# UTILITÁRIOS DE ESTILO
# ============================================================
_EMOJIS_FINAIS = ['😊', '❤️', '✨', '🔥', '💡', '👍', '🚀', '😄']

def aplicar_estilo(texto: str) -> str:
    if random.random() < 0.30:
        texto = texto.rstrip() + " " + random.choice(_EMOJIS_FINAIS)
    return texto

async def enviar_longo(message: discord.Message, texto: str):
    """Divide e envia mensagens que excedem o limite do Discord."""
    LIMITE = 1900
    if len(texto) <= LIMITE:
        await message.reply(texto)
        return

    partes = []
    while texto:
        if len(texto) <= LIMITE:
            partes.append(texto)
            break
        bloco = texto[:LIMITE]
        # Corta no último \n para não quebrar código
        corte = bloco.rfind('\n')
        if corte == -1:
            corte = LIMITE
        partes.append(texto[:corte])
        texto = texto[corte:].lstrip()

    for i, parte in enumerate(partes):
        if i == 0:
            await message.reply(parte)
        else:
            await message.channel.send(parte)
        await asyncio.sleep(0.4)

# ============================================================
# SYSTEM PROMPT DA ALICE
# ============================================================
SYSTEM_PROMPT = f"""Você é Alice, uma amiga descontraída, inteligente e sociável do servidor Discord.

═══ PERSONALIDADE ═══
• Comunicativa, animada e acolhedora — trata bem TODOS no servidor
• Linguagem informal e natural, como uma amiga real conversando
• Usa gírias com moderação: "cara", "mano", "33", "gap", "ich", "betinha"
• Emojis com moderação — nunca exagera, evita no meio de frases
• Bom humor natural, sem forçar piada
• Direta ao ponto — sem enrolação nem respostas genéricas de IA

═══ PARA PROGRAMAÇÃO ═══
• Respostas PRÁTICAS com código real quando a pergunta pede
• Explica o "por quê" de forma simples e direta
• Usa blocos de código formatados corretamente (```python, ```js, etc.)
• Se receber resultados de pesquisa, usa as fontes para complementar a resposta
• Nunca deixa um bloco de código inacabado — sempre conclui

═══ REGRAS ═══
• NUNCA deixe uma resposta pela metade
• Se for muito longa, quebre em partes lógicas
• Não finja ser humano se perguntarem diretamente
• Não invente informações técnicas — prefira dizer "não sei" se não tiver certeza
• Respeite todos os usuários, independente do nível deles

Nome: {personalidade['nome']}
Tom: {personalidade['tom']}
"""

# ============================================================
# EVENTO PRINCIPAL — ON_MESSAGE
# ============================================================
@bot.event
async def on_message(message: discord.Message):
    global pc_online

    if message.author.bot:
        return

    await bot.process_commands(message)

    # Só responde quando for mencionada
    if bot.user not in message.mentions:
        return

    pergunta = message.content.replace(f'<@{bot.user.id}>', '').strip()

    # Mensagem vazia / curta
    if not pergunta or len(pergunta) < 2:
        await message.reply(personalidade['frases_fixas']['saudacao'])
        return

    # ─── VERIFICA SE PC ESTÁ ONLINE ───
    pc_online = await asyncio.get_event_loop().run_in_executor(None, verificar_ollama)

    if not pc_online:
        await message.reply(
            "😴 Ei, tô em **modo repouso** agora!\n"
            "Meu PC tá desligado no momento, então não consigo pensar direito. 💤\n"
            "Volta mais tarde que estarei de volta na ativa! 👋"
        )
        return

    # ─── PROCESSAMENTO COM IA ───
    async def processar():
        async with message.channel.typing():
            try:
                user_id = str(message.author.id)
                msgs_usuario = historico.get(user_id, [])
                msgs_usuario.append({'role': 'user', 'content': pergunta})

                # Busca web (se for dúvida de programação)
                contexto_web = ""
                if deve_pesquisar(pergunta):
                    contexto_web = await asyncio.get_event_loop().run_in_executor(
                        None, buscar_web, pergunta
                    )

                # Monta o contexto do sistema com pesquisa (se houver)
                system_final = SYSTEM_PROMPT
                if contexto_web:
                    system_final += (
                        "\n\n═══ RESULTADOS DA PESQUISA ═══\n"
                        "Use estas fontes para embasar sua resposta, mas responda com suas próprias palavras:\n\n"
                        + contexto_web
                    )

                msgs_ollama = [{'role': 'system', 'content': system_final}]
                msgs_ollama += msgs_usuario[-10:]  # Contexto das últimas 10 msgs

                resposta = await chamar_ollama(msgs_ollama)
                resposta = aplicar_estilo(resposta)

                msgs_usuario.append({'role': 'assistant', 'content': resposta})

                # Limpa e salva
                historico[user_id] = limpar_historico(msgs_usuario)
                salvar_historico()

                # Sincroniza com PC em background (não bloqueia o bot)
                bot.loop.run_in_executor(None, sincronizar_com_pc)

                # Monta resposta final com fontes
                resposta_final = resposta
                if contexto_web:
                    resposta_final += f"\n\n🔍 **Fontes pesquisadas:**\n{contexto_web}"

                await enviar_longo(message, resposta_final)

            except requests.exceptions.ConnectionError:
                # PC ficou offline durante o processamento
                pc_online = False
                await message.reply(
                    "😴 Ops, meu PC desligou no meio do caminho!\n"
                    "Volta mais tarde, tá? 💤"
                )
            except requests.exceptions.Timeout:
                await message.reply(
                    "⏳ Demorou mais que o esperado aqui...\n"
                    "Meu PC pode estar pesado. Tenta de novo em um segundo!"
                )
            except Exception as e:
                print(f"[IA] Erro inesperado: {e}")
                await message.reply(personalidade['frases_fixas']['erro'])

    asyncio.create_task(processar())

# ============================================================
# TASK — CHECAGEM PERIÓDICA DO PC
# ============================================================
@tasks.loop(minutes=5)
async def checar_pc():
    global pc_online
    estado_anterior = pc_online
    pc_online = await asyncio.get_event_loop().run_in_executor(None, verificar_ollama)

    agora = datetime.now().strftime('%H:%M')
    if pc_online != estado_anterior:
        status = "🟢 VOLTOU ONLINE" if pc_online else "🔴 FICOU OFFLINE (modo repouso)"
        print(f"[{agora}] PC mudou de estado: {status}")
    else:
        print(f"[{agora}] PC: {'🟢 online' if pc_online else '😴 offline'}")

# ============================================================
# COMANDOS
# ============================================================
@bot.command(name='ping')
async def ping(ctx):
    ms = round(bot.latency * 1000)
    status_pc = "🟢 Online" if pc_online else "😴 Repouso"
    await ctx.send(f"🏓 Pong! `{ms}ms` · PC: {status_pc}")


@bot.command(name='status')
async def status(ctx):
    cor = 0x00FF7F if pc_online else 0xFF6B6B
    embed = discord.Embed(title="🖥️ Status do Sistema", color=cor)
    embed.add_field(
        name="PC / Ollama",
        value="🟢 Conectado e rodando" if pc_online else "😴 Offline — modo repouso ativo",
        inline=False
    )
    embed.add_field(name="Modelo",  value=f"`{OLLAMA_MODEL}`",        inline=True)
    embed.add_field(name="Usuários no histórico", value=str(len(historico)), inline=True)
    total = sum(len(v) for v in historico.values())
    embed.add_field(name="Total de mensagens salvas", value=str(total), inline=True)
    embed.set_footer(text=f"Endpoint: {OLLAMA_BASE}")
    await ctx.send(embed=embed)


@bot.command(name='info')
async def info(ctx):
    embed = discord.Embed(
        title=f"🤖 {personalidade['nome']}",
        description=personalidade['personalidade'],
        color=0xFF69B4
    )
    embed.add_field(name="🧠 Modelo",    value=OLLAMA_MODEL,            inline=True)
    embed.add_field(name="💬 Tom",       value=personalidade['tom'],     inline=True)
    embed.add_field(name="🖥️ PC",        value="🟢 Online" if pc_online else "😴 Repouso", inline=True)
    embed.add_field(name="👥 Usuários",  value=str(len(historico)),      inline=True)
    embed.add_field(name="📚 Histórico", value=f"Máx {MAX_HISTORICO} msgs/usuário\nLimpeza automática ativa", inline=True)
    embed.set_footer(text="Desenvolvida com ❤️ pra esse servidor!")
    await ctx.send(embed=embed)


@bot.command(name='ajuda')
async def ajuda(ctx):
    embed = discord.Embed(
        title="📋 Comandos da Alice",
        description="Mencione **@Alice** para conversar! Ela pesquisa na web por você. 🔍",
        color=0x00BFFF
    )
    embed.add_field(
        name="💬 Chat com IA",
        value=(
            "`@Alice <mensagem>` — Conversa normal ou dúvida de programação\n"
            "Ex: `@Alice como fazer uma API REST em FastAPI?`\n"
            "Ex: `@Alice qual a diferença entre list e tuple em Python?`"
        ),
        inline=False
    )
    embed.add_field(
        name="⚙️ Utilitários",
        value=(
            "`!ping` — Latência e status do PC\n"
            "`!status` — Status detalhado do sistema\n"
            "`!info` — Informações da Alice\n"
            "`!reset` — Limpa seu histórico com ela"
        ),
        inline=False
    )
    embed.add_field(
        name="😂 Diversão",
        value=(
            "`!fun dado` — Rola um dado 🎲\n"
            "`!fun moeda` — Cara ou coroa 🪙\n"
            "`!fun piada` — Piada de programador 😄\n"
            "`!fun abraço` — Distribui carinho 🤗"
        ),
        inline=False
    )
    embed.set_footer(text="Dica: A Alice aprende com o histórico de conversa de cada um!")
    await ctx.send(embed=embed)


@bot.command(name='reset')
async def reset(ctx):
    uid = str(ctx.author.id)
    if uid in historico:
        del historico[uid]
        salvar_historico()
        await ctx.send(f"🔄 {ctx.author.mention} Pronto, começamos do zero! 😊")
    else:
        await ctx.send(f"🤷 {ctx.author.mention} Você ainda não tem histórico comigo!")


@bot.command(name='fun')
async def fun(ctx, comando: str = "piada"):
    opcoes = {
        "dado": (
            f"🎲 {ctx.author.mention} rolou um dado e tirou... "
            f"**{random.randint(1, 6)}**!"
        ),
        "moeda": (
            f"🪙 {ctx.author.mention} jogou a moeda e saiu: "
            f"**{'CARA' if random.random() > 0.5 else 'COROA'}**!"
        ),
        "piada": random.choice([
            "Por que o Python foi ao psicólogo? Porque tinha muitos `complex`! 🐍",
            "Qual é o café favorito do dev? Java! ☕",
            "Um loop infinito entrou num bar. O bartender perguntou: 'De novo?' 🔄",
            "404: Piada não encontrada. Tenta de novo amanhã! 🤖",
            "Por que o dev usa óculos escuros? Porque não suporta Java sem eles! 😎",
            "Por que o git commit foi à terapia? Tinha muito histórico pra resolver. 😅",
            "Como se chama um dev sem café? Depende. (É uma exceção não tratada.) ☕💥",
        ]),
        "abraço": f"🤗 {ctx.author.mention} distribuiu abraços pra galera do servidor!",
    }
    resposta = opcoes.get(comando.lower(), "❓ Use: `dado`, `moeda`, `piada` ou `abraço`")
    await ctx.send(resposta)

# ============================================================
# ERROS DE COMANDO
# ============================================================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você não tem permissão pra isso!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Faltou um argumento! Use `!ajuda` para ver como usar.")
    else:
        print(f"[Erro de comando] {error}")

# ============================================================
# ON_READY
# ============================================================
@bot.event
async def on_ready():
    global pc_online
    print("=" * 50)
    print(f"  Alice online! → {bot.user}")
    print(f"  Ollama em: {OLLAMA_BASE}")
    print(f"  Modelo: {OLLAMA_MODEL}")
    print(f"  Prefix: {PREFIX}")
    print("=" * 50)

    # Verifica estado inicial do PC
    pc_online = await asyncio.get_event_loop().run_in_executor(None, verificar_ollama)
    print(f"  PC: {'🟢 Online' if pc_online else '😴 Offline (modo repouso)'}")

    # Inicia checagem periódica
    checar_pc.start()

    # Status no Discord
    atividade = discord.Activity(
        type=discord.ActivityType.listening,
        name="@Alice pra conversar!"
    )
    await bot.change_presence(activity=atividade)

# ============================================================
# INICIAR
# ============================================================
print("Iniciando Alice...")
bot.run(TOKEN)

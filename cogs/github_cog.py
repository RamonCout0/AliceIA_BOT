# ============================================================
#  ALICE — github_cog.py
#  Integração com GitHub via API REST
#
#  PERMISSÕES:
#  - Dono (OWNER_ID no config):      tudo — PR, merge, fechar, criar repo, etc.
#  - Membro da org GitHub linkado:   criar issue, comentar, criar repo
#  - Sem link ou fora da org:        só leitura (listar, ver detalhes)
#
#  COMO LINKAR:
#  O usuário do Discord roda:  !gh conectar <usuario_github>
#  O bot verifica se ele é membro da organização e salva o vínculo.
# ============================================================

import discord
from discord.ext import commands
import requests
import json
import os
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'config_bot.json')

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    _cfg = json.load(f)

GH_TOKEN = _cfg['github_token']
GH_REPO  = _cfg['github_repo']          # ex: "MinhaOrg/meu-repo"
GH_ORG   = _cfg['github_org']           # ex: "MinhaOrg"
OWNER_ID = int(_cfg['owner_discord_id'])

GH_API   = "https://api.github.com"
GH_HEADS = {
    "Authorization":        f"Bearer {GH_TOKEN}",
    "Accept":               "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# ============================================================
# VÍNCULO DISCORD <-> GITHUB  (salvo em links_github.json)
# ============================================================
LINKS_PATH = os.path.join(BASE_DIR, 'links_github.json')

def _carregar_links() -> dict:
    try:
        with open(LINKS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def _salvar_links(links: dict):
    with open(LINKS_PATH, 'w', encoding='utf-8') as f:
        json.dump(links, f, ensure_ascii=False, indent=2)

def _github_do_discord(discord_id: int) -> str | None:
    return _carregar_links().get(str(discord_id))

def _vincular(discord_id: int, github_user: str):
    links = _carregar_links()
    links[str(discord_id)] = github_user
    _salvar_links(links)

def _desvincular(discord_id: int):
    links = _carregar_links()
    links.pop(str(discord_id), None)
    _salvar_links(links)

# ============================================================
# VERIFICACAO DE MEMBRO DA ORG
# ============================================================
def _e_membro_org(github_user: str) -> bool:
    """204 = membro  |  404 = nao e membro."""
    r = requests.get(
        f"{GH_API}/orgs/{GH_ORG}/members/{github_user}",
        headers=GH_HEADS,
        timeout=10
    )
    return r.status_code == 204

# ============================================================
# HELPERS DE PERMISSAO
# ============================================================
def _e_dono(ctx: commands.Context) -> bool:
    return ctx.author.id == OWNER_ID

async def _verificar_membro(ctx: commands.Context):
    if _e_dono(ctx):
        gh = _github_do_discord(ctx.author.id) or "dono"
        return True, gh

    gh = _github_do_discord(ctx.author.id)
    if not gh:
        await ctx.send(
            "🔗 Você ainda não vinculou sua conta GitHub!\n"
            "Use `!gh conectar <seu_usuario_github>` para se vincular."
        )
        return False, None

    if not _e_membro_org(gh):
        await ctx.send(
            f"🔒 Sua conta GitHub **{gh}** não é membro da organização **{GH_ORG}**.\n"
            "Peça ao dono para te adicionar à org e tente novamente."
        )
        return False, None

    return True, gh

def _apenas_dono():
    async def predicate(ctx: commands.Context):
        if not _e_dono(ctx):
            await ctx.send("🔒 Só o dono pode fazer isso!")
            return False
        return True
    return commands.check(predicate)

def _membro_ou_dono():
    async def predicate(ctx: commands.Context):
        ok, _ = await _verificar_membro(ctx)
        return ok
    return commands.check(predicate)

# ============================================================
# HELPERS DE API
# ============================================================
def gh_get(endpoint: str, params: dict = None):
    r = requests.get(f"{GH_API}{endpoint}", headers=GH_HEADS, params=params, timeout=12)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}

def gh_post(endpoint: str, body: dict):
    r = requests.post(f"{GH_API}{endpoint}", headers=GH_HEADS, json=body, timeout=12)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}

def gh_patch(endpoint: str, body: dict):
    r = requests.patch(f"{GH_API}{endpoint}", headers=GH_HEADS, json=body, timeout=12)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}

def gh_put(endpoint: str, body: dict):
    r = requests.put(f"{GH_API}{endpoint}", headers=GH_HEADS, json=body, timeout=12)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}

def _data_br(iso: str) -> str:
    try:
        dt = datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return iso[:10]

def _cor_estado(state: str) -> int:
    return {'open': 0x2ECC71, 'closed': 0xE74C3C, 'merged': 0x9B59B6}.get(state, 0x95A5A6)

# ============================================================
# COG
# ============================================================
class GitHubCog(commands.Cog, name="GitHub"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name='gh', invoke_without_command=True)
    async def gh(self, ctx: commands.Context):
        await self._ajuda(ctx)

    # --- CONECTAR / DESCONECTAR ------------------------------------------

    @gh.command(name='conectar')
    async def _conectar(self, ctx: commands.Context, usuario_github: str = None):
        if not usuario_github:
            await ctx.send("❓ Use: `!gh conectar <seu_usuario_github>`")
            return
        usuario_github = usuario_github.strip().lstrip('@')
        s, _ = gh_get(f"/users/{usuario_github}")
        if s == 404:
            await ctx.send(f"❌ Usuário GitHub **{usuario_github}** não encontrado.")
            return
        membro = _e_membro_org(usuario_github)
        _vincular(ctx.author.id, usuario_github)
        if membro:
            embed = discord.Embed(title="✅ Conta vinculada!", color=0x2ECC71)
            embed.add_field(name="Discord", value=ctx.author.display_name, inline=True)
            embed.add_field(name="GitHub",  value=usuario_github,           inline=True)
            embed.add_field(name="Org",     value=f"✅ Membro de **{GH_ORG}**", inline=False)
            embed.set_footer(text="Você pode criar issues, repos e comentar!")
        else:
            embed = discord.Embed(title="🔗 Conta vinculada — acesso limitado", color=0xF39C12)
            embed.add_field(name="Discord", value=ctx.author.display_name, inline=True)
            embed.add_field(name="GitHub",  value=usuario_github,           inline=True)
            embed.add_field(
                name="⚠️ Fora da org",
                value=f"Você não é membro de **{GH_ORG}**.\nApenas leitura. Peça ao dono para te adicionar!",
                inline=False
            )
        await ctx.send(embed=embed)

    @gh.command(name='desconectar')
    async def _desconectar(self, ctx: commands.Context):
        gh_user = _github_do_discord(ctx.author.id)
        if not gh_user:
            await ctx.send("🤷 Você não tem GitHub vinculado!")
            return
        _desvincular(ctx.author.id)
        await ctx.send(f"🔓 Vínculo com **{gh_user}** removido.")

    @gh.command(name='quem')
    async def _quem(self, ctx: commands.Context, membro: discord.Member = None):
        alvo    = membro or ctx.author
        gh_user = _github_do_discord(alvo.id)
        if not gh_user:
            await ctx.send(f"🤷 **{alvo.display_name}** não tem GitHub vinculado.")
            return
        org_ok = _e_membro_org(gh_user)
        await ctx.send(
            f"🔗 **{alvo.display_name}** → `{gh_user}` · "
            f"Org: {'✅ membro' if org_ok else '❌ fora da org'}"
        )

    # --- AJUDA -----------------------------------------------------------

    @gh.command(name='ajuda')
    async def _ajuda(self, ctx: commands.Context):
        gh_user = _github_do_discord(ctx.author.id)
        membro  = gh_user and (_e_dono(ctx) or _e_membro_org(gh_user))
        dono    = _e_dono(ctx)

        embed = discord.Embed(title=f"🐙 GitHub — {GH_ORG}", color=0x24292E)
        embed.add_field(
            name="🔗 Vincular conta",
            value=(
                "`!gh conectar <usuario_github>` — Vincula seu GitHub\n"
                "`!gh desconectar` — Remove o vínculo\n"
                "`!gh quem [@usuario]` — Ver GitHub de alguém"
            ), inline=False
        )
        embed.add_field(
            name="👀 Leitura (todos)",
            value=(
                "`!gh repo [nome]` — Info do repositório\n"
                "`!gh issues [open|closed]` — Listar issues\n"
                "`!gh issue <nº>` — Detalhes de uma issue\n"
                "`!gh prs [open|closed]` — Listar pull requests\n"
                "`!gh pr <nº>` — Detalhes de um PR"
            ), inline=False
        )
        if membro or dono:
            embed.add_field(
                name=f"✏️ Membro da org {GH_ORG}",
                value=(
                    "`!gh nova issue <título> | <descrição>` — Criar issue\n"
                    "`!gh issue <nº> comentar <texto>` — Comentar em issue\n"
                    "`!gh novo repo <nome> | <descrição>` — Criar repositório na org"
                ), inline=False
            )
        if dono:
            embed.add_field(
                name="🔑 Dono (você)",
                value=(
                    "`!gh novo pr <base> | <head> | <título> | [desc]` — Criar PR\n"
                    "`!gh fechar issue <nº>` — Fechar issue\n"
                    "`!gh fechar pr <nº>` — Fechar PR sem merge\n"
                    "`!gh merge <nº> [squash|merge|rebase]` — Merge de PR\n"
                    "`!gh reabrir <issue|pr> <nº>` — Reabrir\n"
                    "`!gh label <nº> <label>` — Adicionar label\n"
                    "`!gh assign <nº> <usuario_github>` — Atribuir responsável\n"
                    "`!gh membros` — Listar membros da org"
                ), inline=False
            )
        status_link = f"✅ Vinculado como `{gh_user}`" if gh_user else "❌ Não vinculado — use `!gh conectar`"
        embed.set_footer(text=f"Seu GitHub: {status_link}")
        await ctx.send(embed=embed)

    # --- REPOSITÓRIO -----------------------------------------------------

    @gh.command(name='repo')
    async def _repo(self, ctx: commands.Context, repo: str = None):
        alvo = f"{GH_ORG}/{repo}" if repo else GH_REPO
        status, data = gh_get(f"/repos/{alvo}")
        if status != 200:
            await ctx.send(f"❌ Repositório `{alvo}` não encontrado. (HTTP {status})")
            return
        embed = discord.Embed(
            title=f"🐙 {data['full_name']}",
            description=data.get('description') or '*Sem descrição*',
            url=data['html_url'], color=0x24292E
        )
        embed.add_field(name="⭐ Stars",          value=str(data.get('stargazers_count', 0)), inline=True)
        embed.add_field(name="🍴 Forks",          value=str(data.get('forks_count', 0)),      inline=True)
        embed.add_field(name="🌿 Branch",         value=data.get('default_branch', 'main'),   inline=True)
        embed.add_field(name="🔓 Visibilidade",   value="Público" if not data.get('private') else "Privado", inline=True)
        embed.add_field(name="🐛 Issues abertas", value=str(data.get('open_issues_count', 0)), inline=True)
        if data.get('language'):
            embed.add_field(name="💻 Linguagem",  value=data['language'], inline=True)
        embed.set_footer(text=f"Criado em {_data_br(data['created_at'])}")
        await ctx.send(embed=embed)

    # --- MEMBROS DA ORG --------------------------------------------------

    @gh.command(name='membros')
    @_apenas_dono()
    async def _membros(self, ctx: commands.Context):
        status, data = gh_get(f"/orgs/{GH_ORG}/members", params={"per_page": 30})
        if status != 200:
            await ctx.send(f"❌ Erro ao buscar membros. (HTTP {status})")
            return
        links    = _carregar_links()
        rev_link = {v: k for k, v in links.items()}
        embed = discord.Embed(title=f"👥 Membros — {GH_ORG}", color=0x24292E)
        linhas = []
        for m in data:
            gh_user     = m['login']
            discord_ref = f"<@{rev_link[gh_user]}>" if gh_user in rev_link else "*(não vinculado no Discord)*"
            linhas.append(f"• `{gh_user}` → {discord_ref}")
        embed.description = "\n".join(linhas) or "Nenhum membro encontrado."
        embed.set_footer(text=f"Total: {len(data)} membros")
        await ctx.send(embed=embed)

    # --- ISSUES ----------------------------------------------------------

    @gh.command(name='issues')
    async def _listar_issues(self, ctx: commands.Context, estado: str = 'open'):
        estado = estado if estado in ('open', 'closed', 'all') else 'open'
        status, data = gh_get(f"/repos/{GH_REPO}/issues", params={"state": estado, "per_page": 10})
        if status != 200:
            await ctx.send(f"❌ Erro ao buscar issues. (HTTP {status})")
            return
        issues = [i for i in data if 'pull_request' not in i]
        if not issues:
            await ctx.send(f"📭 Nenhuma issue **{estado}** no momento.")
            return
        label_estado = {'open': '🟢 Abertas', 'closed': '🔴 Fechadas', 'all': '📋 Todas'}
        embed = discord.Embed(
            title=f"🐛 Issues — {label_estado.get(estado, estado)}",
            url=f"https://github.com/{GH_REPO}/issues",
            color=_cor_estado(estado if estado != 'all' else 'open')
        )
        for issue in issues[:10]:
            labels = ', '.join(l['name'] for l in issue.get('labels', [])) or '—'
            embed.add_field(
                name=f"#{issue['number']} — {issue['title'][:60]}",
                value=(
                    f"👤 {issue['user']['login']} · 🏷️ {labels}\n"
                    f"📅 {_data_br(issue['created_at'])} · [Ver]({issue['html_url']})"
                ), inline=False
            )
        embed.set_footer(text="Use !gh issue <nº> para detalhes.")
        await ctx.send(embed=embed)

    @gh.command(name='issue')
    async def _issue(self, ctx: commands.Context, numero: int = None, acao: str = None, *, texto: str = ''):
        if numero is None:
            await ctx.send("❓ Use: `!gh issue <nº>` ou `!gh issue <nº> comentar <texto>`")
            return
        if acao == 'comentar':
            ok, gh_user = await _verificar_membro(ctx)
            if not ok:
                return
            if not texto:
                await ctx.send("❓ Escreva o comentário: `!gh issue <nº> comentar <texto>`")
                return
            corpo  = f"**{ctx.author.display_name}** (`{gh_user}` via Discord):\n\n{texto}"
            status, data = gh_post(f"/repos/{GH_REPO}/issues/{numero}/comments", {"body": corpo})
            if status == 201:
                await ctx.send(f"💬 Comentário adicionado na issue #{numero}! [Ver]({data['html_url']})")
            else:
                await ctx.send(f"❌ Erro ao comentar. (HTTP {status})")
            return
        status, data = gh_get(f"/repos/{GH_REPO}/issues/{numero}")
        if status == 404:
            await ctx.send(f"❌ Issue #{numero} não encontrada.")
            return
        state = data.get('state', 'open')
        embed = discord.Embed(
            title=f"#{data['number']} — {data['title']}",
            description=(data.get('body') or '*Sem descrição*')[:1000],
            url=data['html_url'], color=_cor_estado(state)
        )
        embed.add_field(name="📊 Estado",      value="🟢 Aberta" if state == 'open' else "🔴 Fechada", inline=True)
        embed.add_field(name="👤 Autor",       value=data['user']['login'],        inline=True)
        embed.add_field(name="💬 Comentários", value=str(data.get('comments', 0)), inline=True)
        if data.get('labels'):
            embed.add_field(name="🏷️ Labels",   value=', '.join(l['name'] for l in data['labels']), inline=True)
        if data.get('assignees'):
            embed.add_field(name="👷 Atribuído", value=', '.join(a['login'] for a in data['assignees']), inline=True)
        embed.set_footer(text=f"Criada em {_data_br(data['created_at'])}")
        await ctx.send(embed=embed)

    # --- CRIAR ISSUE / REPO ----------------------------------------------

    @gh.group(name='nova', invoke_without_command=True)
    async def _nova(self, ctx: commands.Context):
        await ctx.send("❓ Use: `!gh nova issue <título> | <descrição>`")

    @_nova.command(name='issue')
    @_membro_ou_dono()
    async def _nova_issue(self, ctx: commands.Context, *, texto: str):
        if '|' not in texto:
            await ctx.send("❌ Use: `!gh nova issue <título> | <descrição>`")
            return
        titulo, _, desc = texto.partition('|')
        titulo  = titulo.strip()
        desc    = desc.strip()
        gh_user = _github_do_discord(ctx.author.id) or ctx.author.display_name
        rodape  = f"\n\n---\n*Aberta por **{ctx.author.display_name}** (`{gh_user}`) via Discord*"
        status, data = gh_post(f"/repos/{GH_REPO}/issues", {
            "title": titulo,
            "body":  (desc + rodape) if desc else rodape.strip()
        })
        if status == 201:
            embed = discord.Embed(
                title=f"✅ Issue criada — #{data['number']}",
                description=f"**{data['title']}**",
                url=data['html_url'], color=0x2ECC71
            )
            embed.set_footer(text=f"Por {ctx.author.display_name} ({gh_user})")
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Erro ao criar issue. (HTTP {status})\n`{data.get('message', data)}`")

    @gh.group(name='novo', invoke_without_command=True)
    async def _novo(self, ctx: commands.Context):
        await ctx.send("❓ Use: `!gh novo repo <nome> | <descrição>` ou `!gh novo pr <base> | <head> | <título>`")

    @_novo.command(name='repo')
    @_membro_ou_dono()
    async def _novo_repo(self, ctx: commands.Context, *, texto: str):
        partes = [p.strip() for p in texto.split('|')]
        nome   = partes[0].replace(' ', '-').lower()
        desc   = partes[1] if len(partes) > 1 else ''
        if not nome:
            await ctx.send("❌ Use: `!gh novo repo <nome> | <descrição opcional>`")
            return
        status, data = gh_post(f"/orgs/{GH_ORG}/repos", {
            "name": nome, "description": desc, "private": True, "auto_init": True
        })
        if status == 201:
            embed = discord.Embed(
                title="🎉 Repositório criado!",
                description=f"**{data['full_name']}**\n{desc or ''}",
                url=data['html_url'], color=0x2ECC71
            )
            embed.add_field(name="🔒 Visibilidade", value="Privado",                          inline=True)
            embed.add_field(name="🌿 Branch",       value=data.get('default_branch', 'main'), inline=True)
            embed.set_footer(text=f"Criado por {ctx.author.display_name}")
            await ctx.send(embed=embed)
        else:
            msg = data.get('message', str(data))
            if 'already exists' in msg:
                await ctx.send(f"❌ Já existe um repo chamado `{nome}` na org!")
            else:
                await ctx.send(f"❌ Erro ao criar repositório. (HTTP {status})\n`{msg}`")

    # --- PR CRUD ---------------------------------------------------------

    @_novo.command(name='pr')
    @_apenas_dono()
    async def _novo_pr(self, ctx: commands.Context, *, texto: str):
        partes = [p.strip() for p in texto.split('|')]
        if len(partes) < 3:
            await ctx.send("❌ Use: `!gh novo pr <base> | <head> | <título> | [desc]`")
            return
        base, head, titulo = partes[0], partes[1], partes[2]
        desc = partes[3] if len(partes) > 3 else ''
        status, data = gh_post(f"/repos/{GH_REPO}/pulls", {
            "title": titulo, "head": head, "base": base, "body": desc
        })
        if status == 201:
            embed = discord.Embed(
                title=f"✅ PR criado — #{data['number']}",
                description=f"**{data['title']}**\n`{head}` → `{base}`",
                url=data['html_url'], color=0x2ECC71
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Erro ao criar PR. (HTTP {status})\n`{data.get('message', data)}`")

    @gh.command(name='prs')
    async def _listar_prs(self, ctx: commands.Context, estado: str = 'open'):
        estado = estado if estado in ('open', 'closed', 'all') else 'open'
        status, data = gh_get(f"/repos/{GH_REPO}/pulls", params={"state": estado, "per_page": 10})
        if status != 200:
            await ctx.send(f"❌ Erro ao buscar PRs. (HTTP {status})")
            return
        if not data:
            await ctx.send(f"📭 Nenhum PR **{estado}** no momento.")
            return
        label_estado = {'open': '🟢 Abertos', 'closed': '🔴 Fechados', 'all': '📋 Todos'}
        embed = discord.Embed(
            title=f"🔀 Pull Requests — {label_estado.get(estado, estado)}",
            url=f"https://github.com/{GH_REPO}/pulls",
            color=_cor_estado(estado if estado != 'all' else 'open')
        )
        for pr in data[:10]:
            embed.add_field(
                name=f"#{pr['number']} — {pr['title'][:60]}",
                value=(
                    f"👤 {pr['user']['login']} · `{pr['head']['ref']}` → `{pr['base']['ref']}`\n"
                    f"📅 {_data_br(pr['created_at'])} · [Ver]({pr['html_url']})"
                ), inline=False
            )
        embed.set_footer(text="Use !gh pr <nº> para detalhes.")
        await ctx.send(embed=embed)

    @gh.command(name='pr')
    async def _pr(self, ctx: commands.Context, numero: int = None):
        if numero is None:
            await ctx.send("❓ Use: `!gh pr <nº>`")
            return
        status, data = gh_get(f"/repos/{GH_REPO}/pulls/{numero}")
        if status == 404:
            await ctx.send(f"❌ PR #{numero} não encontrado.")
            return
        merged = data.get('merged', False)
        state  = data.get('state', 'open')
        embed  = discord.Embed(
            title=f"#{data['number']} — {data['title']}",
            description=(data.get('body') or '*Sem descrição*')[:1000],
            url=data['html_url'],
            color=0x9B59B6 if merged else _cor_estado(state)
        )
        estado_str = "🟣 Mergeado" if merged else ("🟢 Aberto" if state == 'open' else "🔴 Fechado")
        embed.add_field(name="📊 Estado",   value=estado_str, inline=True)
        embed.add_field(name="👤 Autor",    value=data['user']['login'], inline=True)
        embed.add_field(name="🔀 Branches", value=f"`{data['head']['ref']}` → `{data['base']['ref']}`", inline=True)
        embed.add_field(name="✅ Commits",  value=str(data.get('commits','—')), inline=True)
        embed.add_field(name="📝 Arquivos", value=str(data.get('changed_files','—')), inline=True)
        embed.add_field(name="±  Linhas",   value=f"+{data.get('additions',0)} / -{data.get('deletions',0)}", inline=True)
        embed.set_footer(text=f"Aberto em {_data_br(data['created_at'])}")
        await ctx.send(embed=embed)

    @gh.command(name='merge')
    @_apenas_dono()
    async def _merge(self, ctx: commands.Context, numero: int, metodo: str = 'squash'):
        metodo = metodo if metodo in ('squash','merge','rebase') else 'squash'
        s, pr  = gh_get(f"/repos/{GH_REPO}/pulls/{numero}")
        if s == 404:
            await ctx.send(f"❌ PR #{numero} não encontrado.")
            return
        if pr.get('state') != 'open':
            await ctx.send(f"❌ PR #{numero} não está aberto.")
            return
        status, data = gh_put(f"/repos/{GH_REPO}/pulls/{numero}/merge", {
            "merge_method":   metodo,
            "commit_title":   pr['title'],
            "commit_message": f"Merge via Discord por {ctx.author.display_name}",
        })
        if status == 200:
            embed = discord.Embed(
                title=f"🟣 PR #{numero} mergeado!",
                description=f"**{pr['title']}** · método: `{metodo}`",
                url=pr['html_url'], color=0x9B59B6
            )
            embed.set_footer(text=f"Por {ctx.author.display_name}")
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Erro. (HTTP {status})\n`{data.get('message', data)}`")

    @gh.command(name='fechar')
    @_apenas_dono()
    async def _fechar(self, ctx: commands.Context, tipo: str, numero: int):
        if tipo.lower() not in ('issue','pr'):
            await ctx.send("❓ Use: `!gh fechar issue <nº>` ou `!gh fechar pr <nº>`")
            return
        status, data = gh_patch(f"/repos/{GH_REPO}/issues/{numero}", {"state": "closed"})
        if status == 200:
            await ctx.send(f"🔴 #{numero} fechado! [Ver]({data['html_url']})")
        elif status == 404:
            await ctx.send(f"❌ #{numero} não encontrado.")
        else:
            await ctx.send(f"❌ Erro. (HTTP {status})")

    @gh.command(name='reabrir')
    @_apenas_dono()
    async def _reabrir(self, ctx: commands.Context, tipo: str, numero: int):
        if tipo.lower() not in ('issue','pr'):
            await ctx.send("❓ Use: `!gh reabrir issue <nº>` ou `!gh reabrir pr <nº>`")
            return
        status, data = gh_patch(f"/repos/{GH_REPO}/issues/{numero}", {"state": "open"})
        if status == 200:
            await ctx.send(f"🟢 #{numero} reaberto! [Ver]({data['html_url']})")
        else:
            await ctx.send(f"❌ Erro. (HTTP {status})")

    @gh.command(name='label')
    @_apenas_dono()
    async def _label(self, ctx: commands.Context, numero: int, *, label: str):
        s, issue = gh_get(f"/repos/{GH_REPO}/issues/{numero}")
        if s == 404:
            await ctx.send(f"❌ #{numero} não encontrado.")
            return
        labels_atuais = [l['name'] for l in issue.get('labels', [])]
        novas  = list(set(labels_atuais + [label.strip()]))
        status, data = gh_patch(f"/repos/{GH_REPO}/issues/{numero}", {"labels": novas})
        if status == 200:
            todas = ', '.join(f"`{l['name']}`" for l in data.get('labels', []))
            await ctx.send(f"🏷️ Label `{label}` adicionada ao #{numero}! Labels: {todas}")
        else:
            await ctx.send(f"❌ Erro. (HTTP {status})")

    @gh.command(name='assign')
    @_apenas_dono()
    async def _assign(self, ctx: commands.Context, numero: int, *, usuario: str):
        usuario = usuario.strip().lstrip('@')
        status, data = gh_patch(f"/repos/{GH_REPO}/issues/{numero}", {"assignees": [usuario]})
        if status == 200:
            atribuidos = ', '.join(a['login'] for a in data.get('assignees', []))
            await ctx.send(f"👷 #{numero} atribuído para: **{atribuidos or usuario}**")
        else:
            await ctx.send(f"❌ Erro. (HTTP {status})")

    # --- ERRO GENERICO ---------------------------------------------------

    @gh.error
    async def _gh_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CheckFailure):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Faltou um argumento! Use `!gh ajuda`.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Argumento inválido. Use `!gh ajuda`.")
        else:
            print(f"[GitHub Cog] Erro: {error}")
            await ctx.send("❌ Deu um erro aqui. Tenta de novo!")


# ============================================================
# SETUP
# ============================================================
async def setup(bot: commands.Bot):
    await bot.add_cog(GitHubCog(bot))

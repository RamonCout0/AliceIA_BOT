# 🤖 Alice 1.7 — Arquitetura Redis

## Por que funciona (e o ngrok/tunnel não funcionava)

A arquitetura antiga tentava fazer a **nuvem acessar seu PC** — o que exige port forwarding, IP fixo, liberar firewall do roteador, etc. Qualquer coisa no caminho quebrava.

A nova arquitetura **inverte isso**: seu PC faz chamadas HTTP para fora (para o Redis na nuvem). Isso sempre funciona, porque o seu PC já acessa a internet normalmente.

```
Usuário no Discord
        ↓
   bot.py (Shardclaud)  →  RPUSH  →  Redis (Upstash, nuvem)
                                              ↑
                                    cliente_pc.py (seu PC)
                                    faz BLPOP → chama Ollama local
                                    → publica resposta no Redis
                                              ↓
   bot.py recebe a resposta  ←  GET  ←  Redis
        ↓
   Usuário recebe a resposta
```

**Quando PC desliga:** o heartbeat para, a chave `alice:online` expira em 30s, e o bot entra no modo repouso automaticamente.

---

## 📁 Estrutura do Projeto

```
alice-1.6/
├── cogs/
│   └── github_cog.py          # Integração com GitHub
├── config/
│   ├── config_bot.json        # Configuração do bot (Shardclaud)
│   ├── config_pc.json         # Configuração do cliente (seu PC)
│   └── personalidade.json     # Tom e estilo da Alice
├── core/
│   ├── bot.py                 # Bot Discord 24/7
│   └── cliente_pc.py          # Processa pedidos com Ollama
├── historico.json             # Gerado automaticamente (Shardclaud)
├── links_github.json          # Vínculos Discord-GitHub (gerado automaticamente)
├── alice_log.txt              # Log do cliente (seu PC)
├── requirements.txt           # Dependências Python
└── README.md                  # Este arquivo
```

---

## ⚙️ Setup passo a passo

### PASSO 1 — Criar banco Redis gratuito (Upstash)

1. Acesse **https://upstash.com** e crie uma conta (gratuita)
2. Clique em **"Create Database"**
3. Dê um nome (ex: `alice`), escolha a região mais próxima
4. Após criar, vá em **"REST API"**
5. Copie a **"UPSTASH_REDIS_REST_URL"** e o **"UPSTASH_REDIS_REST_TOKEN"**

> 💡 O plano gratuito do Upstash tem 10.000 comandos/dia — mais que suficiente para um bot de Discord.

---

### PASSO 2 — Configurar os arquivos

**`config/config_bot.json`** (vai pro Shardclaud):
```json
{
  "discord_token": "seu_token_discord",
  "upstash_redis_url":   "https://seu-banco.upstash.io",
  "upstash_redis_token": "seu_token_upstash"
}
```

**`config/config_pc.json`** (fica no seu PC):
```json
{
  "upstash_redis_url":   "https://seu-banco.upstash.io",
  "upstash_redis_token": "seu_token_upstash",
  "ollama_model": "llama3.2:3b"
}
```

> Ambos usam os **mesmos valores** do Upstash!

---

### PASSO 3 — Configurar Ollama no PC

```bash
# Instalar um modelo (escolha um):
ollama pull llama3.2:3b       # Rápido, leve (~2GB RAM)
ollama pull llama3.1:8b       # Melhor qualidade (~8GB RAM)
ollama pull mistral:7b        # Bom equilíbrio (~5GB RAM)

# Iniciar o Ollama (já inicia automaticamente no Windows normalmente)
ollama serve
```

---

### PASSO 4 — Rodar o cliente no PC

```bash
# Instalar dependência (só requests — sem precisar de redis client!)
pip install -r requirements.txt

# Rodar
python core/cliente_pc.py
```

Você vai ver algo como:
```
[10:23:01] Alice — Cliente PC iniciado
[10:23:01] Ollama OK! Modelos disponíveis: ['llama3.2:3b']
[10:23:01] Heartbeat iniciado. PC está marcado como ONLINE no Discord.
[10:23:01] Aguardando pedidos...
```

---

### PASSO 5 — Subir o bot no Shardclaud

```bash
# Instalar dependências
pip install discord.py requests beautifulsoup4

# Copiar pro Shardclaud:
# bot.py, config_bot.json, personalidade.json

# Rodar
python bot.py
```

---

## 💬 Como usar no Discord

| O que fazer | Exemplo |
|---|---|
| Conversar | `@Alice oi, como vai?` |
| Dúvida de código | `@Alice como fazer um decorator em Python?` |
| Debugar erro | `@Alice tô tendo: TypeError: 'NoneType' object is not subscriptable` |
| Ver status | `!status` |
| Limpar histórico | `!reset` |
| Ver qtd de msgs | `!hist` |
| Diversão | `!fun piada` / `!fun dado` / `!fun moeda` |

---

## 😴 Modo Repouso

Quando o `cliente_pc.py` for fechado ou o PC desligar, em até **30 segundos** o bot entra em modo repouso e responde:

> *"😴 Modo Repouso — Meu PC tá desligado agora. Volta mais tarde! 💤"*

Quando você abre o `cliente_pc.py` de novo, o heartbeat atualiza o Redis e o bot volta a funcionar normalmente em segundos. **Não precisa reiniciar nada no Shardclaud.**

---

## 📚 Sistema de Histórico

- Cada usuário tem histórico individual e privado
- Salvo em `historico.json` no Shardclaud
- **Limpeza automática** quando passa de 30 mensagens:
  - Filtra saudações, "ok", "obrigado" e respostas triviais
  - Preserva sempre as 15 mensagens mais recentes
  - Mantém dúvidas de programação e conversas com substância

---

## 🔒 Segurança

- **Nunca** suba `config_bot.json` ou `config_pc.json` para o GitHub
- Adicione ao `.gitignore`: `config_bot.json`, `config_pc.json`, `historico.json`, `*.log`
- O token hardcoded que existia no bot anterior foi **removido** — gere um novo em https://discord.com/developers
- O Redis do Upstash usa HTTPS com token — comunicação criptografada

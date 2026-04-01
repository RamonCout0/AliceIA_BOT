# 🤖 Alice — Bot Discord com IA Local via Ollama

Bot sociável para Discord que usa o **Ollama no seu PC** como cérebro.
Fica online 24/7 no Shardclaud, mas a IA roda no seu hardware.

---

## 📁 Arquivos

| Arquivo | Onde roda | Função |
|---|---|---|
| `bot.py` | Shardclaud (nuvem) | Bot principal 24/7 |
| `servidor_local.py` | Seu PC | Recebe histórico, health check |
| `config.json` | Shardclaud | Configurações (IP, token, etc.) |
| `personalidade.json` | Shardclaud | Tom e estilo da Alice |
| `historico.json` | Shardclaud | Gerado automaticamente |
| `historico_local.json` | Seu PC | Gerado pelo servidor_local.py |

---

## ⚙️ Pré-requisitos

### No seu PC:
- [Ollama](https://ollama.com) instalado e rodando
- Python 3.10+
- Pacotes: `pip install flask`
- Portas abertas no roteador: **11434** (Ollama) e **5001** (servidor local)

### No Shardclaud:
- Python 3.10+
- Pacotes: `pip install discord.py requests beautifulsoup4`

---

## 🚀 Setup Passo a Passo

### 1. Configurar o Ollama no PC

```bash
# Instalar o modelo (escolha um):
ollama pull llama3.2:3b      # Mais rápido, leve
ollama pull llama3.1:8b      # Melhor qualidade
ollama pull mistral:7b       # Bom equilíbrio

# Rodar o Ollama acessível na rede (importante!):
OLLAMA_HOST=0.0.0.0 ollama serve
# No Windows PowerShell:
$env:OLLAMA_HOST="0.0.0.0"; ollama serve
```

### 2. Descobrir seu IP público

Acesse: https://whatismyip.com  
Copie o IP e coloque em `config.json` no campo `ollama_ip`.

### 3. Liberar portas no Windows Firewall

No PowerShell (como Administrador):
```powershell
# Porta do Ollama
netsh advfirewall firewall add rule name="Ollama" dir=in action=allow protocol=TCP localport=11434

# Porta do servidor local da Alice
netsh advfirewall firewall add rule name="Alice Local" dir=in action=allow protocol=TCP localport=5001
```

### 4. Configurar redirecionamento no roteador

No painel do seu roteador, crie regras de **Port Forwarding**:
- Porta 11434 → IP local do seu PC (ex: 192.168.1.100)
- Porta 5001  → IP local do seu PC

> 💡 Para encontrar seu IP local: no Windows, execute `ipconfig` no terminal.

### 5. Preencher o config.json

```json
{
  "discord_token": "token_do_bot_aqui",
  "ollama_ip": "seu_ip_publico_aqui",
  "ollama_model": "llama3.2:3b"
}
```

### 6. Rodar o servidor local no PC

```bash
python servidor_local.py
```
Deixe esse processo rodando sempre que quiser a Alice ativa.

### 7. Subir o bot no Shardclaud

```bash
pip install discord.py requests beautifulsoup4
python bot.py
```

---

## 💬 Como usar no Discord

| Ação | Exemplo |
|---|---|
| Conversar | `@Alice como vai?` |
| Dúvida de código | `@Alice como fazer uma requisição GET em Python?` |
| Erro de programação | `@Alice tô tendo esse erro: AttributeError...` |
| Resetar histórico | `!reset` |
| Ver status | `!status` |
| Brincadeiras | `!fun piada` / `!fun dado` / `!fun moeda` |

---

## 😴 Modo Repouso

Quando seu PC estiver desligado, a Alice responderá automaticamente:

> *"Ei, tô em modo repouso agora! Meu PC tá desligado no momento. Volta mais tarde! 💤"*

Quando o PC voltar, ela retoma normalmente — sem precisar reiniciar nada.

---

## 📚 Sistema de Histórico

- Cada usuário tem seu histórico individual salvo em `historico.json`
- O histórico é enviado ao seu PC via `servidor_local.py` a cada conversa
- **Limpeza automática**: quando um usuário passa de 30 mensagens, o bot filtra as mensagens curtas/triviais e mantém as mais relevantes (dúvidas reais, programação)
- As 15 mensagens mais recentes são **sempre** preservadas
- Você pode ver o histórico de um usuário acessando: `http://localhost:5001/historico/ID_DO_USUARIO`

---

## 🔒 Segurança

- **NUNCA** suba o `config.json` com seu token para o GitHub
- Adicione `config.json` e `historico.json` ao `.gitignore`
- O token do Discord que estava hardcoded no bot anterior foi removido — gere um novo em https://discord.com/developers

---

## 🛠️ Alternativa sem port forwarding: Cloudflare Tunnel

Se não quiser mexer no roteador, use o Cloudflare Tunnel:

```bash
# Instale o cloudflared e rode:
cloudflared tunnel --url http://localhost:11434
cloudflared tunnel --url http://localhost:5001
```

O tunnel vai gerar URLs públicas que você coloca no `config.json`.

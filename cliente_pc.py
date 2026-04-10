# ============================================================
#  ALICE — cliente_pc.py
#  Roda no: SEU PC
#  Função: Fica ouvindo a fila Redis e processa com Ollama local
# ============================================================
#
#  Instalar:  pip install requests
#  Rodar:     python cliente_pc.py
#  Deixar rodando enquanto quiser que a Alice funcione!
# ============================================================

import requests
import json
import os
import time
import threading
import datetime

# ============================================================
# CONFIG
# ============================================================
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config_pc.json')

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

REDIS_URL    = cfg['upstash_redis_url']
REDIS_TOKEN  = cfg['upstash_redis_token']
OLLAMA_URL   = cfg.get('ollama_url', 'http://localhost:11434')
OLLAMA_MODEL = cfg.get('ollama_model', 'llama3.2:3b')
HEARTBEAT_S  = cfg.get('heartbeat_segundos', 20)

# ============================================================
# REDIS
# ============================================================
_HEADERS = {
    "Authorization": f"Bearer {REDIS_TOKEN}",
    "Content-Type":  "application/json",
}

def redis_cmd(cmd: list, timeout: int = 35) -> dict | None:
    """Executa um comando no Redis via Upstash REST API."""
    try:
        r = requests.post(REDIS_URL, headers=_HEADERS, json=cmd, timeout=timeout)
        return r.json()
    except Exception as e:
        log(f"[Redis] Erro: {e}")
        return None

def pop_fila() -> dict | None:
    """
    Tenta retirar um item da fila alice:fila.
    Usa BLPOP com timeout de 5s (blocking pop — não ocupa CPU).
    Retorna o payload decodificado ou None.
    """
    r = redis_cmd(["BLPOP", "alice:fila", "5"], timeout=10)
    if not r or not r.get("result"):
        return None
    try:
        # BLPOP retorna [nome_da_lista, valor]
        raw = r["result"]
        if isinstance(raw, list):
            raw = raw[1]
        return json.loads(raw)
    except Exception as e:
        log(f"[Fila] Erro ao parsear payload: {e}")
        return None

def publicar_resposta(request_id: str, resposta: str):
    """Salva a resposta no Redis com TTL de 120s."""
    redis_cmd(["SET", f"alice:resp:{request_id}", resposta, "EX", "120"])

# ============================================================
# HEARTBEAT — avisa o bot que o PC está online
# ============================================================
def heartbeat_loop():
    """Atualiza alice:online a cada HEARTBEAT_S segundos."""
    while True:
        try:
            redis_cmd(["SET", "alice:online", "1", "EX", "30"])
        except Exception as e:
            log(f"[Heartbeat] Erro: {e}")
        time.sleep(HEARTBEAT_S)

# ============================================================
# OLLAMA
# ============================================================
def chamar_ollama(system: str, mensagens: list) -> str:
    """
    Chama o Ollama local com o system prompt e histórico de mensagens.
    Retorna o texto da resposta.
    """
    payload = {
        "model":    OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}] + mensagens,
        "stream":   False,
        "options":  {
            "num_predict": 900,
            "temperature": 0.72,
            "top_p":       0.9,
        }
    }
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        timeout=180   # Modelos maiores podem demorar
    )
    r.raise_for_status()
    return r.json()["message"]["content"].strip()

# ============================================================
# LOG
# ============================================================
LOG_PATH = os.path.join(BASE_DIR, 'alice_log.txt')

def log(msg: str):
    agora = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    linha = f"[{agora}] {msg}"
    print(linha)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(linha + "\n")
    except Exception:
        pass

# ============================================================
# LOOP PRINCIPAL
# ============================================================
def processar(payload: dict):
    rid      = payload.get("id", "sem-id")
    uid      = payload.get("user_id", "?")
    username = payload.get("username", "Usuário")
    system   = payload.get("system", "")
    mensagens = payload.get("mensagens", [])

    log(f"Processando pedido de {username} (uid={uid}) | id={rid}")

    try:
        resposta = chamar_ollama(system, mensagens)
        publicar_resposta(rid, resposta)
        log(f"Resposta enviada para {username} ({len(resposta)} chars)")
    except requests.exceptions.ConnectionError:
        log(f"[Ollama] Ollama não está rodando! Inicie com: ollama serve")
        # Publica mensagem de erro para o bot não ficar travado
        publicar_resposta(rid, "⚠️ Ollama tá desligado no meu PC agora! Abre ele lá e tenta de novo.")
    except requests.exceptions.Timeout:
        log(f"[Ollama] Timeout ao processar pedido de {username}")
        publicar_resposta(rid, "⏳ Demorou demais aqui no meu PC... Tenta de novo!")
    except Exception as e:
        log(f"[Ollama] Erro inesperado: {e}")
        publicar_resposta(rid, "❌ Deu um erro aqui no meu PC. Tenta de novo em instantes!")

def main():
    log("=" * 50)
    log(f"  Alice — Cliente PC iniciado")
    log(f"  Ollama: {OLLAMA_URL}")
    log(f"  Modelo: {OLLAMA_MODEL}")
    log(f"  Redis:  {REDIS_URL[:35]}...")
    log("=" * 50)

    # Verifica se Ollama está acessível
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        modelos = [m['name'] for m in r.json().get('models', [])]
        log(f"Ollama OK! Modelos disponíveis: {modelos}")
        if OLLAMA_MODEL not in modelos and not any(OLLAMA_MODEL in m for m in modelos):
            log(f"⚠️  Modelo '{OLLAMA_MODEL}' não encontrado! Execute: ollama pull {OLLAMA_MODEL}")
    except Exception:
        log("⚠️  Ollama não está respondendo! Certifique-se de rodar: ollama serve")
        log("    Continuando mesmo assim — vai tentar novamente a cada pedido...")

    # Inicia heartbeat em thread separada
    hb = threading.Thread(target=heartbeat_loop, daemon=True)
    hb.start()
    log("Heartbeat iniciado. PC está marcado como ONLINE no Discord.")
    log("Aguardando pedidos...")

    # Loop principal de processamento
    while True:
        try:
            payload = pop_fila()
            if payload:
                processar(payload)
        except KeyboardInterrupt:
            log("Encerrando cliente... PC ficará OFFLINE no Discord em ~30 segundos.")
            break
        except Exception as e:
            log(f"[Loop] Erro inesperado: {e}")
            time.sleep(3)

if __name__ == '__main__':
    main()

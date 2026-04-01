# ============================================================
#   SERVIDOR LOCAL DA ALICE — Rode no SEU PC
#   Responsabilidades:
#   1. Receber o histórico do bot (Shardclaud) e salvar localmente
#   2. Servir como ponto de verificação para o bot saber se o PC tá online
#   3. Expor o Ollama na rede (o Ollama já faz isso na porta 11434)
# ============================================================
#
#   COMO USAR:
#   1. Instale Flask:    pip install flask
#   2. Execute:         python servidor_local.py
#   3. Deixe rodando enquanto quiser que a Alice funcione
#
#   PORTA PADRÃO: 5001
#   Certifique-se de liberar essa porta no firewall do Windows
#   e configurar o redirecionamento de porta no roteador!
# ============================================================

from flask import Flask, request, jsonify
import json
import os
import datetime

app = Flask(__name__)

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
HISTORICO_LOCAL = os.path.join(BASE_DIR, 'historico_local.json')
LOG_PATH        = os.path.join(BASE_DIR, 'sync_log.txt')

def log(msg: str):
    agora = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    linha = f"[{agora}] {msg}"
    print(linha)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(linha + "\n")
    except Exception:
        pass

# ──────────────────────────────────────────────
# ROTA: Recebe o histórico do bot e salva no PC
# ──────────────────────────────────────────────
@app.route('/sync_historico', methods=['POST'])
def sync_historico():
    try:
        dados = request.get_json(force=True)
        if not isinstance(dados, dict):
            return jsonify({'status': 'erro', 'msg': 'Payload inválido'}), 400

        with open(HISTORICO_LOCAL, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)

        total_msgs = sum(len(v) for v in dados.values())
        log(f"Histórico sincronizado: {len(dados)} usuários, {total_msgs} mensagens.")
        return jsonify({'status': 'ok', 'usuarios': len(dados), 'mensagens': total_msgs})

    except Exception as e:
        log(f"Erro ao sincronizar histórico: {e}")
        return jsonify({'status': 'erro', 'msg': str(e)}), 500

# ──────────────────────────────────────────────
# ROTA: Health check — o bot usa isso pra saber
#        se o PC / Ollama tá acessível
# ──────────────────────────────────────────────
@app.route('/', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'servidor': 'Alice Local',
        'hora': datetime.datetime.now().isoformat()
    })

# ──────────────────────────────────────────────
# ROTA: Ver histórico de um usuário específico
# ──────────────────────────────────────────────
@app.route('/historico/<user_id>', methods=['GET'])
def ver_historico_usuario(user_id: str):
    try:
        with open(HISTORICO_LOCAL, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        msgs = dados.get(str(user_id), [])
        return jsonify({'user_id': user_id, 'mensagens': len(msgs), 'historico': msgs})
    except FileNotFoundError:
        return jsonify({'status': 'sem histórico ainda'}), 404

# ──────────────────────────────────────────────
# ROTA: Resumo geral do histórico
# ──────────────────────────────────────────────
@app.route('/historico', methods=['GET'])
def resumo_historico():
    try:
        with open(HISTORICO_LOCAL, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        resumo = {
            uid: len(msgs)
            for uid, msgs in dados.items()
        }
        return jsonify({
            'total_usuarios': len(resumo),
            'total_mensagens': sum(resumo.values()),
            'por_usuario': resumo
        })
    except FileNotFoundError:
        return jsonify({'status': 'sem histórico ainda'}), 404

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 55)
    print("  🤖 Servidor Local da Alice")
    print("  Porta: 5001")
    print("  Acesso: http://0.0.0.0:5001")
    print()
    print("  Rotas disponíveis:")
    print("    GET  /                   → Health check")
    print("    POST /sync_historico     → Recebe histórico do bot")
    print("    GET  /historico          → Resumo do histórico")
    print("    GET  /historico/<userid> → Histórico de um usuário")
    print()
    print("  ⚠️  Mantenha este processo rodando enquanto usar o bot!")
    print("  ⚠️  Libere a porta 5001 no Windows Defender Firewall.")
    print("=" * 55)

    log("Servidor local iniciado.")
    app.run(host='0.0.0.0', port=5001, debug=False)

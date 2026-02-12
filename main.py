import time
import sys
from core.visao import capturar_tela
from core.cerebro import pensar
from core.controle import CorpoAlice

def main():
    print("--- INICIANDO SISTEMA ---")
    
    try:
        alice_corpo = CorpoAlice()
        print("✅ Controle conectado.")
    except Exception as e:
        print(f"❌ ERRO CRÍTICO NO CONTROLE: {e}")
        return

    historico = [] 
    
    print("🤖 Alice pronta. Entrando no loop infinito em 3 segundos...")
    time.sleep(3)

    loop_count = 0

    while True:
        loop_count += 1
        print(f"\n--- RODADA {loop_count} ---")
        
        # 1. DEBUG VISÃO
        print("1. Olhos: Tentando capturar tela...")
        try:
            frame = capturar_tela()
            print("   ✅ Imagem capturada com sucesso.")
        except Exception as e:
            print(f"   ❌ ERRO DE VISÃO: {e}")
            print("   DICA: Verifique se o MSS está achando o monitor 1.")
            time.sleep(5)
            continue # Pula para a próxima tentativa

        # 2. DEBUG CÉREBRO
        print("2. Cérebro: Enviando para o Ollama (Pode demorar se for a 1ª vez)...")
        start_time = time.time()
        try:
            contexto = " -> ".join(historico[-3:])
            decisao_json = pensar(frame, contexto)
            tempo_gasto = time.time() - start_time
            print(f"   ✅ Ollama respondeu em {tempo_gasto:.2f} segundos.")
            print(f"   🧠 Conteúdo: {decisao_json}")
        except Exception as e:
            print(f"   ❌ ERRO NO OLLAMA: {e}")
            print("   DICA: O comando 'ollama serve' está rodando?")
            time.sleep(5)
            continue

        # 3. DEBUG CORPO
        print("3. Corpo: Executando ação física...")
        try:
            pensamento = alice_corpo.agir(decisao_json)
            print(f"   ✅ Ação executada: {pensamento}")
        except Exception as e:
            print(f"   ❌ ERRO DE MOVIMENTO: {e}")

        historico.append(pensamento)
        if len(historico) > 5: historico.pop(0)

        print("💤 Aguardando 1 segundo...")
        time.sleep(1)

if __name__ == "__main__":
    main()
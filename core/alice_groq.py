import os
import time
import json
import threading
import base64
import re
import vgamepad as vg
import mss
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from groq import Groq

# ==============================================================================
# 1. CONFIGURAÇÕES GROQ
# ==============================================================================
load_dotenv()
API_KEY = os.getenv('GROQ_API_KEY')

if not API_KEY:
    print("❌ ERRO: Faltando GROQ_API_KEY no .env")
    exit()

client = Groq(api_key=API_KEY)

CONFIG = {
    # Modelo mais potente de visão da Groq (O 'Cérebro Grande')
    "MODELO": "llama-3.2-90b-vision-preview", 
    "MONITOR": {"top": 0, "left": 0, "width": 1920, "height": 1080}, # Ajuste sua resolução
    "HISTORICO_LEN": 10,
    "FPS_IA": 2.0 # Intervalo (segundos)
}

# ==============================================================================
# 2. SISTEMA DE MACROS (IGUAL AO ANTERIOR - O CORPO INTELIGENTE)
# ==============================================================================
class MacroEngine:
    def __init__(self, gamepad):
        self.gp = gamepad
        self.stop_event = threading.Event()
        self.current_thread = None

    def executar(self, comando, duracao=1.0):
        # Para a ação anterior
        self.stop_event.set()
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread.join()
        
        self.stop_event.clear()
        
        # Inicia a nova ação
        if comando == "ANDAR_DIREITA":
            self.current_thread = threading.Thread(target=self._andar, args=(32000, duracao))
        elif comando == "ANDAR_ESQUERDA":
            self.current_thread = threading.Thread(target=self._andar, args=(-32000, duracao))
        elif comando == "PULAR_DIREITA":
            self.current_thread = threading.Thread(target=self._pular_andar, args=(32000, duracao))
        elif comando == "MINERAR_FRENTE":
            self.current_thread = threading.Thread(target=self._minerar_parede, args=("frente", duracao))
        elif comando == "MINERAR_BAIXO":
            self.current_thread = threading.Thread(target=self._minerar_parede, args=("baixo", duracao))
        elif comando == "ATACAR":
            self.current_thread = threading.Thread(target=self._combate, args=(duracao,))
        
        if self.current_thread:
            self.current_thread.start()

    # --- MOVIMENTOS FÍSICOS ---
    def _andar(self, direcao, tempo):
        start = time.time()
        while time.time() - start < tempo and not self.stop_event.is_set():
            self.gp.left_joystick(x_value=direcao, y_value=0)
            self.gp.update()
            time.sleep(0.05)
        self.gp.reset(); self.gp.update()

    def _pular_andar(self, direcao, tempo):
        start = time.time()
        while time.time() - start < tempo and not self.stop_event.is_set():
            self.gp.left_joystick(x_value=direcao, y_value=0)
            self.gp.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
            self.gp.update()
            time.sleep(0.3)
            self.gp.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
            self.gp.update()
            time.sleep(0.1)
        self.gp.reset(); self.gp.update()

    def _minerar_parede(self, tipo, tempo):
        """RESOLVE O PROBLEMA DA PAREDE"""
        start = time.time()
        self.gp.right_trigger(value=255) # Segura ataque/minerar
        
        while time.time() - start < tempo and not self.stop_event.is_set():
            if tipo == "frente":
                # Mira na frente e mexe um pouco pra cima/baixo pra abrir passagem
                self.gp.right_joystick(x_value=32000, y_value=15000)
                self.gp.update()
                time.sleep(0.2)
                self.gp.right_joystick(x_value=32000, y_value=-15000)
                self.gp.update()
                time.sleep(0.2)
            elif tipo == "baixo":
                self.gp.right_joystick(x_value=0, y_value=-32000)
                self.gp.update()
                time.sleep(0.1)
        self.gp.reset(); self.gp.update()

    def _combate(self, tempo):
        start = time.time()
        while time.time() - start < tempo and not self.stop_event.is_set():
            self.gp.right_trigger(value=255)
            self.gp.right_joystick(x_value=32000, y_value=0)
            self.gp.update()
            time.sleep(0.1)
        self.gp.reset(); self.gp.update()

# ==============================================================================
# 3. CÉREBRO GROQ (Llama 3.2 Vision)
# ==============================================================================
PROMPT_MESTRE = """
Você é a Alice, IA jogando Terraria.
Analise a imagem e o histórico. Decida o MACRO correto.

REGRAS:
1. SE vir uma parede bloqueando o rosto -> USE "MINERAR_FRENTE".
2. SE vir inimigos -> USE "ATACAR".
3. SE o caminho estiver livre -> USE "ANDAR_DIREITA".
4. SE for um degrau pequeno -> USE "PULAR_DIREITA".

Responda APENAS JSON:
{
    "analise": "Vejo parede de terra alta.",
    "comando": "MINERAR_FRENTE",
    "duracao": 2.5
}
"""

def encode_image(image):
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

class AliceBrain:
    def __init__(self):
        self.historico = []

    def pensar(self, imagem_pil):
        # 1. Prepara imagem
        base64_img = encode_image(imagem_pil)
        
        # 2. Contexto
        contexto_txt = "Histórico:\n" + "\n".join(self.historico[-5:])
        
        try:
            # 3. Chamada Groq
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT_MESTRE + "\n" + contexto_txt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"},
                            },
                        ],
                    }
                ],
                model=CONFIG["MODELO"],
                temperature=0.1, # Preciso e frio
                max_tokens=200
            )
            
            # 4. Limpeza da resposta (Llama as vezes fala demais)
            raw_text = chat_completion.choices[0].message.content
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            else:
                return {"comando": "PARAR", "analise": "JSON Inválido", "duracao": 0}

        except Exception as e:
            print(f"Erro Groq: {e}")
            return {"comando": "PARAR", "analise": "Erro API", "duracao": 0}

    def registrar(self, analise, comando):
        entry = f"Vi: {analise} -> Fiz: {comando}"
        self.historico.append(entry)
        if len(self.historico) > CONFIG["HISTORICO_LEN"]: self.historico.pop(0)

# ==============================================================================
# 4. LOOP PRINCIPAL
# ==============================================================================
def main():
    gamepad = vg.VX360Gamepad()
    corpo = MacroEngine(gamepad)
    cerebro = AliceBrain()
    
    print(f"🚀 ALICE ULTIMATE (GROQ EDITION) - Modelo: {CONFIG['MODELO']}")
    
    with mss.mss() as sct:
        while True:
            cycle_start = time.time()

            # Captura
            sct_img = sct.grab(CONFIG["MONITOR"])
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.thumbnail((720, 720)) # Tamanho bom pro Llama Vision

            # Pensamento
            decisao = cerebro.pensar(img)
            
            cmd = decisao.get("comando", "PARAR")
            dur = float(decisao.get("duracao", 1.0))
            analise = decisao.get("analise", "...")

            print(f"🧠 Groq: {analise} | Macro: {cmd} ({dur}s)")

            # Ação
            corpo.executar(cmd, duracao=dur)
            cerebro.registrar(analise, cmd)

            # Controle de tempo (Groq é rápida, não precisa dormir muito)
            tempo_gasto = time.time() - cycle_start
            sleep_time = max(0, CONFIG["FPS_IA"] - tempo_gasto)
            time.sleep(sleep_time)

if __name__ == "__main__":
    main()
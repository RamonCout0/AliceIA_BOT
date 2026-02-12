import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

print("🔍 Buscando modelos ativos na Groq...")
try:
    models = client.models.list()
    print("\n✅ Modelos Disponíveis:")
    for m in models.data:
        # Filtra apenas modelos que parecem aceitar imagem ou são recentes
        if "vision" in m.id or "llama" in m.id:
            print(f" - ID: {m.id}")
            
    print("\n👉 Copie um ID que tenha 'vision' no nome e cole no seu main.py")
except Exception as e:
    print(f"❌ Erro: {e}")
import os

# factories/model_factory.py lê as chaves na importação do módulo — precisa existir
# uma chave (mesmo que falsa) antes de qualquer teste importar código do agente.
os.environ.setdefault("GOOGLE_API_KEY", "test-key-for-pytest")

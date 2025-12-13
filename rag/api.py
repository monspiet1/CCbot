from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from rag_ementa import rag_ementa
from rag_livros import rag_livros
from rag_ambos import rag_ambos
from integracao import routing  # separe o routing em um arquivo

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = FastAPI()

class Question(BaseModel):
    pergunta: str

@app.post("/chat")
def chat(data: Question):
    pergunta = data.pergunta
    decision = routing(pergunta)

    if decision == "ementa":
        resposta = rag_ementa(pergunta)
    elif decision == "livros":
        resposta = rag_livros(pergunta)
    else:
        resposta = rag_ambos(pergunta)

    return {
        "rota": decision,
        "resposta": resposta
    }

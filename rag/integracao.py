from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from rag_ementa import rag_ementa
from rag_ambos import rag_ambos
from rag_livros import rag_livros
from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

template_for_routing = PromptTemplate.from_template(
    """
    Classifique a pergunta abaixo como uma das opções:

    1. "ementa"
    2. "livros"
    3. "ambos"

    Regras:
    - Use "ementa" quando a pergunta tratar de conteúdos objetivos da disciplina, tópicos, requisitos, critérios de avaliação.
    - Use "livros" quando a pergunta pedir explicações teóricas, conceitos do conteúdo dos livros ou autores específicos.
    - Use "ambos" quando a pergunta exigir tanto referências da ementa quanto conteúdo conceitual dos livros.

    Responda somente com: ementa, livros ou ambos.

    ## USER QUERY
    {pergunta}

    Resposta:
    """
)

# modelo para verificar se a pergunta se refere a ementa, livros ou ambos
def routing(user_query:str) -> str:
  chain_routing = (template_for_routing |
           ChatGroq(model="llama-3.1-8b-instant", temperature=0 , api_key=GROQ_API_KEY) |
           StrOutputParser()
           )

  return chain_routing.invoke({"pergunta": user_query})


pergunta = "O que está contido na ementa de Programação I? Como posso implementar uma fila circular?"
decision = routing(pergunta)

if decision == "ementa":
    print(rag_ementa(pergunta))

elif decision == "livros":
    print(rag_livros(pergunta))

elif decision == "ambos":
    print(rag_ambos(pergunta))
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

embeddings_livros = HuggingFaceEmbeddings(
    model_name="./models/mini-lm",
    model_kwargs={"device": "cuda"}
)

db_livros = Chroma(
    persist_directory="livrosdb",
    embedding_function=embeddings_livros
)

template_for_livros = PromptTemplate.from_template(
    """
    Você é um assistente que ajuda pessoas a entenderem sobre assuntos presente no contexto.
    Responda sempre em pt-BR.

    Use como contexto o conteúdo abaixo.
    SE O CONTEXTO TIVER METADADOS, use-os na resposta.

    - SEMPRE responda com a fonte real usando exatamente o campo metadata['fonte'].
    - Se não houver fonte no metadata, diga “Fonte não disponível”.
    - Se não souber a resposta, diga que não sabe.
    - Sempre ensine o usuário a fazer o que quer sem usar código, usando tópicos numerados com texto puro.
    ## CONTEXT
    {contexto}

    ## USER QUERY
    {pergunta}

    Resposta (somente texto explicativo, sem código):
    """

)

def rag_livros(user_query:str) -> str:
  context = db_livros.similarity_search(user_query, k = 3) # traz os documentos mais semelhantes

  if len(context) == 0:
    return "Eu não sou capaz de responder esta pergunta"

  context = "\n\n".join([f"## Documento {k}\n" + doc.page_content + "\nFonte: " + doc.metadata.get("source", "") for k, doc in enumerate(context, start=1)])

  chain = (template_for_livros |
           ChatGroq(model="llama-3.1-8b-instant", temperature=0 , api_key=GROQ_API_KEY) |
           StrOutputParser()
           )

  return chain.invoke({"contexto":context, "pergunta": user_query})
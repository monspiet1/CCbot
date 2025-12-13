from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

embeddings_ementa = HuggingFaceEmbeddings(
    model_name="./models/mini-lm",   # pasta onde salvou
    model_kwargs={"device": "cuda"}   # ou "cuda"
)

embeddings_livros = HuggingFaceEmbeddings(
    model_name="./models/mini-lm",
    model_kwargs={"device": "cuda"}
)


db_ementa = Chroma(
    persist_directory="ementadb",
    embedding_function=embeddings_ementa
)

db_livros = Chroma(
    persist_directory="livrosdb",
    embedding_function=embeddings_livros
)

template_for_ambos = PromptTemplate.from_template(
    """
    Você é um assistente que ajuda pessoas a entenderem sobre assuntos relacionados a ementa e conteúdos.
    Responda sempre em pt-BR.

    Use como contexto o conteúdo abaixo.
    SE O CONTEXTO TIVER METADADOS, use-os na resposta.

    - SEMPRE responda com a fonte real usando exatamente o campo metadata['fonte'].
    - Se não houver fonte no metadata, diga “Fonte não disponível”.
    - Se não souber a resposta, diga que não sabe.
    - Sempre ensine o usuário a fazer o que quer sem usar código, usando tópicos numerados com texto puro.

    ## CONTEXT
    {contexto_ementa}

    ## CONTEXT
    {contexto_livros}

    ## USER QUERY
    {pergunta}

    Resposta (somente texto explicativo, sem código):
    """

)

def rag_ambos(user_query:str) -> str:
  context_ementa_docs = db_ementa.similarity_search(user_query, k=3)
  context_livros_docs = db_livros.similarity_search(user_query, k=3)

  if len(context_livros_docs) == 0:
      context_livros = "Nenhum resultado encontrado nos livros."
  else:
      context_livros = "\n\n".join([
          f"## Documento {i}\n{doc.page_content}\nFonte: {doc.metadata.get('source','')}"
          for i, doc in enumerate(context_livros_docs, start=1)
      ])

  if len(context_ementa_docs) == 0:
      context_ementa = "Nenhum resultado encontrado na ementa."
  else:
      context_ementa = "\n\n".join([
          f"## Documento {i}\n{doc.page_content}\nFonte: {doc.metadata.get('source','')}"
          for i, doc in enumerate(context_ementa_docs, start=1)
      ])
  chain = (template_for_ambos |
           ChatGroq(model="llama-3.1-8b-instant", temperature=0 , api_key=GROQ_API_KEY) |
           StrOutputParser()
           )

  return chain.invoke({"contexto_ementa":context_ementa, "contexto_livros":context_livros, "pergunta": user_query})
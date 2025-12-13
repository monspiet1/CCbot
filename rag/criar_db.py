from langchain_community.document_loaders import PyPDFLoader
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_classic.schema import Document
import re


# criação do db de ementa
loader = PyPDFLoader("C:\\Users\\Andrey21\\my-projects\\langchain_chat2\\ed_prog.pdf")
docs = loader.load()

ed_prog = "\n".join([d.page_content for d in docs])

# Regex para detectar início de disciplina
pattern = r"DISCIPLINA\s*:\s*(.+?)\n"

matches = list(re.finditer(pattern, ed_prog))

disciplinas = []

for i, m in enumerate(matches):
    nome = m.group(1).strip()

    start = m.end()
    end = matches[i+1].start() if i + 1 < len(matches) else len(ed_prog)

    bloco = ed_prog[start:end].strip()

    disciplinas.append(
        Document(
            page_content=f"DISCIPLINA: {nome}\n{bloco}",
            metadata={"disciplina": nome, "fonte": "https://dacc.unir.br/uploads/91919191/arquivos/04_1348703281.pdf"}
        )
    )


embeddings_ementa = HuggingFaceEmbeddings(
    model_name="./models/mini-lm",   # pasta onde salvou
    model_kwargs={"device": "cuda"}   # ou "cuda"
)

db_ementa = Chroma.from_documents(
    documents = disciplinas,
    embedding = embeddings_ementa,
    persist_directory= "./ementadb",
    collection_metadata={"hnsw:space": "cosine"}
)



# criação do db de livros
urls = [
    "C:\\Users\\Andrey21\\my-projects\\langchain_chat2\\algoritmos.pdf",
    "C:\\Users\\Andrey21\\my-projects\\langchain_chat2\\Como-Programar-C.pdf"
]

docs = []
for i in range(len(urls)):
    loader = PyPDFLoader(urls[i])
    docs.extend(loader.load())


text_splitter_livros = RecursiveCharacterTextSplitter(
    chunk_size = 1000,
    chunk_overlap = 500,
    length_function = len,
)

chunk_livro = text_splitter_livros.split_documents(docs)

embeddings_livros = HuggingFaceEmbeddings(
    model_name="./models/mini-lm",   # pasta onde salvou
    model_kwargs={"device": "cuda"}   # ou "cuda"
)

db_livros = Chroma.from_documents(
    documents = chunk_livro,
    embedding = embeddings_livros,
    persist_directory= "livrosdb",
    collection_metadata={"hnsw:space": "cosine"}
)
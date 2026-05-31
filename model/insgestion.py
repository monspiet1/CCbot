from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from vector_store import vector_store

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)

def add_text_to_chroma(text: str, source_name: str):
    """Transforms raw text into a Document, splits it into chunks, and saves it to ChromaDB."""

    doc = Document(page_content=text, metadata={"source": source_name})

    splits = text_splitter.split_documents([doc])

    vector_store.add_documents(documents=splits)
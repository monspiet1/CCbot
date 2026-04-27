from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

vector_store = Chroma(
    collection_name="ccbot_collection",
    embedding_function=embeddings,
    persist_directory="./vector-store/chroma_db"
)
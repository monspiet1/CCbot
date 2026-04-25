import pandas as pd
import chromadb

df_qa = pd.read_csv("qa.csv")
df_qa = df_qa.sample(500, random_state=0).reset_index(drop=True)


df_qa['combined_text'] = (
    "Question: " + df_qa['Question'].fillna("").astype(str) + '. ' +
    "Answer: " + df_qa['Answer'].fillna("").astype(str) + '. ' +
    "Type: " + df_qa['qtype'].fillna("").astype(str) + '. ' 
)

df_md = pd.read_csv("md.csv")
df_md = df_md.sample(500, random_state=0).reset_index(drop=True)

df_md['combined_text'] = (
    "Device Name: " + df_md['Device_Name'].fillna("Unknown").astype(str) + ". " +
    "Model: " + df_md['Model_Number'].fillna("N/A").astype(str) + ". " +
    "Manufacturer: " + df_md['Manufacturer'].fillna("Unknown").astype(str) + ". " +
    "Indications: " + df_md['Indications_for_Use'].fillna("None").astype(str) + ". " +
    "Contraindications: " + df_md['Contraindications'].fillna('None').astype(str)
)


# =========================================================================================
# Parte destinada ao chroma db

client = chromadb.PersistentClient(path="./chromadb")

collection1 = client.get_or_create_collection(name='medical_qa')
collection1.add(
    documents=df_qa['combined_text'].tolist(),
    metadatas= df_qa.to_dict(orient="records"),
    ids=df_qa.index.astype(str).tolist()
)

collection2 = client.get_or_create_collection(name='medical_devices')
collection2.add(
    documents=df_md['combined_text'].tolist(),
    metadatas= df_md.to_dict(orient="records"),
    ids=df_md.index.astype(str).tolist()
)

query = "what are the devices relevant to surgery"

results = collection2.query(query_texts=[query], n_results=3)

print(results)
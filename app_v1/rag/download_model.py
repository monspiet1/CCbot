from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    local_dir="./models/mini-lm"
)
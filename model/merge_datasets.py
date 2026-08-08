import json
import os


def merge_jsonl_datasets(
    base_filepath: str, new_filepath: str, output_filepath: str
) -> None:
    """
    Une dois arquivos JSONL de sessões do Socratic CT-Tutor.
    Renomeia os IDs do segundo arquivo para continuar a contagem exata do primeiro.
    """
    all_sessions = []

    # 1. Carrega o dataset base (suas 6 sessões originais)
    if os.path.exists(base_filepath):
        with open(base_filepath, "r", encoding="utf-8") as f_base:
            for line in f_base:
                if line.strip():
                    all_sessions.append(json.loads(line))
    else:
        print(
            f"Aviso: Arquivo base '{base_filepath}' não encontrado. Iniciando do zero."
        )

    base_count = len(all_sessions)
    print(f"--- Lendo arquivo base: '{base_filepath}' ---")
    print(f"Sessões originais carregadas: {base_count}")

    # 2. Carrega as novas sessões e atualiza os IDs para evitar duplicação
    new_sessions_added = 0
    if os.path.exists(new_filepath):
        print(f"\n--- Lendo arquivo novo: '{new_filepath}' ---")
        with open(new_filepath, "r", encoding="utf-8") as f_new:
            for line in f_new:
                if line.strip():
                    session_data = json.loads(line)

                    # Lógica de controle de ID Sequencial
                    new_id_number = base_count + new_sessions_added + 1
                    new_session_id = f"session_{new_id_number:03d}"

                    old_id = session_data.get("session_id")
                    session_data["session_id"] = new_session_id

                    print(
                        f"Renomeando ID: {old_id} -> {new_session_id} | Perfil: {session_data['profile']['name']}"
                    )

                    all_sessions.append(session_data)
                    new_sessions_added += 1
    else:
        print(f"Erro: Arquivo com novas sessões '{new_filepath}' não encontrado.")
        return

    # 3. Salva o dataset final unificado
    print(f"\n--- Salvando arquivo unificado: '{output_filepath}' ---")
    with open(output_filepath, "w", encoding="utf-8") as f_out:
        for session in all_sessions:
            f_out.write(json.dumps(session, ensure_ascii=False) + "\n")

    print(
        f"Merge concluído com sucesso! Dataset final contém {len(all_sessions)} sessões."
    )


if __name__ == "__main__":
    # Variáveis apontando para os seus arquivos
    ARQUIVO_BASE = "dataset_ct_tutoring.jsonl"
    ARQUIVO_NOVO = "dataset_ct_tutoring (2).jsonl"

    # Sugiro salvar em um nome novo para você verificar antes de substituir o original
    ARQUIVO_FINAL = "dataset_ct_tutoring_unificado.jsonl"

    merge_jsonl_datasets(ARQUIVO_BASE, ARQUIVO_NOVO, ARQUIVO_FINAL)

import argparse
import ast
import json
import os
import sys
import time

import pandas as pd
from deepeval import evaluate
from deepeval.evaluate.configs import AsyncConfig, DisplayConfig
from deepeval.test_case import LLMTestCase
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval_metrics import (
    get_contextual_relevancy_metric,
    get_pedagogical_progression_metric,
    get_scaffolding_effectiveness_metric,
    get_socratic_alignment_metric,
)


def clean_message_content(content: str) -> str:
    """Extrai o texto limpo de um content block do Gemini (stringified list)."""
    if isinstance(content, str) and content.startswith("["):
        try:
            blocks = ast.literal_eval(content)
            text_parts = [
                block["text"]
                for block in blocks
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            if text_parts:
                return " ".join(text_parts)
        except (ValueError, SyntaxError):
            pass
    return content


def load_dataset_as_test_cases(jsonl_filepath: str) -> List[LLMTestCase]:
    """Converte os arquivos JSONL de telemetria em casos de teste formais da biblioteca DeepEval,
    isolando os turnos em que o Tutor interage em resposta ao estudante."""
    test_cases = []
    with open(jsonl_filepath, "r", encoding="utf-8") as f:
        for line in f:
            session = json.loads(line)
            trace = session["trace"]

            for i in range(1, len(trace)):
                current_turn = trace[i]
                prev_turn = trace[i - 1]

                if current_turn["speaker"] == "tutor" and prev_turn["speaker"] == "student":
                    artifacts = current_turn.get("artifacts_snapshot", "{}")

                    test_case = LLMTestCase(
                        input=clean_message_content(prev_turn["content"]),
                        actual_output=clean_message_content(current_turn["content"]),
                        retrieval_context=[
                            f"Blackboard Snapshot: {artifacts}",
                            f"Current CT Stage: {current_turn['stage']}",
                        ],
                        expected_output=(
                            f"A Socratic guiding question aligned with the "
                            f"{current_turn['stage']} methodology."
                        ),
                    )
                    test_cases.append(test_case)

    return test_cases


def _evaluate_with_retry(
    batch: List[LLMTestCase],
    metrics: List,
    batch_size: int,
    max_attempts: int = 5,
    retry_delay: float = 70.0,
):
    """Avalia um lote com retries para erros transitórios da API (429/503)."""
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return evaluate(
                test_cases=batch,
                metrics=metrics,
                async_config=AsyncConfig(
                    run_async=True, max_concurrent=batch_size
                ),
                display_config=DisplayConfig(
                    show_indicator=False,
                    print_results=False,
                    inspect_after_run=False,
                ),
            )
        except Exception as exc:
            last_error = exc
            print(
                f"--- Erro transitório ({type(exc).__name__}) na tentativa "
                f"{attempt + 1}/{max_attempts} | aguardando {retry_delay:.0f}s ---"
            )
            time.sleep(retry_delay)
    if last_error is not None:
        raise last_error
    raise RuntimeError("Falha inesperada: nenhuma exceção capturada durante a avaliação.")


def _build_and_write_summary(csv_file: str, metrics: List) -> None:
    """Lê o CSV completo e regenera a tabela de síntese estatística (escala 0-5 para a Socrática)."""
    df_results_full = pd.read_csv(csv_file)
    print("\n--- Síntese Estatística para Seção de Resultados do Artigo ---")
    summary = {}
    for m in metrics:
        score_col = next(
            (c for c in df_results_full.columns if c.startswith(f"{m.name} ") and c.endswith(" (Score)")),
            None,
        )
        success_col = next(
            (c for c in df_results_full.columns if c.startswith(f"{m.name} ") and c.endswith(" (Success)")),
            None,
        )

        if score_col is not None and success_col is not None:
            mean_score = df_results_full[score_col].mean()
            std_score = df_results_full[score_col].std()
            pass_rate = (df_results_full[success_col].sum() / len(df_results_full)) * 100

            if "Socrat" in m.name:
                summary[m.name] = {
                    "Média Score": f"{(mean_score * 5):.2f} (±{(std_score * 5):.2f}) [Escala 0-5]",
                    "Taxa de Sucesso (%)": f"{pass_rate:.1f}%",
                }
            else:
                summary[m.name] = {
                    "Média Score": f"{mean_score:.3f} (±{std_score:.3f}) [Escala 0-1]",
                    "Taxa de Sucesso (%)": f"{pass_rate:.1f}%",
                }

    df_summary = pd.DataFrame(summary).T
    df_summary.index.name = "Metric"
    print(df_summary.to_string())
    df_summary.to_csv("paper_benchmark_summary_table.csv")


def run_paper_benchmark(
    jsonl_filepath: str = "dataset_ct_tutoring.jsonl",
    max_cases: int | None = None,
    batch_size: int = 3,
    sleep_between_batches: float = 65.0,
):
    print("--- Iniciando carregamento do dataset e montagem dos casos de teste ---")
    test_cases = load_dataset_as_test_cases(jsonl_filepath)
    if max_cases is not None:
        test_cases = test_cases[:max_cases]
    print(f"--- Total de turnos pedagógicos extraídos: {len(test_cases)} ---")

    csv_file = "paper_benchmark_detailed_results.csv"
    evaluated_count = 0

    if os.path.exists(csv_file):
        df_existing = pd.read_csv(csv_file)
        evaluated_count = len(df_existing)
        print(f"--- Encontrados {evaluated_count} testes já avaliados no arquivo CSV. ---")

    if evaluated_count >= len(test_cases):
        print("--- Todos os testes já foram avaliados. Nenhuma ação necessária. ---")
        return

    remaining_test_cases = test_cases[evaluated_count:]
    print(f"--- Retomando a avaliação automática para os {len(remaining_test_cases)} testes restantes... ---")

    socratic_metric = get_socratic_alignment_metric()
    scaffolding_metric = get_scaffolding_effectiveness_metric()
    progression_metric = get_pedagogical_progression_metric()
    relevancy_metric = get_contextual_relevancy_metric()

    metrics = [socratic_metric, scaffolding_metric, progression_metric, relevancy_metric]

    for i, start in enumerate(range(0, len(remaining_test_cases), batch_size)):
        batch = remaining_test_cases[start : start + batch_size]
        results = _evaluate_with_retry(batch, metrics, batch_size)

        data_rows = []
        for test_result in results.test_results:
            row: dict[str, object] = {
                "input_student": str(test_result.input)[:60] + "...",
                "output_tutor": str(test_result.actual_output)[:60] + "...",
            }
            for metric_data in (test_result.metrics_data or []):
                row[f"{metric_data.name} (Score)"] = metric_data.score
                row[f"{metric_data.name} (Success)"] = metric_data.success
                row[f"{metric_data.name} (Reasoning)"] = (
                    metric_data.reason[:120] + "..." if metric_data.reason else ""
                )
            data_rows.append(row)

        df_batch = pd.DataFrame(data_rows)
        if evaluated_count > 0 or i > 0:
            df_batch.to_csv(csv_file, mode="a", header=False, index=False)
        else:
            df_batch.to_csv(csv_file, index=False)

        processed = evaluated_count + (i + 1) * len(batch)
        print(f"--- Lote {i + 1} avaliado e persistido no CSV ({processed}/{len(test_cases)} casos) ---")

        _build_and_write_summary(csv_file, metrics)

        remaining = len(remaining_test_cases) - (start + len(batch))
        if remaining > 0:
            print(
                f"--- Restam {remaining} casos "
                f"| Pausa de {sleep_between_batches:.0f}s para respeitar a cota da API ---"
            )
            time.sleep(sleep_between_batches)

    print("--- Benchmark concluído: todos os casos avaliados e persistidos ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark psicométrico do Socratic CT-Tutor via DeepEval."
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="dataset_ct_tutoring.jsonl",
        help="Caminho para o dataset JSONL de telemetria (default: dataset_ct_tutoring.jsonl).",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=None,
        help="Limita o número de turnos pedagógicos avaliados (pilot/amostra).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=3,
        help="Casos de teste por lote (padrão 3 = 12 chamadas LLM por lote).",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=65.0,
        help="Pausa em segundos entre lotes para respeitar a cota da API (padrão 65s).",
    )
    args = parser.parse_args()

    run_paper_benchmark(
        jsonl_filepath=args.dataset,
        max_cases=args.max_cases,
        batch_size=args.batch_size,
        sleep_between_batches=args.sleep,
    )

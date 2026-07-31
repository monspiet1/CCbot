import ast
import json
import os
import sys

import pandas as pd
from deepeval import evaluate
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


def run_paper_benchmark(jsonl_filepath: str = "dataset_ct_tutoring.jsonl"):
    """Executa a suíte psicométrica completa via DeepEval e exporta tabelas consolidadas para o artigo."""
    print("--- Iniciando carregamento do dataset e montagem dos casos de teste ---")
    test_cases = load_dataset_as_test_cases(jsonl_filepath)
    print(
        f"--- Total de turnos pedagógicos isolados para avaliação: {len(test_cases)} ---"
    )

    socratic_metric = get_socratic_alignment_metric()
    scaffolding_metric = get_scaffolding_effectiveness_metric()
    progression_metric = get_pedagogical_progression_metric()
    relevancy_metric = get_contextual_relevancy_metric()

    metrics = [socratic_metric, scaffolding_metric, progression_metric, relevancy_metric]

    print("--- Executando julgamento automatizado via DeepEval (LLM-as-a-Judge) ---")
    results = evaluate(test_cases=test_cases, metrics=metrics)

    data_rows = []
    for test_result in results.test_results:
        row = {
            "input_student": str(test_result.input)[:60] + "...",
            "output_tutor": str(test_result.actual_output)[:60] + "...",
        }
        for metric_data in test_result.metrics_data:
            row[f"{metric_data.name} (Score)"] = metric_data.score
            row[f"{metric_data.name} (Success)"] = metric_data.success
            row[f"{metric_data.name} (Reasoning)"] = (
                metric_data.reason[:120] + "..." if metric_data.reason else ""
            )
        data_rows.append(row)

    df_results = pd.DataFrame(data_rows)
    df_results.to_csv("paper_benchmark_detailed_results.csv", index=False)

    print("--- Síntese Estatística para Seção de Resultados do Artigo ---")
    summary = {}
    for m in metrics:
        score_col = f"{m.name} (Score)"
        success_col = f"{m.name} (Success)"
        if score_col in df_results.columns:
            mean_score = df_results[score_col].mean()
            std_score = df_results[score_col].std()
            pass_rate = (df_results[success_col].sum() / len(df_results)) * 100
            summary[m.name] = {
                "Média Score (0.0 - 1.0)": f"{mean_score:.3f} (±{std_score:.3f})",
                "Taxa de Sucesso (%)": f"{pass_rate:.1f}%",
            }

    df_summary = pd.DataFrame(summary).T
    print(df_summary.to_string())
    df_summary.to_csv("paper_benchmark_summary_table.csv")
    print("--- Validação concluída: Arquivos CSV de benchmark gerados com êxito ---")


if __name__ == "__main__":
    run_paper_benchmark()

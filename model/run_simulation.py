import argparse
import json
import math
import random
import time
from typing import List

from profiles import PROFILES
from simulation.orchestrator import SimulationOrchestrator
from simulation.schema import StudentProfile


def append_session_to_jsonl(session: dict, filepath: str) -> None:
    """Salva uma sessão no arquivo JSONL (modo append)."""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(session, ensure_ascii=False) + "\n")


def distribute_sessions_uniformly(
    num_sessions: int, profiles: List[StudentProfile]
) -> List[StudentProfile]:
    """Distribui sessões uniformemente entre os perfis disponíveis."""
    base_count = math.ceil(num_sessions / len(profiles))
    distribution = []

    for profile in profiles:
        count = min(base_count, num_sessions - len(distribution))
        distribution.extend([profile] * count)

    return distribution[:num_sessions]


def run_batch_simulation(
    num_sessions: int = 15,
    seed: int | None = None,
    delay: float = 65.0,
    output_path: str = "dataset_ct_tutoring.jsonl",
) -> List[dict]:
    """Executa simulações em batch com distribuição uniforme de perfis."""
    if seed is not None:
        random.seed(seed)
        print(f"Seed definida: {seed}")

    profiles = distribute_sessions_uniformly(num_sessions, PROFILES)
    orchestrator = SimulationOrchestrator(max_turns_per_session=15, delay_between_requests=delay)
    sessions = []

    print(f"\n{'='*60}")
    print(f"INICIANDO LOTE DE SIMULAÇÕES")
    print(f"Total de sessões: {num_sessions}")
    print(f"Distribuição uniforme: {len(profiles)} sessões")
    print(f"Delay entre requisições LLM: {delay}s")
    print(f"Arquivo de saída: {output_path}")
    print(f"{'='*60}\n")

    start_time = time.time()

    for i, profile in enumerate(profiles):
        session_id = f"session_{i+1:03d}"
        print(f"\n[{i+1}/{num_sessions}] Executando sessão {session_id}...")

        result = orchestrator.simulate_session(profile, session_id)
        sessions.append(result)

        append_session_to_jsonl(result, output_path)
        print(f"  Sessão salva em {output_path}")

        elapsed = time.time() - start_time
        avg_time = elapsed / (i + 1)
        remaining = avg_time * (num_sessions - i - 1)
        print(
            f"  Sessão concluída: {result['completed']} | "
            f"Turnos: {result['total_turns']} | "
            f"Tempo restante estimado: {remaining:.0f}s"
        )

    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"LOTE CONCLUÍDO")
    print(f"Tempo total: {total_time:.1f}s")
    print(f"Sessões executadas: {len(sessions)}")
    print(f"{'='*60}\n")

    return sessions


def main():
    parser = argparse.ArgumentParser(
        description="Executa simulações do Socratic CT-Tutor e gera dataset JSONL"
    )
    parser.add_argument(
        "--num-sessions",
        type=int,
        default=15,
        help="Número total de sessões a executar (padrão: 15)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed para reprodutibilidade (opcional)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset_ct_tutoring.jsonl",
        help="Caminho do arquivo de saída JSONL (padrão: dataset_ct_tutoring.jsonl)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=65.0,
        help="Delay em segundos entre requisições LLM (padrão: 65.0)",
    )

    args = parser.parse_args()

    if args.num_sessions < 1:
        print("Erro: O número de sessões deve ser maior que 0.")
        return

    sessions = run_batch_simulation(
        num_sessions=args.num_sessions,
        seed=args.seed,
        delay=args.delay,
        output_path=args.output,
    )

    completed = sum(1 for s in sessions if s["completed"])
    print(f"\nResumo:")
    print(f"  Total de sessões: {len(sessions)}")
    print(f"  Sessões completas: {completed}")
    print(f"  Sessões incompletas: {len(sessions) - completed}")
    print(f"  Taxa de conclusão: {completed/len(sessions)*100:.1f}%")


if __name__ == "__main__":
    main()

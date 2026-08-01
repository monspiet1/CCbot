import json
import time
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage

from simulation.schema import StudentProfile
from simulation.student_agent import run_student_turn
from workflow import app as tutor_app


class SimulationOrchestrator:
    """Orquestrador dual-agent que coordena o loop de retroalimentação entre o TutorGraph e o StudentAgent."""

    def __init__(
        self, max_turns_per_session: int = 15, delay_between_requests: float = 65.0
    ):
        self.max_turns = max_turns_per_session
        self.delay = delay_between_requests

    def simulate_session(
        self, profile: StudentProfile, session_id: str
    ) -> Dict[str, Any]:
        """Executa uma simulação ponta a ponta entre o Tutor e o Aluno, registrando a telemetria da conversação."""
        print(
            f"\n--- Iniciando Simulação [{session_id}] | Persona: {profile.name} ({profile.knowledge_level}) ---"
        )

        initial_msg = f"Olá, preciso de ajuda pedagógica para modelar e criar a lógica de um problema de {profile.domain_problem}."

        state: Dict[str, Any] = {
            "messages": [HumanMessage(content=initial_msg)],
            "current_stage": "decomposition",
            "is_tutoring_active": False,
            "approved": False,
            "evaluation_feedback": "",
            "student_artifacts": {},
        }

        turn_count = 0
        session_trace: List[Dict[str, Any]] = []
        is_completed = False
        attempts_in_current_stage = 0
        last_stage = state["current_stage"]

        while turn_count < self.max_turns:
            turn_count += 1
            print(f"\n[Turno {turn_count}] Processando transição no Grafo do Tutor...")

            tutor_output_state = None
            for event in tutor_app.stream(state):
                for node_name, node_data in event.items():
                    tutor_output_state = node_data

            print(f"  [Delay] Aguardando {self.delay}s após chamada do Tutor...")
            time.sleep(self.delay)

            if tutor_output_state:
                if "messages" in tutor_output_state:
                    state["messages"].extend(tutor_output_state["messages"])
                for key in [
                    "current_stage",
                    "is_tutoring_active",
                    "approved",
                    "evaluation_feedback",
                    "student_artifacts",
                ]:
                    if key in tutor_output_state:
                        state[key] = tutor_output_state[key]

            if state["current_stage"] == last_stage and not state["approved"]:
                attempts_in_current_stage += 1
            else:
                attempts_in_current_stage = 0
                last_stage = state["current_stage"]

            last_ai_msg = state["messages"][-1].content
            if isinstance(last_ai_msg, list):
                last_ai_msg = str(last_ai_msg)
            print(
                f"[Tutor -> Aluno | Pilar: {state['current_stage']} | Status Aprovado: {state['approved']}]: {last_ai_msg[:100]}..."
            )

            session_trace.append(
                {
                    "turn": turn_count,
                    "speaker": "tutor",
                    "stage": state["current_stage"],
                    "approved": state["approved"],
                    "content": last_ai_msg,
                    "artifacts_snapshot": str(state["student_artifacts"]),
                }
            )

            if state["current_stage"] == "completed":
                print(
                    "--- Sessão finalizada com sucesso: Todos os quatro pilares foram consolidados no Quadro-Negro ---"
                )
                is_completed = True
                break

            print(
                f"[Turno {turn_count}] Processando resposta cognitiva do Agente Aluno..."
            )
            student_reply = run_student_turn(
                messages=state["messages"],
                profile=profile,
                current_stage=state["current_stage"],
                attempts_in_stage=attempts_in_current_stage,
            )
            print(
                f"[Aluno -> Tutor (tentativa {attempts_in_current_stage} no estágio)]: {student_reply[:100]}..."
            )

            print(f"  [Delay] Aguardando {self.delay}s após chamada do Aluno...")
            time.sleep(self.delay)

            state["messages"].append(HumanMessage(content=student_reply))

            session_trace.append(
                {
                    "turn": turn_count,
                    "speaker": "student",
                    "stage": state["current_stage"],
                    "content": student_reply,
                }
            )

        return {
            "session_id": session_id,
            "profile": profile.model_dump(),
            "completed": is_completed,
            "total_turns": turn_count,
            "final_stage_reached": state["current_stage"],
            "artifacts_collected": state["student_artifacts"],
            "trace": session_trace,
        }

    def export_dataset_jsonl(
        self,
        sessions: List[Dict[str, Any]],
        filepath: str = "dataset_ct_tutoring.jsonl",
    ) -> None:
        """Exporta os registros das sessões no formato JSONL padrão para fine-tuning ou benchmarking estatístico."""
        with open(filepath, "w", encoding="utf-8") as f:
            for s in sessions:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        print(
            f"\n--- Dataset contendo {len(sessions)} interações exportado com sucesso para '{filepath}' ---"
        )

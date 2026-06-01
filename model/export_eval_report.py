from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from evals.ct_metrics import build_conversational_metrics
from evals.ct_runner import run_scripted_conversation
from evals.ct_scenarios import POSITIVE_SCENARIOS


def main() -> None:
    output_dir = Path("eval_reports")
    output_dir.mkdir(exist_ok=True)

    rows: list[dict] = []

    for scenario in POSITIVE_SCENARIOS:
        test_case, final_state, trace = run_scripted_conversation(scenario)

        for metric in build_conversational_metrics():
            metric.measure(test_case)

            rows.append(
                {
                    "scenario_id": scenario.id,
                    "metric": getattr(metric, "name", metric.__class__.__name__),
                    "score": getattr(metric, "score", None),
                    "success": getattr(metric, "success", None),
                    "threshold": getattr(metric, "threshold", None),
                    "reason": getattr(metric, "reason", None),
                    "final_stage": final_state.get("current_stage"),
                    "is_tutoring_active": final_state.get("is_tutoring_active"),
                    "artifact_keys": list(
                        final_state.get("student_artifacts", {}).keys()
                    ),
                }
            )

        rows.append(
            {
                "scenario_id": scenario.id,
                "metric": "Structural Trace",
                "score": None,
                "success": True,
                "threshold": None,
                "reason": "Execution trace captured for auditability.",
                "trace": trace,
            }
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"ct_graph_eval_{timestamp}.json"

    output_path.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Evaluation report saved to: {output_path}")


if __name__ == "__main__":
    main()

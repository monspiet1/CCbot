# utils/rate_limiter.py

from __future__ import annotations

import os
import threading
import time
from typing import Any


class SimpleRateLimiter:
    """
    Rate limiter simples para evitar exceder limite de requisições por minuto.

    Ele força um intervalo mínimo entre chamadas consecutivas ao modelo.
    Útil para uso com planos gratuitos de APIs como Gemini.
    """

    def __init__(self, min_interval_seconds: float = 65.0):
        self.min_interval_seconds = min_interval_seconds
        self._lock = threading.Lock()
        self._last_call_timestamp = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call_timestamp

            remaining = self.min_interval_seconds - elapsed

            if remaining > 0:
                print(
                    f"[RateLimiter] Aguardando {remaining:.1f}s "
                    f"antes da próxima chamada ao LLM..."
                )
                time.sleep(remaining)

            self._last_call_timestamp = time.monotonic()


GEMINI_MIN_INTERVAL_SECONDS = float(os.getenv("GEMINI_MIN_INTERVAL_SECONDS", "65"))

gemini_rate_limiter = SimpleRateLimiter(
    min_interval_seconds=GEMINI_MIN_INTERVAL_SECONDS
)


def rate_limited_invoke(model: Any, *args: Any, **kwargs: Any) -> Any:
    """
    Executa model.invoke(...) respeitando o intervalo mínimo configurado.
    """
    gemini_rate_limiter.wait()
    return model.invoke(*args, **kwargs)

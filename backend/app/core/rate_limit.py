import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    """Limitador de tentativas por chave (janela deslizante).

    ponytail: em memória e por processo — suficiente para uma instância de
    desenvolvimento/homologação; trocar por Redis quando houver mais de um
    worker em produção.
    """

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str) -> bool:
        """Registra uma tentativa. Retorna False se o limite foi excedido."""
        now = time.monotonic()
        window = self._attempts[key]
        while window and now - window[0] > self.window_seconds:
            window.popleft()
        if len(window) >= self.max_attempts:
            return False
        window.append(now)
        return True

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)

"""Circuit breaker — protects external HTTP calls from cascading failures.

States:
    CLOSED  — requests pass through normally; failures are counted.
    OPEN    — requests are rejected immediately (fail-fast).
    HALF_OPEN — one probe request is allowed; success closes, failure re-opens.

Transitions:
    CLOSED → OPEN:      failure_threshold failures within failure_window seconds.
    OPEN → HALF_OPEN:   recovery_timeout seconds have elapsed.
    HALF_OPEN → CLOSED: probe request succeeds.
    HALF_OPEN → OPEN:   probe request fails.
"""

import threading
import time
from enum import StrEnum


class CircuitState(StrEnum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Thread-safe circuit breaker for external service calls.

    Args:
        name: Identifier for this circuit (used in logging/health).
        failure_threshold: Number of failures to trip the circuit.
        failure_window: Rolling window in seconds for counting failures.
        recovery_timeout: Seconds to wait before allowing a probe.
    """

    def __init__(
        self,
        name: str,
        *,
        failure_threshold: int = 3,
        failure_window: float = 30.0,
        recovery_timeout: float = 60.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.failure_window = failure_window
        self.recovery_timeout = recovery_timeout

        self._lock = threading.Lock()
        self._state: CircuitState = CircuitState.CLOSED
        self._failures: list[float] = []  # timestamps of recent failures
        self._opened_at: float = 0.0

    @property
    def state(self) -> CircuitState:
        """Current circuit state (evaluates OPEN → HALF_OPEN transition)."""
        with self._lock:
            return self._evaluate_state()

    def _evaluate_state(self) -> CircuitState:
        """Evaluate current state, transitioning OPEN → HALF_OPEN if timeout elapsed.

        Must be called with self._lock held.
        """
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._opened_at >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def allow_request(self) -> bool:
        """Check whether a request should be allowed through.

        Returns:
            True if the request may proceed, False if the circuit is open.
        """
        with self._lock:
            current = self._evaluate_state()
            return current in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """Record a successful request. Closes the circuit if half-open."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._failures.clear()
            elif self._state == CircuitState.CLOSED:
                # Success in closed state — no action needed
                pass

    def record_failure(self) -> None:
        """Record a failed request. May trip the circuit."""
        now = time.monotonic()
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # Probe failed — re-open immediately
                self._state = CircuitState.OPEN
                self._opened_at = now
                return

            if self._state == CircuitState.CLOSED:
                # Prune failures outside the window
                cutoff = now - self.failure_window
                self._failures = [t for t in self._failures if t > cutoff]
                self._failures.append(now)

                if len(self._failures) >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._opened_at = now

    def get_health(self) -> dict[str, str | int | float]:
        """Return health info for admin diagnostics."""
        with self._lock:
            current = self._evaluate_state()
            now = time.monotonic()
            cutoff = now - self.failure_window
            recent_failures = len([t for t in self._failures if t > cutoff])

            result: dict[str, str | int | float] = {
                "name": self.name,
                "state": current.value,
                "failure_count": recent_failures,
                "failure_threshold": self.failure_threshold,
            }

            if current == CircuitState.OPEN:
                remaining = self.recovery_timeout - (now - self._opened_at)
                result["recovery_remaining_seconds"] = round(max(0.0, remaining), 1)

            return result

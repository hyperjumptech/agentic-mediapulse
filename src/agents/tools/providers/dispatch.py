import os
from collections.abc import Callable


class AllProvidersFailed(Exception):
    """Raised when every configured provider for a capability errored on one call."""

    def __init__(self, capability: str, failures: list[tuple[str, str]]) -> None:
        self.capability = capability
        self.failures = failures
        detail = "; ".join(f"{name}={reason}" for name, reason in failures) or "no providers configured"

        super().__init__(f"all {capability} providers failed: {detail}")


class Provider:
    """A named web provider, active only when its API-key env var is set."""

    def __init__(self, name: str, env: str, fn: Callable) -> None:
        self.name = name
        self.env = env
        self.fn = fn

    def available(self) -> bool:
        return bool(os.getenv(self.env))


# Round-robin cursor per capability ("search"/"fetch"). Lock-free: a benign race only skews load.
_cursor: dict[str, int] = {}


def reset_cursor() -> None:
    """Clear the round-robin cursor so tests start from a known position."""
    _cursor.clear()


def _rotate(capability: str, active: list[Provider]):
    start = _cursor.get(capability, 0)
    _cursor[capability] = start + 1

    for offset in range(len(active)):
        yield active[(start + offset) % len(active)]


def dispatch(capability: str, providers: list[Provider], call: Callable, accept: Callable) -> object:
    """Round-robin across the available providers, failing over on error or unusable result.

    Returns the first result accepted by `accept`. If providers respond but none is usable (for
    example all empty), returns the last such result. If every configured provider errors, raises
    AllProvidersFailed naming each one.
    """
    active = [provider for provider in providers if provider.available()]
    errors: list[tuple[str, str]] = []
    empty_result, saw_empty = None, False

    for provider in _rotate(capability, active):
        try:
            result = call(provider.fn)
        except Exception as error:
            errors.append((provider.name, f"{type(error).__name__}: {error}"))

            continue

        if accept(result):
            return result

        empty_result, saw_empty = result, True

    if saw_empty:
        return empty_result

    raise AllProvidersFailed(capability, errors)

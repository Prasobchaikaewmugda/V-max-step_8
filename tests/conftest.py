"""Pytest + Hypothesis wiring for K-plane tests only."""

from __future__ import annotations

from hypothesis import settings

# Reproducible property tests: same examples for a given test body (no RNG drift across CI).
settings.register_profile(
    "kplane_deterministic",
    derandomize=True,
    max_examples=100,
)


def pytest_configure(config: object) -> None:
    settings.load_profile("kplane_deterministic")

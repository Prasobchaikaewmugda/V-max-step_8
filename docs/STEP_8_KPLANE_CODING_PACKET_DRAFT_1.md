# STEP_8_KPLANE_CODING_PACKET_DRAFT_1.md

STATUS: ACTIVE WORK PACKET
OWNER: Delivery Engineer
TRUTH_CLASS: implementation_packet
NOT_RUNTIME_TRUTH: YES
BOUND_BY:
- `149_STEP8_LAWFUL_HANDOFF_KPLANE_CODING_AUTHORIZATION.md`

## PURPOSE

This packet opens only the narrow K-plane coding lane already authorized by `149_`.

It contains:

- one local-stream K-plane protocol scaffold
- one AF_UNIX / SOCK_STREAM transport scaffold
- one local test suite for fail-closed parsing and typed K-lane handling

It does **not** contain:

- trading logic
- rollout logic
- topology law
- vendor mandate
- H-plane / D-plane / Watchdog implementation code

## WHERE THE CODE LIVES

Canonical Python sources and tests are **only** under the `step8_kplane_packet/` directory (`src/`, `tests/`). This `docs/` folder under `step8_kplane_packet/` holds governance markdown only — **no** `.py` implementation or test files here.

## FILES IN THIS PACKET

- `step8_kplane_packet/pyproject.toml` — `uv`, Ruff, mypy, pytest, Hypothesis
- `step8_kplane_packet/src/kplane_protocol.py`
- `step8_kplane_packet/src/kplane_uds.py`
- `step8_kplane_packet/tests/test_kplane_protocol.py`
- `step8_kplane_packet/tests/test_kplane_uds.py`
- `step8_kplane_packet/tests/test_kplane_hypothesis.py` — property / fuzz (after deterministic suite is green)
- `step8_kplane_packet/tests/conftest.py` — pytest + Hypothesis profile wiring

## IMPLEMENTATION BOUNDARY

Authorized scope covered here:

- Local Stream IPC / UDS
- K framing & parsing
- typed K-lane handling (`CONTROL`, `HEARTBEAT`, `REVERSE_ACK`)
- fail-closed rejection on malformed / ambiguous / oversized **frame** input (parser)
- **Receive path (`recv_message`):** each call uses a **positive wall-clock budget** (default 60s) for
  the full length-prefix + body read; no public API disables this. Raises only `ProtocolError`
  (including wrapped socket errors). This bounds the prior “stall after declared length” seam for
  **receive** only, as covered by unit tests—not a claim of full transport adversarial coverage.
- **Send path (`send_message`):** each call uses the same style of **positive deadline** (default 60s)
  for completing the framed write, with the same exception contract.
- Hypothesis exercises **randomized** parser/UDS inputs within stated **size** bounds; it does not
  prove safety against arbitrary peer behavior beyond what those tests assert.

Still closed:

- H-plane code
- D-plane code
- Watchdog implementation
- Execution / trading logic
- rollout / deployment / topology
- vendor-product choices as governance truth

## CURSOR SCOPING INSTRUCTION

Use only these files in active coding context:

- `@step8_kplane_packet/src/kplane_protocol.py`
- `@step8_kplane_packet/src/kplane_uds.py`
- `@step8_kplane_packet/tests/test_kplane_protocol.py`
- `@step8_kplane_packet/tests/test_kplane_uds.py`
- `@step8_kplane_packet/tests/test_kplane_hypothesis.py`
- `@step8_kplane_packet/pyproject.toml`

Do not pull broader repo context unless a contradiction claim requires it.

## LOCAL RUN

```bash
cd step8_kplane_packet
uv sync --extra dev
```

**Deterministic suite first (unittest-style tests):**

```bash
uv run pytest tests/test_kplane_protocol.py tests/test_kplane_uds.py -q
# or: uv run pytest -m "not hypothesis" -q
```

**Full suite (includes Hypothesis):**

```bash
uv run pytest
```

Legacy unittest (from `step8_kplane_packet/`):

```bash
python -m unittest discover -s tests -t src -v
```

## DELIVERY NOTE

This packet is a scaffold, not a claim of completion.
Any expansion beyond the K-plane boundary requires a separate lawful handoff.

# STEP_8_KPLANE_HARDENING_PASS_PACKET_DRAFT_1.md

STATUS: ACTIVE WORK PACKET
OWNER: Delivery Engineer
TRUTH_CLASS: implementation_packet
NOT_RUNTIME_TRUTH: YES
NOT_CANONICAL_LOCK: YES
NOT_IMPLEMENTATION_MANDATE: YES

BOUND_BY:
- `149_STEP8_LAWFUL_HANDOFF_KPLANE_CODING_AUTHORIZATION.md`
- `STEP_8_KPLANE_CODING_PACKET_DRAFT_1.md`

---

## 1. PURPOSE

This packet defines the next lawful implementation round inside `wf149active`.

This round is:

- **K-plane hardening only**
- **repo hygiene + deterministic green + fail-closed hardening + hypothesis stabilization**
- **not** a new battlefront
- **not** a reviewer pack
- **not** non-K expansion
- **not** runtime substrate expansion
- **not** rollout / topology / vendor work

---

## 2. CURRENT TARGET

### SINGLE IMPLEMENTATION OBJECTIVE

Stabilize the K-plane local implementation boundary so that:

1. repo structure is clean
2. deterministic tests are green
3. fail-closed cases are explicitly covered
4. Hypothesis property tests (randomized inputs within configured bounds) are stabilized
5. no non-K contamination exists

---

## 3. APPS / TOOLS TO USE

## Destination
Delivery Engineer

### Obsidian = Law
**Use for:**
- reading the active handoff
- reading locked Step 7 K artifacts
- confirming what is allowed vs forbidden

**Why this app:**
- Obsidian is the governance / truth vault
- use it to prevent scope drift before coding starts

**Input/context needed:**
- `149_STEP8_LAWFUL_HANDOFF_KPLANE_CODING_AUTHORIZATION.md`
- `STEP_8_KPLANE_CODING_PACKET_DRAFT_1.md`
- locked Step 7 K artifacts only

### Cursor Composer / Sonnet = Scaffolder
**Use for:**
- narrow code patching
- repo cleanup
- targeted parser / test edits

**Why this app:**
- Cursor is best used for high-speed narrow-scope code scaffolding
- it must not be used as repo-wide architecture brain

**Input/context needed:**
Only these files:
- `@src/kplane_protocol.py`
- `@src/kplane_uds.py`
- `@tests/test_kplane_protocol.py`
- `@tests/test_kplane_uds.py`
- `@tests/test_kplane_hypothesis.py`
- `@STEP_8_KPLANE_CODING_PACKET_DRAFT_1.md`
- `@STEP_8_KPLANE_HARDENING_PASS_PACKET_DRAFT_1.md`

### PyCharm Professional = Court
**Use for:**
- run/debug/test
- inspect socket / parser failures
- run local commands
- inspect failing hypothesis examples

**Why this app:**
- PyCharm is the correct execution/debugging court for implementation truth
- deterministic debugging belongs here, not in chat

**Input/context needed:**
- local repo
- `src/`
- `tests/`
- project interpreter / env

### Git = Evidence Chain
**Use for:**
- checkpoint each completed pass
- preserve rollback path
- isolate K-plane commits

**Why this app:**
- implementation without evidence chain becomes unrecoverable noise

**Input/context needed:**
- one clear pass boundary per commit

### uv = Reproducibility
**Use for:**
- running the project env
- dependency / environment consistency

**Why this app:**
- fast, reproducible Python workflow

**Input/context needed:**
- project root
- `pyproject.toml`

### Ruff = Hygiene
**Use for:**
- lint
- format checks

**Why this app:**
- clears style and hygiene noise before deeper review

**Input/context needed:**
- `src/`
- `tests/`

### mypy = Type Discipline
**Use for:**
- strict type checking on parser / IPC boundary code

**Why this app:**
- catches type confusion early
- critical for boundary parsing code

**Input/context needed:**
- typed `src/`
- typed `tests/`

### pytest = Deterministic Proof
**Use for:**
- stable unit/integration tests for local K-plane behavior

**Why this app:**
- deterministic proof must go green before fuzz/property testing

**Input/context needed:**
- `tests/test_kplane_protocol.py`
- `tests/test_kplane_uds.py`

### Hypothesis = Property testing
**Use for:**
- randomized frame bytes and chunking patterns within explicit size limits

**Why this app:**
- extra stress on parser/UDS paths; complements (does not replace) deterministic tests

**Input/context needed:**
- `tests/test_kplane_hypothesis.py`
- stable deterministic suite first

---

## 4. AUTHORIZED FILE BOUNDARY

### Source files allowed
- `src/kplane_protocol.py`
- `src/kplane_uds.py`
- `src/py.typed`

### Test files allowed
- `tests/conftest.py`
- `tests/test_kplane_protocol.py`
- `tests/test_kplane_uds.py`
- `tests/test_kplane_hypothesis.py`

### Packet / docs files allowed
- `STEP_8_KPLANE_CODING_PACKET_DRAFT_1.md`
- `STEP_8_KPLANE_HARDENING_PASS_PACKET_DRAFT_1.md`

### Must be removed or forbidden from coding location
- any `.py` file under `docs/`
- any `test_*.py` under `docs/`
- any H-plane / D-plane / Watchdog / Execution files
- rollout notes
- topology notes
- vendor/product notes

---

## 5. HARDENING PASSES

## PASS A — Repo Hygiene
### Goal
Clean the repo so implementation truth is not mixed with packet/docs truth.

### Required outcome
Repo shape must look like this:

```text
step8_kplane_packet/
  src/
    kplane_protocol.py
    kplane_uds.py
    py.typed
  tests/
    conftest.py
    test_kplane_protocol.py
    test_kplane_uds.py
    test_kplane_hypothesis.py
  docs/
    STEP_8_KPLANE_CODING_PACKET_DRAFT_1.md
    STEP_8_KPLANE_HARDENING_PASS_PACKET_DRAFT_1.md
  pyproject.toml
  .gitignore
```

### Definition of done
- no `.py` files remain under `docs/`
- no duplicated implementation files outside `src/`
- no duplicated test files outside `tests/`

### Commit name
`kplane: repo hygiene and scope cleanup`

---

## PASS B — Deterministic Green
### Goal
Get deterministic protocol + UDS tests green before hypothesis work.

### Required commands
```bash
uv run ruff check .
uv run mypy src tests
uv run pytest tests/test_kplane_protocol.py -q
uv run pytest tests/test_kplane_uds.py -q
```

### Must pass
- roundtrip typed message behavior
- unknown type reject
- zero-length frame reject
- oversized frame reject
- truncated frame reject
- malformed body reject
- unexpected EOF fail-closed
- AF_UNIX / SOCK_STREAM local-only boundary

### Definition of done
- Ruff passes
- mypy passes
- deterministic pytest files pass

### Commit name
`kplane: deterministic parser and uds tests green`

---

## PASS C — Fail-Closed Hardening
### Goal
Make parser reject behavior explicit; document **receive** and **send** deadlines on the UDS helpers
as implemented and tested—not a blanket “transport fail-closed proof.”

### Required law-preserving focus
- parser must reject malformed or ambiguous **frame** input (tests name concrete cases)
- `recv_message` / `send_message`: positive deadlines only; bounded read/write via socket timeout;
  `ProtocolError` only at this API (including wrapped socket errors), as tests show
- typed lanes must remain:
  - `CONTROL`
  - `HEARTBEAT`
  - `REVERSE_ACK`
- no business logic may be added

### Definition of done
- parser fail-closed cases are visible in tests
- UDS deadline / EOF / garbage cases match the **worded** guarantees (receive + send), not broader claims
- no business semantics are introduced

### Commit name
`kplane: fail-closed boundary hardening`

---

## PASS D — Hypothesis Stabilization
### Goal
Stabilize Hypothesis property tests only after deterministic suite is green.

### Required command
```bash
uv run pytest tests/test_kplane_hypothesis.py -q
```

### If failing
- inspect concrete failing example in PyCharm
- patch narrowly in Cursor
- rerun only the affected hypothesis target
- do **not** widen scope
- do **not** add runtime/library expansion

### Definition of done
- hypothesis tests are stable enough to remain in suite
- or unstable hypothesis cases are quarantined explicitly without polluting deterministic green suite

### Commit name
`kplane: hypothesis property tests stabilized`

---

## 6. STRICT DO NOT DO

- Do **not** open H-plane code.
- Do **not** open D-plane code.
- Do **not** open Watchdog implementation code.
- Do **not** open Execution / trading logic.
- Do **not** introduce Rust / PyO3 / C++ substrate work in this round.
- Do **not** introduce CRC/runtime-expansion doctrine in this round.
- Do **not** start rollout / topology / vendor selection work.
- Do **not** send a reviewer pack while deterministic green is not established.
- Do **not** claim this round is lock-ready.

---

## 7. REVIEWER FORWARDING STATUS

### Can this be sent to reviewer / another review chat now?
**NOT YET**

### Why not yet
Because this round is still an **implementation hardening round**, not a reviewer round.

### Conditions before reviewer forwarding becomes lawful
- repo hygiene complete
- deterministic suite green
- fail-closed cases explicitly covered
- hypothesis stabilized or explicitly quarantined
- no non-K contamination remains
- then a separate internal status summary may be prepared

Until then:
- **do not send to reviewer chat**
- **do not package as adjudication material**
- **do not claim readiness for non-K expansion**

---

## 8. INTERNAL EXECUTION LOOP

1. **Read law in Obsidian**
2. **Run/debug current failures in PyCharm**
3. **Patch narrowly in Cursor Composer / Sonnet**
4. **Run gates in PyCharm terminal**
5. **Commit in Git only after a pass is actually complete**

### Gate order
1. Ruff
2. mypy
3. pytest deterministic
4. Hypothesis

---

## 9. SUCCESS CRITERIA FOR THIS PACKET

This packet is successful only if all of the following are true:

- K-plane scope stayed narrow
- repo structure is clean
- deterministic suite is green
- parser fail-closed behavior and **stated** UDS receive/send deadline behavior are covered by tests
- hypothesis work is stabilized or cleanly quarantined
- no reviewer forwarding occurred too early

---

END OF PACKET

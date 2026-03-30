# CHAT1_ROUTING_AF_UNIX_EVIDENCE_PACKET.md

**Destination:** Chat 1 (Workflow Control / routing review)  
**NOT** reviewer-forward — no Chat 3 hostile-review question in this round.  
**Scope:** K-plane transport evidence only (`wf149active`, `149_STEP8_LAWFUL_HANDOFF_KPLANE_CODING_AUTHORIZATION.md` ACTIVE).

---

## 1. Exact platform used for AF_UNIX proof

**On this Delivery Engineer session (Windows host, agent execution):**

- **No AF_UNIX proof was produced here.** Windows CPython reports `socket.AF_UNIX` absent (`win32`); UDS/socketpair-dependent tests are skipped in the full suite.
- **WSL2:** attempted; failed — `Failed to attach disk ... ext4.vhdx ... PATH_NOT_FOUND` (WSL instance not usable on this machine).
- **Docker:** not installed / not on `PATH`.

**Canonical platform class for the required transport-level proof:** **Linux or macOS** with working `AF_UNIX` + `SOCK_STREAM` `socket.socketpair()` (same K-plane code, same tests).

**Operational procedure:** Run `bash scripts/run_linux_af_unix_gates.sh` from `step8_kplane_packet/` on such a host after `uv sync --extra dev`. Optional: `LOG=linux_af_unix_gate_transcript.txt bash scripts/run_linux_af_unix_gates.sh` to capture a single verbatim transcript file.

---

## 2. Exact commit/hash tested (this session)

| Artifact | Value |
|----------|--------|
| **K-plane `src/` + `tests/` + `docs/*` packet bodies (implementation anchor)** | `974f68634c9040a2bfedaea0bd8062c0f7b68e0f` |
| **Single-file hostile payload artifact (`HOSTILE_REVIEW_EXACT_PACKET_CHAT3.md`)** | `3ac2c97053a9da796f5fe3e0cb3acfa8028f563f` |
| **This Chat1 routing packet + `scripts/run_linux_af_unix_gates.sh`** | Use `git rev-parse HEAD` after checkout — must include these paths for reproducibility. |

**Note:** Linux/macOS re-runs must use the **same tree** (or a later K-plane-only commit) and attach the transcript; `git rev-parse HEAD` printed by the gate script must match the tree under test. Implementation bodies are still the `974f686` tree unless a new K-plane-only commit changes them.

---

## 3. Exact UDS/socketpair commands and verbatim results

### 3a) This session (Windows — **no** AF_UNIX path; evidence ceiling)

**Commands:**

```text
uv run python -c "import socket; print(hasattr(socket,'AF_UNIX')); import sys; print(sys.platform)"
```

**Verbatim result:**

```text
False
win32
```

**Full gate (Windows — parser + AF_INET guards; UDS path skipped):**

```text
uv run ruff check .
uv run mypy src tests
uv run pytest tests/ -v --tb=short
```

**Verbatim result (last run on this host):**

```text
All checks passed!
Success: no issues found in 6 source files
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.2, pluggy-1.6.0
rootdir: D:\VMAX\Cursor\step8_kplane_packet
configfile: pyproject.toml
plugins: hypothesis-6.151.10
collected 39 items

tests\test_kplane_hypothesis.py ....ss                                   [ 15%]
tests\test_kplane_protocol.py ..................                         [ 61%]
tests\test_kplane_uds.py ....sssssssssss                                 [100%]

======================= 26 passed, 13 skipped in 0.63s ========================
```

**Interpretation:** Skips are **UDS/socketpair** and **Hypothesis UDS** branches on Windows — they do **not** establish the relied-on AF_UNIX fail-closed transport behavior. This satisfies Chat 3’s **evidence-ceiling** defect (not a summary-proof defect).

### 3b) Linux/macOS (required for AF_UNIX proof)

**Commands:**

```bash
cd step8_kplane_packet
uv sync --extra dev
bash scripts/run_linux_af_unix_gates.sh
# or: LOG=linux_af_unix_gate_transcript.txt bash scripts/run_linux_af_unix_gates.sh
```

**Verbatim result:** **Not yet captured in this environment** — operator must run 3b on a suitable host and attach the transcript (or paste) for the next evidence round.

---

## 4. Proof of fail-closed transport on the exercised AF_UNIX path (what the suite proves when not skipped)

When `AF_UNIX` `socketpair` is available, the **same** tests exercise the K-plane UDS boundary:

- **`tests/test_kplane_uds.py` — `KPlaneUDSAFUnixTests`:** non-`AF_UNIX` stream rejected, `recv`/`send` positive deadlines, `socketpair` locality, `create_server_socket` rejects non-socket path without unlink, send/recv fail-closed shutdown after peer disconnect, garbage / oversize declared length / stall / EOF paths — all **`ProtocolError`**-only at the public API as documented.
- **`tests/test_kplane_hypothesis.py`:** `@_skip_uds_on_windows` — on Linux/macOS, property tests roundtrip and bounded-blob receive without non-`ProtocolError` escapes on the UDS path.

**No change to claims:** still **bounded I/O** (`recv_message` / `send_message`), **not** full-stack transport hardening; **no** business semantics.

---

## 5. Proof that claims remain scoped to K-plane only

- **Authorized surface:** local framing/parser + AF_UNIX `SOCK_STREAM` helpers in `src/kplane_protocol.py` / `src/kplane_uds.py` and K-plane tests only.
- **No H-plane, D-plane, Watchdog, execution/trading, rollout, topology, vendor/product** content added for this evidence path.
- **Script `scripts/run_linux_af_unix_gates.sh`** runs only `ruff`, `mypy`, `pytest` on existing `src/` + `tests/` — no new battlefront.

---

## 6. Whether Windows-only wording needs narrowing after AF_UNIX proof is added

**Yes — for hostile-review packets, not the implementation.**

- **Tests:** `test_kplane_hypothesis.py` already documents Windows skip for UDS — accurate; keep.
- **Evidence narrative:** When a Linux/macOS transcript exists, the **canonical transport proof** for the AF_UNIX path should be that transcript; Windows results remain **supplementary** (parser + AF_INET guard rails + skipped UDS count).
- **Optional next edit (later round, when Linux proof is attached):** tighten `HOSTILE_REVIEW_EXACT_PACKET_CHAT3.md` (or successor) **Section 0/1** to state explicitly: **primary transport verification = POSIX host with AF_UNIX socketpair**; Windows = partial coverage. **Do not** imply Windows-only gates suffice for UDS fail-closed.

---

## 7. Return packet for Chat 1 routing review only

| Item | Status |
|------|--------|
| **Reviewer-forward** | **Blocked** (no new AF_UNIX same-context transcript from this agent host). |
| **Governance-forward** | **Blocked** (no sequencing / lock reopen). |
| **Deliverables for Chat 1** | This file; `scripts/run_linux_af_unix_gates.sh`; honest blocker + reproducible Linux/macOS path. |
| **Next operator action** | Run §3b on Linux/macOS at commit `3ac2c97` (or agreed K-plane hash); attach **verbatim** transcript; then update hostile-review packet (separate round, not this routing packet). |

---

END OF CHAT1_ROUTING PACKET

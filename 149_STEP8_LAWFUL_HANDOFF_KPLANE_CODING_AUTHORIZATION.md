# 149_STEP8_LAWFUL_HANDOFF_KPLANE_CODING_AUTHORIZATION.md

STATUS: ACTIVE
OWNER: Strategic Chair / System Reviewer
TRUTH_CLASS: handoff_truth
NOT_RUNTIME_TRUTH: YES

## 1. CURRENT LOCKED BASELINE

The following artifacts are in force and remain non-reopenable within this handoff:

- `STEP_7_IMPLEMENTATION_ENTRY_BLUEPRINT_LOCKED.md`
- `STEP_7_COMPONENT_INTERFACE_AND_STATE_CONTRACTS_LOCKED.md`
  - If the canonical file is absent from the working tree, `STEP_7_COMPONENT_INTERFACE_AND_STATE_CONTRACTS_LOCKED_RESTORED.md` may be used as a workspace substitute only.
- `STEP_7_PROCESS_BOUNDARY_AND_CROSSING_MATRIX_LOCKED.md`
- `STEP_7_RESIDUAL_MECHANISM_BINDINGS_LOCKED.md`
- `STEP_7_K1_K2_K3_PRODUCTION_MECHANISM_SELECTION_LOCKED.md`
- `STEP_7_K1_K2_K3_PRODUCTION_IMPLEMENTATION_BOUNDARY_LOCKED.md`
- `STEP_7_EVIDENCE_BUFFER_MECHANISM_CLASS_SELECTION_LOCKED.md`
- `STEP_7_ISSUANCE_AUTHORITY_MECHANISM_CLASS_SELECTION_LOCKED.md`
- `STEP_7_WATCHDOG_OBSERVABILITY_MECHANISM_CLASS_SELECTION_LOCKED.md`

The following Step 8 governance artifacts are accepted and in force for sequencing only:

- `STEP_8_ENTRY_GATE_DRAFT_1.md`
- `STEP_8_FIRST_IMPLEMENTATION_BATTLEFRONT_SELECTION_DRAFT_2.md`

Program state before this handoff:

- `STEP_8_FIRST_IMPLEMENTATION_BATTLEFRONT_SELECTION_DRAFT_2.md = ACCEPTED`
- `K-plane = sole first Step 8 implementation battlefront`
- `non-K Step 8 battlefronts remain closed`
- `this sequencing artifact is NOT coding authorization`
- `Current program state = HOLD`

No rollout, topology, vendor/product mandate, or multi-front Step 8 opening has been authorized before this handoff.

---

## 2. NEXT SINGLE TARGET

**Authorize K-plane coding only** under one narrowly bounded implementation surface.

### Authorized implementation surface

The sole authorized Step 8 coding surface is:

`K-plane implementation boundary only`

This means downstream coding may address only the already locked K-plane boundary, including:

- connected local stream supervision carrier realization
- K framing / parsing boundary
- fail-closed rejection behavior for malformed or ambiguous K input
- typed K-lane handling required by locked law
- reverse-ACK ceiling preservation at the K boundary
- enforcement that the admitted K path remains local and does not widen into network-stack / public transport semantics

### This handoff unlocks only

- K-plane code scaffolding / implementation work
- K-plane-local tests directly tied to the locked K boundary
- K-plane parser / framing / local IPC code
- K-plane fail-closed behavior implementation

### This handoff does not unlock

- H-plane implementation
- D-plane implementation
- Watchdog observability implementation
- Execution / trading logic implementation
- rollout planning
- topology law
- vendor/product mandate
- multi-front Step 8 coding

---

## 3. WHY THIS TARGET IS NOW LAWFUL

This target is now lawful because:

- Step 8 governance entry has already been opened at the entry-gate layer
- the first implementation battlefront has already been selected and accepted as `K-plane only`
- the K-plane is the narrowest, most load-bearing, and least domain-specific first implementation surface
- this move remains downstream of locked Step 7 law and does not reopen mechanism selection
- this move still does not authorize rollout, topology lock, or vendor/product doctrine
- this move preserves single-front sequencing discipline at Step 8

Institutional reading:

This handoff is the first lawful permission to write implementation code, but only inside the K-plane boundary already fixed by locked Step 7 law and Step 8 sequencing acceptance.

---

## 4. MUST NOT DO

- Do **not** reopen Step 4 / Step 5 / Step 6.
- Do **not** reopen locked Step 7 artifacts.
- Do **not** reopen accepted Step 8 sequencing artifacts.
- Do **not** open H-plane, D-plane, Watchdog implementation, or Execution / trading implementation.
- Do **not** authorize or perform rollout planning, deployment planning, topology design, or vendor/product selection as governance truth.
- Do **not** widen from local connected stream K-plane semantics into network-stack, loopback-IP, service-bus, or public transport semantics.
- Do **not** smuggle venue adapters, Ledger ingestion, Evidence Buffer integration, Issuance workflows, or observability platform work into this coding lane.
- Do **not** open more than one Step 8 implementation front.
- Do **not** treat this handoff as blanket permission to code the system.
- Do **not** pull old draft chains unless a contradiction claim requires proof.

---

## 5. FILES ALLOWED IN CONTEXT

Only the following files are admissible in context for this K-plane coding lane:

- `@01_VMAX_ROLE_AND_AUTHORITY_MAP.md`
- `@STEP_7_IMPLEMENTATION_ENTRY_BLUEPRINT_LOCKED.md`
- `@STEP_7_COMPONENT_INTERFACE_AND_STATE_CONTRACTS_LOCKED.md`
  - If missing in workspace: `@STEP_7_COMPONENT_INTERFACE_AND_STATE_CONTRACTS_LOCKED_RESTORED.md`
- `@STEP_7_PROCESS_BOUNDARY_AND_CROSSING_MATRIX_LOCKED.md`
- `@STEP_7_K1_K2_K3_PRODUCTION_MECHANISM_SELECTION_LOCKED.md`
- `@STEP_7_K1_K2_K3_PRODUCTION_IMPLEMENTATION_BOUNDARY_LOCKED.md`
- `@STEP_8_ENTRY_GATE_DRAFT_1.md`
- `@STEP_8_FIRST_IMPLEMENTATION_BATTLEFRONT_SELECTION_DRAFT_2.md`
- this lawful handoff text

### Context exclusion rule

The following must remain excluded from this coding context unless a contradiction claim specifically requires them:

- Evidence Buffer implementation material
- Issuance implementation material
- Watchdog observability implementation material
- rollout notes
- topology notes
- vendor/product selection notes
- screenshots
- SQL
- unrelated Step 7 draft chains
- non-K Step 8 implementation plans

### Token discipline

- attach only the minimum locked and sequencing files needed for K-plane implementation
- do not attach broad repo context
- do not attach files from closed Step 8 battlefronts

---

## 6. ROUTING / HANDOFF

### Send to

- Workflow Control
- then Cursor Composer / Delivery Engineer

### Coding lane opened by this handoff

- K-plane implementation work only

### Explicitly still closed

- H-plane coding
- D-plane coding
- Watchdog implementation coding
- Execution / trading logic coding
- rollout execution
- deployment planning
- topology lock
- vendor/product mandate

### Status effect

- HOLD may be lifted for this single K-plane coding battlefront only
- no other Step 8 artifact or coding lane is authorized by implication

---

END OF HANDOFF

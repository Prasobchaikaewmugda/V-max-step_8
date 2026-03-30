"""Assemble HOSTILE_REVIEW_EXACT_PACKET_CHAT3.md from a single git commit + gate stdout."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = [
    "src/kplane_protocol.py",
    "src/kplane_uds.py",
    "tests/conftest.py",
    "tests/test_kplane_protocol.py",
    "tests/test_kplane_uds.py",
    "tests/test_kplane_hypothesis.py",
    "docs/STEP_8_KPLANE_CODING_PACKET_DRAFT_1.md",
    "docs/STEP_8_KPLANE_HARDENING_PASS_PACKET_DRAFT_1.md",
]


def _run(cmd: list[str]) -> str:
    p = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    out = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0:
        sys.stderr.write(out)
        raise SystemExit(p.returncode)
    return out


def git_show(commit: str, path: str) -> str:
    p = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if p.returncode != 0:
        sys.stderr.write(p.stderr or "")
        raise SystemExit(p.returncode)
    return p.stdout or ""


def verify_clean_paths(commit: str) -> None:
    diff = subprocess.run(
        ["git", "diff", commit, "--", *FILES],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if diff.stdout:
        sys.stderr.write(
            "ERROR: working tree differs from anchor for SECTION 2 paths:\n" + diff.stdout
        )
        raise SystemExit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--section1-from",
        metavar="FILE",
        help="Use FILE contents as SECTION 1 verbatim (e.g. stdout from "
        "scripts/chat3_linux_gates.sh on Linux at the same commit). "
        "If omitted, SECTION 1 is captured on this host via ruff/mypy/pytest.",
    )
    ap.add_argument(
        "--anchor",
        metavar="COMMIT",
        default=None,
        help="Commit for SECTION 2 (`git show`) and SECTION 0 anchor text. "
        "Default: HEAD. Use when committing the packet one commit after the "
        "implementation snapshot so the label still names the code commit.",
    )
    args = ap.parse_args()

    commit = args.anchor
    if commit is None:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    commit = subprocess.run(
        ["git", "rev-parse", commit],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    commit_short = subprocess.run(
        ["git", "rev-parse", "--short", commit],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    verify_clean_paths(commit)

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    if args.section1_from:
        section1_body = Path(args.section1_from).read_text(encoding="utf-8")
        section1_note = (
            f"SECTION 1 transcript: verbatim from file {args.section1_from!r}; produced for the "
            f"same implementation anchor commit {commit} (e.g. `bash scripts/chat3_linux_gates.sh` "
            "on Linux at that checkout, or GitHub Actions artifact `chat3-linux-section1`). "
            "This is not a Windows/win32 gate transcript."
        )
    else:
        ruff_out = _run(["uv", "run", "ruff", "check", "."]).rstrip() + "\n"
        mypy_out = _run(["uv", "run", "mypy", "src", "tests"]).rstrip() + "\n"
        pytest_out = _run(["uv", "run", "pytest", "tests/", "-v", "--tb=short"]).rstrip() + "\n"
        section1_body = "\n".join(
            [
                "Command: uv run ruff check .",
                "--- stdout ---",
                ruff_out.rstrip("\n"),
                "",
                "Command: uv run mypy src tests",
                "--- stdout ---",
                mypy_out.rstrip("\n"),
                "",
                "Command: uv run pytest tests/ -v --tb=short",
                "--- stdout ---",
                pytest_out.rstrip("\n"),
            ]
        )
        section1_note = (
            "SECTION 1 transcript: captured immediately before assembly from this clone; "
            "`git diff <anchor> -- <SECTION 2 paths>` was empty. "
            "Environment: Windows, uv-managed Python."
        )

    lines: list[str] = []
    append_line = lines.append

    append_line("HOSTILE REVIEW — EXACT PAYLOAD PACKET (single file)")
    append_line("Scope: K-plane implementation boundary only. Not H/D-plane, rollout, or topology.")
    append_line("")
    append_line("=" * 80)
    append_line("SECTION 0 — LINKAGE AND COMMIT ANCHOR (single implementation object)")
    append_line("=" * 80)
    append_line(
        "Implementation anchor (full) — SECTION 2 bodies and the intended SECTION 1 gate run: "
        f"{commit}"
    )
    append_line(
        f"Short: {commit_short}. SECTION 2 is always `git show {commit_short}:<path>` for the "
        "listed paths; SECTION 1 must be a gate transcript from that same tree (Linux/POSIX for "
        "AF_UNIX/UDS same-context proof), not a different implementation commit."
    )
    append_line(
        f"Packet artifact / assembly tip commit may differ from the implementation anchor: "
        f"repository HEAD at assembly is {head}. "
        f"If HEAD != {commit_short}, only tooling/packet files changed after {commit_short}; "
        f"SECTION 2 paths still match anchor {commit}."
    )
    append_line(
        "SECTION 2 bodies below were produced with: "
        f"`git show {commit}:<path>` for each listed path (byte-for-byte)."
    )
    append_line(section1_note)
    if not args.section1_from:
        append_line(
            "For a Linux/POSIX SECTION 1 only: run `bash scripts/chat3_linux_gates.sh` on Linux "
            f"at `git checkout {commit}`, save stdout to a file, then regenerate this packet with "
            "`uv run python tools/assemble_unified_hostile_packet.py --anchor <same-commit> "
            "--section1-from <file>`."
        )
    append_line(
        "Prior artifacts (e.g. HOSTILE_REVIEW_EXACT_PAYLOAD_AND_GATES.txt) are superseded "
        "by this self-contained packet."
    )
    append_line("")
    append_line("=" * 80)
    append_line("SECTION 1 — VERBATIM GATE EVIDENCE (same commit as SECTION 0 / SECTION 2)")
    append_line("=" * 80)
    append_line(section1_body.rstrip("\n"))
    append_line("")
    append_line("=" * 80)
    append_line("SECTION 2 — EXACT FILE BODIES (full text, not summaries)")
    append_line("=" * 80)
    append_line("")

    for rel in FILES:
        body = git_show(commit, rel)
        append_line(f"<<< BEGIN FILE {rel} >>>")
        append_line(body.rstrip("\n"))
        append_line(f"<<< END FILE {rel} >>>")
        append_line("")

    out_path = ROOT / "HOSTILE_REVIEW_EXACT_PACKET_CHAT3.md"
    text = "\n".join(lines) + "\n"
    out_path.write_text(text, encoding="utf-8")
    print(f"Wrote {out_path} ({text.count(chr(10)) + 1} lines) anchor={commit}")


if __name__ == "__main__":
    main()

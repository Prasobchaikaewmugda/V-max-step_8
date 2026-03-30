HOSTILE REVIEW — EXACT PAYLOAD PACKET (single file)
Scope: K-plane implementation boundary only. Not H/D-plane, rollout, or topology.

================================================================================
SECTION 0 — LINKAGE AND COMMIT ANCHOR (single implementation object)
================================================================================
Exact commit anchor (full) for SECTION 2 bodies and for the repository state used to produce SECTION 1: 4db13f362f9404176834264fb40f1b678365bd90
Short: 4db13f3. This packet does not use commit 58ee2eb or any mixed anchor; transcript and file bodies refer to the same commit only.
Repository HEAD at packet assembly: 05b711ee3a802947c56051f846cd56c15c3ec5a1 (SECTION 2 listed paths match anchor 4db13f3; later commits may add only packet/tooling files).
SECTION 2 bodies below were produced with: `git show 4db13f362f9404176834264fb40f1b678365bd90:<path>` for each listed path (byte-for-byte).
SECTION 1 transcript: captured immediately before assembly from this clone; `git diff <anchor> -- <SECTION 2 paths>` was empty. Environment: Windows, uv-managed Python.
For a Linux/POSIX SECTION 1 only: run `bash scripts/chat3_linux_gates.sh` on Linux at `git checkout 4db13f362f9404176834264fb40f1b678365bd90`, save stdout to a file, then regenerate this packet with `uv run python tools/assemble_unified_hostile_packet.py --anchor <same-commit> --section1-from <file>`.
Prior artifacts (e.g. HOSTILE_REVIEW_EXACT_PAYLOAD_AND_GATES.txt) are superseded by this self-contained packet.

================================================================================
SECTION 1 — VERBATIM GATE EVIDENCE (same commit as SECTION 0 / SECTION 2)
================================================================================
Command: uv run ruff check .
--- stdout ---
All checks passed!

Command: uv run mypy src tests
--- stdout ---
Success: no issues found in 6 source files

Command: uv run pytest tests/ -v --tb=short
--- stdout ---
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.2, pluggy-1.6.0
rootdir: D:\VMAX\Cursor\step8_kplane_packet
configfile: pyproject.toml
plugins: hypothesis-6.151.10
collected 39 items

tests\test_kplane_hypothesis.py ....ss                                   [ 15%]
tests\test_kplane_protocol.py ..................                         [ 61%]
tests\test_kplane_uds.py ....sssssssssss                                 [100%]

======================= 26 passed, 13 skipped in 0.64s ========================

================================================================================
SECTION 2 — EXACT FILE BODIES (full text, not summaries)
================================================================================

<<< BEGIN FILE src/kplane_protocol.py >>>
from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum

# Conservative local boundary. Runtime tuning is deferred.
MAX_FRAME_SIZE = 64 * 1024
_LENGTH_PREFIX = struct.Struct(">I")


class ProtocolError(Exception):
    """Raised when K-plane input violates the locked fail-closed boundary."""


class MessageKind(IntEnum):
    CONTROL = 1
    HEARTBEAT = 2
    REVERSE_ACK = 3


@dataclass(frozen=True)
class KMessage:
    kind: MessageKind
    payload: bytes = b""


def encode_frame(message: KMessage) -> bytes:
    """Encode a K-plane message with a 4-byte big-endian length prefix.

    Frame body:
        1 byte  - message kind
        N bytes - payload

    This module preserves typed K-lane handling only.
    It does not elevate REVERSE_ACK beyond its locked ceiling.
    """
    body = bytes([int(message.kind)]) + message.payload
    if len(body) > MAX_FRAME_SIZE:
        raise ProtocolError("frame exceeds MAX_FRAME_SIZE")
    return _LENGTH_PREFIX.pack(len(body)) + body


def decode_frame(body: bytes) -> KMessage:
    """Decode one full frame body. Raises ProtocolError on any malformed input."""
    if not body:
        raise ProtocolError("empty frame body")
    if len(body) > MAX_FRAME_SIZE:
        raise ProtocolError("frame exceeds MAX_FRAME_SIZE")

    kind_value = body[0]
    try:
        kind = MessageKind(kind_value)
    except ValueError as exc:
        raise ProtocolError(f"unknown message kind: {kind_value}") from exc

    return KMessage(kind=kind, payload=body[1:])


class FrameReader:
    """Incremental parser for local stream K-plane traffic.

    Fail-closed behavior:
    - oversized length prefix => ProtocolError
    - unknown type => ProtocolError
    - non-empty trailing bytes at EOF => ProtocolError
    """

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[KMessage]:
        if not data:
            return []
        self._buffer.extend(data)
        messages: list[KMessage] = []

        while True:
            if len(self._buffer) < _LENGTH_PREFIX.size:
                return messages

            frame_len = _LENGTH_PREFIX.unpack(self._buffer[: _LENGTH_PREFIX.size])[0]
            if frame_len == 0:
                raise ProtocolError("zero-length frame is forbidden")
            if frame_len > MAX_FRAME_SIZE:
                raise ProtocolError("declared frame length exceeds MAX_FRAME_SIZE")

            total = _LENGTH_PREFIX.size + frame_len
            if len(self._buffer) < total:
                return messages

            body = bytes(self._buffer[_LENGTH_PREFIX.size : total])
            del self._buffer[:total]
            messages.append(decode_frame(body))

    def feed_eof(self) -> None:
        if self._buffer:
            raise ProtocolError("truncated frame at EOF")
<<< END FILE src/kplane_protocol.py >>>

<<< BEGIN FILE src/kplane_uds.py >>>
from __future__ import annotations

import contextlib
import os
import socket
import stat
import time
from pathlib import Path

from kplane_protocol import MAX_FRAME_SIZE, KMessage, ProtocolError, decode_frame, encode_frame

# Default wall-clock budget for one bounded UDS operation (send or full recv). Must be positive.
DEFAULT_UDS_DEADLINE_SEC: float = 60.0

# Typeshed omits AF_UNIX on some platforms (e.g. Windows); CPython may still define it at runtime.
AF_UNIX_FAMILY: int = getattr(socket, "AF_UNIX", -1)


def _is_unix_stream(sock: socket.socket) -> bool:
    """True only for AF_UNIX + SOCK_STREAM (flags on type masked).

    Portability: ``SOCK_STREAM`` is masked with ``0xF`` so platforms that OR extra type bits
    (e.g. ``SOCK_NONBLOCK``) still classify as stream. This is a heuristic, not a kernel guarantee.
    """
    if sock.family != AF_UNIX_FAMILY:
        return False
    masked = sock.type
    if hasattr(socket, "SOCK_NONBLOCK"):
        masked &= ~socket.SOCK_NONBLOCK
    # Windows may not define SOCK_NONBLOCK; mask common flag bits if present
    return (masked & 0xF) == socket.SOCK_STREAM


def create_server_socket(path: str, backlog: int = 1) -> socket.socket:
    """Create a local AF_UNIX / SOCK_STREAM listener (thin helper; no I/O deadlines here).

    If *path* already exists, it must be a socket inode (e.g. stale ``bind``); otherwise fail closed
    without unlinking (avoids deleting arbitrary files).

    This is **not** race-free against concurrent creation/replacement of *path* by another process:
    the ``lstat`` / ``unlink`` sequence is best-effort for the common single-writer case only.
    """
    sock_path = Path(path)
    if sock_path.exists():
        if not stat.S_ISSOCK(sock_path.lstat().st_mode):
            raise ProtocolError(f"path exists and is not a socket: {sock_path}")
        os.unlink(sock_path)

    server = socket.socket(AF_UNIX_FAMILY, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    server.listen(backlog)
    return server


def connect_client(path: str) -> socket.socket:
    """Connect to a local AF_UNIX / SOCK_STREAM path (thin helper; blocking ``connect`` only)."""
    client = socket.socket(AF_UNIX_FAMILY, socket.SOCK_STREAM)
    client.connect(path)
    return client


def recv_exact(sock: socket.socket, nbytes: int, *, deadline: float) -> bytes:
    """Read exactly nbytes before monotonic *deadline*, or raise ProtocolError.

    OSError from the socket is normalized to ProtocolError (single boundary contract).
    """
    chunks = bytearray()
    while len(chunks) < nbytes:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProtocolError("recv stalled: deadline exceeded before completing read")
        sock.settimeout(remaining)
        try:
            chunk = sock.recv(nbytes - len(chunks))
        except OSError as exc:
            raise ProtocolError(f"transport: {exc}") from exc
        if not chunk:
            raise ProtocolError("unexpected EOF on stream")
        chunks.extend(chunk)
    return bytes(chunks)


def _sendall_bounded(sock: socket.socket, data: bytes, *, deadline: float) -> None:
    """Write all *data* before *deadline*; OSError -> ProtocolError."""
    sent = 0
    while sent < len(data):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProtocolError("send stalled: deadline exceeded before completing send")
        sock.settimeout(remaining)
        try:
            n = sock.send(data[sent:])
        except OSError as exc:
            raise ProtocolError(f"transport: {exc}") from exc
        if n == 0:
            raise ProtocolError("send made no progress")
        sent += n


def send_message(
    sock: socket.socket,
    message: KMessage,
    *,
    send_deadline_sec: float = DEFAULT_UDS_DEADLINE_SEC,
) -> None:
    """Send one framed message; bounded by *send_deadline_sec* (must be > 0).

    Raises ``ProtocolError`` for invalid deadline, wrong socket type, framing, or transport.
    On failure once any byte may have been written, the socket is fail-closed like ``recv_message``.
    """
    if send_deadline_sec <= 0:
        raise ProtocolError("send_deadline_sec must be positive")
    if not _is_unix_stream(sock):
        raise ProtocolError("socket must be AF_UNIX SOCK_STREAM")
    payload = encode_frame(message)
    deadline = time.monotonic() + float(send_deadline_sec)
    old_timeout = sock.gettimeout()
    try:
        _sendall_bounded(sock, payload, deadline=deadline)
    except ProtocolError:
        _fail_closed_shutdown(sock)
        raise
    finally:
        with contextlib.suppress(OSError):
            sock.settimeout(old_timeout)


def recv_message(
    sock: socket.socket,
    *,
    recv_deadline_sec: float = DEFAULT_UDS_DEADLINE_SEC,
) -> KMessage:
    """Receive one message and fail closed on malformed input.

    *recv_deadline_sec*: wall-clock budget for the entire message (prefix + body); must be > 0.
    There is no public API to disable this budget.

    Raises only :class:`ProtocolError` (invalid deadline, framing, EOF, stall/deadline, transport).
    """
    if recv_deadline_sec <= 0:
        raise ProtocolError("recv_deadline_sec must be positive")
    if not _is_unix_stream(sock):
        raise ProtocolError("socket must be AF_UNIX SOCK_STREAM")
    deadline = time.monotonic() + float(recv_deadline_sec)
    old_timeout = sock.gettimeout()
    try:
        header = recv_exact(sock, 4, deadline=deadline)
        frame_len = int.from_bytes(header, "big", signed=False)
        if frame_len == 0:
            raise ProtocolError("zero-length frame is forbidden")
        if frame_len > MAX_FRAME_SIZE:
            raise ProtocolError("declared frame length exceeds MAX_FRAME_SIZE")
        body = recv_exact(sock, frame_len, deadline=deadline)
        return decode_frame(body)
    except ProtocolError:
        _fail_closed_shutdown(sock)
        raise
    finally:
        with contextlib.suppress(OSError):
            sock.settimeout(old_timeout)


def _fail_closed_shutdown(sock: socket.socket) -> None:
    with contextlib.suppress(OSError):
        sock.shutdown(socket.SHUT_RDWR)
    with contextlib.suppress(OSError):
        sock.close()


def socketpair() -> tuple[socket.socket, socket.socket]:
    """Local full-duplex AF_UNIX / SOCK_STREAM pair for tests only."""
    return socket.socketpair(AF_UNIX_FAMILY, socket.SOCK_STREAM)
<<< END FILE src/kplane_uds.py >>>

<<< BEGIN FILE tests/test_kplane_protocol.py >>>
from __future__ import annotations

import unittest

from kplane_protocol import (
    MAX_FRAME_SIZE,
    FrameReader,
    KMessage,
    MessageKind,
    ProtocolError,
    decode_frame,
    encode_frame,
)


class TestFailClosedParser(unittest.TestCase):
    """Explicit fail-closed cases for the incremental parser and frame body decoder."""

    def test_unknown_kind_zero_rejected(self) -> None:
        with self.assertRaises(ProtocolError):
            decode_frame(bytes([0]))

    def test_feed_eof_clean_after_empty_feed(self) -> None:
        reader = FrameReader()
        self.assertEqual(reader.feed(b""), [])
        reader.feed_eof()


class KPlaneProtocolTests(unittest.TestCase):
    def test_roundtrip_control(self) -> None:
        original = KMessage(MessageKind.CONTROL, b"halt")
        wire = encode_frame(original)
        reader = FrameReader()
        messages = reader.feed(wire)
        self.assertEqual(messages, [original])

    def test_roundtrip_heartbeat(self) -> None:
        original = KMessage(MessageKind.HEARTBEAT, b"hb")
        wire = encode_frame(original)
        body = wire[4:]
        self.assertEqual(decode_frame(body), original)

    def test_roundtrip_reverse_ack(self) -> None:
        original = KMessage(MessageKind.REVERSE_ACK, b"ack")
        wire = encode_frame(original)
        body = wire[4:]
        self.assertEqual(decode_frame(body), original)

    def test_unknown_kind_rejected(self) -> None:
        with self.assertRaises(ProtocolError):
            decode_frame(bytes([99]) + b"junk")

    def test_zero_length_frame_rejected(self) -> None:
        reader = FrameReader()
        with self.assertRaises(ProtocolError):
            reader.feed((0).to_bytes(4, "big"))

    def test_oversized_declared_frame_rejected(self) -> None:
        reader = FrameReader()
        oversize = (MAX_FRAME_SIZE + 1).to_bytes(4, "big")
        with self.assertRaises(ProtocolError):
            reader.feed(oversize)

    def test_truncated_frame_rejected_at_eof(self) -> None:
        original = KMessage(MessageKind.HEARTBEAT, b"abc")
        wire = encode_frame(original)
        reader = FrameReader()
        reader.feed(wire[:-1])
        with self.assertRaises(ProtocolError):
            reader.feed_eof()

    def test_multiple_frames_in_one_feed(self) -> None:
        m1 = KMessage(MessageKind.CONTROL, b"a")
        m2 = KMessage(MessageKind.HEARTBEAT, b"b")
        wire = encode_frame(m1) + encode_frame(m2)
        reader = FrameReader()
        messages = reader.feed(wire)
        self.assertEqual(messages, [m1, m2])
        self.assertEqual(reader.feed(b""), [])

    def test_incremental_feed_two_frames(self) -> None:
        m1 = KMessage(MessageKind.CONTROL, b"x")
        m2 = KMessage(MessageKind.REVERSE_ACK, b"y")
        w1 = encode_frame(m1)
        w2 = encode_frame(m2)
        reader = FrameReader()
        mid = len(w1) // 2
        self.assertEqual(reader.feed(w1[:mid]), [])
        self.assertEqual(reader.feed(w1[mid:] + w2[:1]), [m1])
        self.assertEqual(reader.feed(w2[1:]), [m2])

    def test_empty_frame_body_rejected(self) -> None:
        with self.assertRaises(ProtocolError):
            decode_frame(b"")

    def test_encode_max_body_size(self) -> None:
        payload = b"\x00" * (MAX_FRAME_SIZE - 1)
        msg = KMessage(MessageKind.HEARTBEAT, payload)
        wire = encode_frame(msg)
        reader = FrameReader()
        self.assertEqual(reader.feed(wire), [msg])

    def test_encode_rejects_body_too_large(self) -> None:
        payload = b"\x00" * MAX_FRAME_SIZE
        msg = KMessage(MessageKind.HEARTBEAT, payload)
        with self.assertRaises(ProtocolError):
            encode_frame(msg)

    def test_decode_rejects_body_longer_than_max(self) -> None:
        body = bytes([MessageKind.CONTROL]) + b"\x00" * MAX_FRAME_SIZE
        with self.assertRaises(ProtocolError):
            decode_frame(body)

    def test_feed_eof_rejects_incomplete_length_prefix(self) -> None:
        reader = FrameReader()
        reader.feed(b"\x00\x01")
        with self.assertRaises(ProtocolError):
            reader.feed_eof()

    def test_feed_eof_rejects_trailing_byte_after_full_frame(self) -> None:
        wire = encode_frame(KMessage(MessageKind.HEARTBEAT, b"z"))
        reader = FrameReader()
        reader.feed(wire + b"\x01")
        with self.assertRaises(ProtocolError):
            reader.feed_eof()

    def test_length_prefix_uint32_max_rejected(self) -> None:
        reader = FrameReader()
        with self.assertRaises(ProtocolError):
            reader.feed((0xFFFFFFFF).to_bytes(4, "big"))


if __name__ == "__main__":
    unittest.main()
<<< END FILE tests/test_kplane_protocol.py >>>

<<< BEGIN FILE tests/test_kplane_uds.py >>>
from __future__ import annotations

import contextlib
import socket
import tempfile
import unittest
from pathlib import Path

from kplane_protocol import MAX_FRAME_SIZE, KMessage, MessageKind, ProtocolError, encode_frame
from kplane_uds import (
    AF_UNIX_FAMILY,
    _is_unix_stream,
    create_server_socket,
    recv_message,
    send_message,
    socketpair,
)


def _af_unix_socketpair_available() -> bool:
    if not hasattr(socket, "AF_UNIX"):
        return False
    try:
        a, b = socketpair()
        a.close()
        b.close()
        return True
    except OSError:
        return False


class KPlaneUDSInetTests(unittest.TestCase):
    """AF_INET guards — do not require AF_UNIX socketpair."""

    def test_non_unix_socket_rejected(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with self.assertRaises(ProtocolError):
                send_message(s, KMessage(MessageKind.HEARTBEAT, b"x"))
        finally:
            s.close()

    def test_recv_non_unix_socket_rejected(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with self.assertRaises(ProtocolError):
                recv_message(s)
        finally:
            s.close()

    def test_recv_deadline_must_be_positive(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with self.assertRaises(ProtocolError):
                recv_message(s, recv_deadline_sec=0.0)
        finally:
            s.close()

    def test_send_deadline_must_be_positive(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with self.assertRaises(ProtocolError):
                send_message(s, KMessage(MessageKind.HEARTBEAT, b"x"), send_deadline_sec=0.0)
        finally:
            s.close()


@unittest.skipUnless(
    _af_unix_socketpair_available(),
    "AF_UNIX SOCK_STREAM socketpair not available",
)
class KPlaneUDSAFUnixTests(unittest.TestCase):
    """AF_UNIX / SOCK_STREAM transport: fail-closed on garbage, EOF, and oversize."""

    def test_socketpair_is_local_stream(self) -> None:
        left, right = socketpair()
        try:
            self.assertEqual(left.family, AF_UNIX_FAMILY)
            self.assertEqual(left.type & socket.SOCK_STREAM, socket.SOCK_STREAM)
            self.assertEqual(right.family, AF_UNIX_FAMILY)
            self.assertEqual(right.type & socket.SOCK_STREAM, socket.SOCK_STREAM)
            # _is_unix_stream must agree with real AF_UNIX stream sockets from socketpair()
            self.assertTrue(_is_unix_stream(left))
            self.assertTrue(_is_unix_stream(right))
        finally:
            left.close()
            right.close()

    def test_create_server_rejects_existing_non_socket_path(self) -> None:
        """Regular file at bind path: fail closed; do not unlink arbitrary data."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sockpath"
            p.write_bytes(b"not a socket")
            with self.assertRaises(ProtocolError) as ctx:
                create_server_socket(str(p))
            self.assertIn("not a socket", str(ctx.exception).lower())

    def test_send_fail_closed_closes_socket_after_peer_disconnect(self) -> None:
        """After send_message fails mid-path, socket must not be left open for ambiguous reuse."""
        left, right = socketpair()
        try:
            right.close()
            with self.assertRaises(ProtocolError):
                send_message(left, KMessage(MessageKind.HEARTBEAT, b"x" * 4096))
            with self.assertRaises(OSError):
                left.send(b"z")
            with self.assertRaises(ProtocolError):
                send_message(left, KMessage(MessageKind.HEARTBEAT, b"a"))
        finally:
            with contextlib.suppress(OSError):
                left.close()

    def test_send_receive_roundtrip(self) -> None:
        left, right = socketpair()
        try:
            send_message(left, KMessage(MessageKind.HEARTBEAT, b"hb"))
            received = recv_message(right)
            self.assertEqual(received, KMessage(MessageKind.HEARTBEAT, b"hb"))
        finally:
            left.close()
            with contextlib.suppress(OSError):
                right.close()

    def test_garbage_rejected_fail_closed(self) -> None:
        left, right = socketpair()
        try:
            left.sendall((3).to_bytes(4, "big") + bytes([255, 0, 0]))
            with self.assertRaises(ProtocolError):
                recv_message(right)
        finally:
            left.close()
            with contextlib.suppress(OSError):
                right.close()

    def test_recv_fail_closed_shuts_receiver_after_garbage(self) -> None:
        """Second recv on the same socket must not succeed after malformed frame handling."""
        left, right = socketpair()
        try:
            left.sendall((3).to_bytes(4, "big") + bytes([255, 0, 0]))
            with self.assertRaises(ProtocolError):
                recv_message(right)
            with self.assertRaises(ProtocolError):
                recv_message(right)
        finally:
            left.close()
            with contextlib.suppress(OSError):
                right.close()

    def test_stall_after_declared_length_protocol_error(self) -> None:
        """Peer declares a body length but sends nothing more: must not block past recv deadline."""
        left, right = socketpair()
        try:
            left.sendall((100).to_bytes(4, "big"))
            with self.assertRaises(ProtocolError) as ctx:
                recv_message(right, recv_deadline_sec=0.25)
            self.assertTrue(
                "transport:" in str(ctx.exception).lower()
                or "deadline" in str(ctx.exception).lower()
                or "stalled" in str(ctx.exception).lower(),
                msg=str(ctx.exception),
            )
        finally:
            left.close()
            with contextlib.suppress(OSError):
                right.close()

    def _close_pair(self, left: socket.socket, right: socket.socket) -> None:
        left.close()
        with contextlib.suppress(OSError):
            right.close()

    def test_disconnect_before_header_completes(self) -> None:
        left, right = socketpair()
        try:
            left.sendall(b"\x00\x01")
            left.shutdown(socket.SHUT_WR)
            with self.assertRaises(ProtocolError) as ctx:
                recv_message(right)
            self.assertIn("EOF", str(ctx.exception))
        finally:
            self._close_pair(left, right)

    def test_disconnect_mid_body_after_valid_header(self) -> None:
        left, right = socketpair()
        try:
            wire = encode_frame(KMessage(MessageKind.HEARTBEAT, b"x" * 40))
            left.sendall(wire[: 4 + 10])
            left.shutdown(socket.SHUT_WR)
            with self.assertRaises(ProtocolError) as ctx:
                recv_message(right)
            self.assertIn("EOF", str(ctx.exception))
        finally:
            self._close_pair(left, right)

    def test_declared_length_exceeds_max_rejected_before_body_read(self) -> None:
        left, right = socketpair()
        try:
            left.sendall((MAX_FRAME_SIZE + 1).to_bytes(4, "big"))
            left.shutdown(socket.SHUT_WR)
            with self.assertRaises(ProtocolError) as ctx:
                recv_message(right)
            self.assertIn("exceeds MAX_FRAME_SIZE", str(ctx.exception))
        finally:
            self._close_pair(left, right)

    def test_peer_shuts_down_write_before_any_byte(self) -> None:
        left, right = socketpair()
        try:
            left.shutdown(socket.SHUT_WR)
            with self.assertRaises(ProtocolError) as ctx:
                recv_message(right)
            self.assertIn("EOF", str(ctx.exception))
        finally:
            self._close_pair(left, right)


if __name__ == "__main__":
    unittest.main()
<<< END FILE tests/test_kplane_uds.py >>>

<<< BEGIN FILE tests/test_kplane_hypothesis.py >>>
"""Property-based and fuzz coverage for the K-plane parser (no domain semantics)."""

from __future__ import annotations

import contextlib
import sys
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from kplane_protocol import (
    MAX_FRAME_SIZE,
    FrameReader,
    KMessage,
    MessageKind,
    ProtocolError,
    decode_frame,
    encode_frame,
)
from kplane_uds import recv_message, send_message, socketpair

pytestmark = pytest.mark.hypothesis

_valid_kind = st.sampled_from(
    [MessageKind.CONTROL, MessageKind.HEARTBEAT, MessageKind.REVERSE_ACK]
)

# Windows CPython's socketpair does not support AF_UNIX; UDS coverage runs on Linux/macOS CI.
_skip_uds_on_windows = pytest.mark.skipif(
    sys.platform == "win32",
    reason="AF_UNIX UDS socketpair is not supported on Windows",
)


def _messages_strategy() -> st.SearchStrategy[KMessage]:
    return st.builds(KMessage, _valid_kind, st.binary(max_size=MAX_FRAME_SIZE - 1)).filter(
        lambda m: 1 + len(m.payload) <= MAX_FRAME_SIZE
    )


@given(msgs=st.lists(_messages_strategy(), max_size=24))
def test_encode_decode_roundtrip_frame_body(msgs: list[KMessage]) -> None:
    for m in msgs:
        wire = encode_frame(m)
        body = wire[4:]
        assert decode_frame(body) == m


@given(msgs=st.lists(_messages_strategy(), max_size=24), data=st.data())
def test_framereader_chunked_reassembly(msgs: list[KMessage], data: Any) -> None:
    wire = b"".join(encode_frame(m) for m in msgs)
    chunks: list[bytes] = []
    rest = wire
    while rest:
        take = data.draw(st.integers(1, len(rest)))
        chunks.append(rest[:take])
        rest = rest[take:]

    reader = FrameReader()
    out: list[KMessage] = []
    for c in chunks:
        out.extend(reader.feed(c))
    assert out == msgs
    reader.feed_eof()


@given(st.binary(max_size=600))
def test_framereader_feed_only_raises_protocol_error_or_ok(blob: bytes) -> None:
    reader = FrameReader()
    try:
        reader.feed(blob)
    except ProtocolError:
        return
    except Exception as exc:
        pytest.fail(f"FrameReader.feed must not raise except ProtocolError, got {exc!r}")


@given(st.binary(max_size=400))
def test_framereader_feed_eof_fail_closed(blob: bytes) -> None:
    reader = FrameReader()
    try:
        reader.feed(blob)
    except ProtocolError:
        return
    except Exception as exc:
        pytest.fail(f"FrameReader.feed must not raise except ProtocolError, got {exc!r}")
    try:
        reader.feed_eof()
    except ProtocolError:
        return
    except Exception as exc:
        pytest.fail(f"FrameReader.feed_eof must not raise except ProtocolError, got {exc!r}")


@_skip_uds_on_windows
@given(msg=_messages_strategy())
def test_uds_roundtrip_property(msg: KMessage) -> None:
    try:
        left, right = socketpair()
    except (OSError, ValueError):
        pytest.skip("AF_UNIX socketpair not available")
    try:
        send_message(left, msg)
        assert recv_message(right) == msg
    finally:
        left.close()
        with contextlib.suppress(OSError):
            right.close()


@_skip_uds_on_windows
@given(blob=st.binary(min_size=1, max_size=256))
def test_uds_recv_bounded_blob_never_uncaught(blob: bytes) -> None:
    try:
        left, right = socketpair()
    except (OSError, ValueError):
        pytest.skip("AF_UNIX socketpair not available")
    try:
        left.sendall(blob)
        try:
            recv_message(right)
        except ProtocolError:
            pass
        except Exception as exc:
            pytest.fail(f"recv_message must raise only ProtocolError, got {exc!r}")
    finally:
        left.close()
        with contextlib.suppress(OSError):
            right.close()
<<< END FILE tests/test_kplane_hypothesis.py >>>

<<< BEGIN FILE docs/STEP_8_KPLANE_CODING_PACKET_DRAFT_1.md >>>
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
- **Bounded I/O (only `send_message` / `recv_message`):** each call uses a **positive wall-clock budget**
  (default 60s) for that operation; no public API disables it. On failure after I/O may have started,
  the socket is fail-closed (shutdown/close). These entry points raise **only `ProtocolError`** for
  this boundary (invalid deadlines, framing, transport wraps, EOF/stall), as covered by unit tests.
  This is **not** a claim of full-stack “transport hardening.”
- **`create_server_socket` / `connect_client`:** thin helpers (bind/listen; blocking `connect` only).
  They do **not** apply send/recv deadlines. **`create_server_socket`:** if the path already exists,
  `lstat` must show a **socket** inode before unlink; otherwise `ProtocolError` and **no** unlink.
  This avoids accidental deletion of wrong inode types in the usual case; it does **not** assert
  safety against **concurrent** path mutation (TOCTOU/races are out of scope for this helper).
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
<<< END FILE docs/STEP_8_KPLANE_CODING_PACKET_DRAFT_1.md >>>

<<< BEGIN FILE docs/STEP_8_KPLANE_HARDENING_PASS_PACKET_DRAFT_1.md >>>
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
  fail-closed shutdown on failure after I/O may have started; **`ProtocolError` only** at this API
  (including non-positive deadlines), as tests show
- `create_server_socket` / `connect_client`: out of scope for deadline claims (raw helpers);
  `create_server_socket`: if path exists and is not a socket, `ProtocolError` and no unlink (see tests);
  **no** claim of atomicity vs concurrent path mutation
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

### Hostile review (exact payload)
This packet describes an **implementation hardening round**, not the review verdict itself. When hardening is complete—repo hygiene done, deterministic gates green (Ruff, mypy, deterministic pytest), fail-closed cases covered, hypothesis stabilized or explicitly quarantined, and no non-K contamination—the **exact payload** (authorized `src/`, `tests/`, and the K-plane packet docs bundled for the handoff) is the material forwarded to the **hostile-review** chat for adjudication.

### What stays forbidden
- Forwarding **before** deterministic green is established (same gate order as Section 8).
- Replacing the exact file payload with a **summary-only** or partial listing (prior rejection cause).
- Treating chat output as lock-ready authorization or non-K expansion approval—only the hostile reviewer’s stated verdict applies.

### Readiness checklist (before forwarding)
- repo hygiene complete
- deterministic suite green
- fail-closed cases explicitly covered
- hypothesis stabilized or explicitly quarantined
- no non-K contamination remains

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
<<< END FILE docs/STEP_8_KPLANE_HARDENING_PASS_PACKET_DRAFT_1.md >>>


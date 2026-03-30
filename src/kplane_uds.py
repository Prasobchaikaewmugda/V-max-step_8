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

    On failure once any byte may have been written, the socket is fail-closed like ``recv_message``.
    """
    if send_deadline_sec <= 0:
        raise ValueError("send_deadline_sec must be positive")
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

    Raises only :class:`ProtocolError` (framing, EOF, stall/deadline, wrapped transport).
    """
    if recv_deadline_sec <= 0:
        raise ValueError("recv_deadline_sec must be positive")
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

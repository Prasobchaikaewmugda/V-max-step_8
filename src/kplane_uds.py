from __future__ import annotations

import os
import socket
from pathlib import Path

from kplane_protocol import MAX_FRAME_SIZE, KMessage, ProtocolError, decode_frame, encode_frame


def _is_unix_stream(sock: socket.socket) -> bool:
    """True only for AF_UNIX + SOCK_STREAM (flags on type masked)."""
    if sock.family != socket.AF_UNIX:
        return False
    masked = sock.type
    if hasattr(socket, "SOCK_NONBLOCK"):
        masked &= ~socket.SOCK_NONBLOCK
    # Windows may not define SOCK_NONBLOCK; mask common flag bits if present
    return (masked & 0xF) == socket.SOCK_STREAM


def create_server_socket(path: str, backlog: int = 1) -> socket.socket:
    """Create a local AF_UNIX / SOCK_STREAM server socket only."""
    sock_path = Path(path)
    try:
        os.unlink(sock_path)
    except FileNotFoundError:
        pass

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    server.listen(backlog)
    return server


def connect_client(path: str) -> socket.socket:
    """Connect to a local AF_UNIX / SOCK_STREAM socket only."""
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(path)
    return client


def recv_exact(sock: socket.socket, nbytes: int) -> bytes:
    """Read exactly nbytes or raise ProtocolError on short / closed read."""
    chunks = bytearray()
    while len(chunks) < nbytes:
        chunk = sock.recv(nbytes - len(chunks))
        if not chunk:
            raise ProtocolError("unexpected EOF on stream")
        chunks.extend(chunk)
    return bytes(chunks)


def send_message(sock: socket.socket, message: KMessage) -> None:
    if not _is_unix_stream(sock):
        raise ProtocolError("socket must be AF_UNIX SOCK_STREAM")
    sock.sendall(encode_frame(message))


def recv_message(sock: socket.socket) -> KMessage:
    """Receive one message and fail closed on malformed input."""
    if not _is_unix_stream(sock):
        raise ProtocolError("socket must be AF_UNIX SOCK_STREAM")
    try:
        header = recv_exact(sock, 4)
        frame_len = int.from_bytes(header, "big", signed=False)
        if frame_len == 0:
            raise ProtocolError("zero-length frame is forbidden")
        if frame_len > MAX_FRAME_SIZE:
            raise ProtocolError("declared frame length exceeds MAX_FRAME_SIZE")
        body = recv_exact(sock, frame_len)
        return decode_frame(body)
    except ProtocolError:
        _fail_closed_shutdown(sock)
        raise
    except OSError:
        _fail_closed_shutdown(sock)
        raise


def _fail_closed_shutdown(sock: socket.socket) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass


def socketpair() -> tuple[socket.socket, socket.socket]:
    """Local full-duplex AF_UNIX / SOCK_STREAM pair for tests only."""
    return socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)

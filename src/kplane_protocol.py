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

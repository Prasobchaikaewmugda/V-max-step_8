"""Property-based and fuzz coverage for the K-plane parser (no domain semantics)."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given, strategies as st

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


@given(msg=_messages_strategy())
def test_uds_roundtrip_property(msg: KMessage) -> None:
    try:
        left, right = socketpair()
    except OSError:
        pytest.skip("AF_UNIX socketpair not available")
    try:
        send_message(left, msg)
        assert recv_message(right) == msg
    finally:
        left.close()
        try:
            right.close()
        except OSError:
            pass


@given(blob=st.binary(min_size=1, max_size=256))
def test_uds_recv_bounded_blob_never_uncaught(blob: bytes) -> None:
    try:
        left, right = socketpair()
    except OSError:
        pytest.skip("AF_UNIX socketpair not available")
    try:
        left.sendall(blob)
        try:
            recv_message(right)
        except ProtocolError:
            pass
        except OSError:
            pass
        except Exception as exc:
            pytest.fail(f"recv_message must not raise except ProtocolError/OSError, got {exc!r}")
    finally:
        left.close()
        try:
            right.close()
        except OSError:
            pass

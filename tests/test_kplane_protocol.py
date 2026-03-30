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

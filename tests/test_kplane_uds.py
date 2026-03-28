from __future__ import annotations

import socket
import unittest

from kplane_protocol import KMessage, MAX_FRAME_SIZE, MessageKind, ProtocolError, encode_frame
from kplane_uds import recv_message, send_message, socketpair


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


@unittest.skipUnless(
    _af_unix_socketpair_available(),
    "AF_UNIX SOCK_STREAM socketpair not available",
)
class KPlaneUDSAFUnixTests(unittest.TestCase):
    """AF_UNIX / SOCK_STREAM transport: fail-closed on garbage, EOF, and oversize."""

    def test_socketpair_is_local_stream(self) -> None:
        left, right = socketpair()
        try:
            self.assertEqual(left.family, socket.AF_UNIX)
            self.assertEqual(left.type & socket.SOCK_STREAM, socket.SOCK_STREAM)
            self.assertEqual(right.family, socket.AF_UNIX)
            self.assertEqual(right.type & socket.SOCK_STREAM, socket.SOCK_STREAM)
        finally:
            left.close()
            right.close()

    def test_send_receive_roundtrip(self) -> None:
        left, right = socketpair()
        try:
            send_message(left, KMessage(MessageKind.HEARTBEAT, b"hb"))
            received = recv_message(right)
            self.assertEqual(received, KMessage(MessageKind.HEARTBEAT, b"hb"))
        finally:
            left.close()
            try:
                right.close()
            except OSError:
                pass

    def test_garbage_rejected_fail_closed(self) -> None:
        left, right = socketpair()
        try:
            left.sendall((3).to_bytes(4, "big") + bytes([255, 0, 0]))
            with self.assertRaises(ProtocolError):
                recv_message(right)
        finally:
            left.close()
            try:
                right.close()
            except OSError:
                pass

    def test_recv_fail_closed_shuts_receiver_after_garbage(self) -> None:
        """Second recv on the same socket must not succeed after malformed frame handling."""
        left, right = socketpair()
        try:
            left.sendall((3).to_bytes(4, "big") + bytes([255, 0, 0]))
            with self.assertRaises(ProtocolError):
                recv_message(right)
            with self.assertRaises((OSError, ProtocolError)):
                recv_message(right)
        finally:
            left.close()
            try:
                right.close()
            except OSError:
                pass

    def _close_pair(self, left: socket.socket, right: socket.socket) -> None:
        left.close()
        try:
            right.close()
        except OSError:
            pass

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

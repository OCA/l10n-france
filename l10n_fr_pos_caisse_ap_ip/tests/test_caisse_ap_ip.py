# Copyright 2026 Moka Tourisme (https://www.mokatourisme.fr/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import socket
import socketserver
import threading
import time

from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

from ..models.pos_payment_method import (
    _is_answer_complete,
    _talk_to_terminal,
)


def build_message(pairs):
    """Encode a Caisse-AP message: TAG(2) + LENGTH(3) + VALUE, per record."""
    return "".join("%s%s%s" % (t, str(len(v)).zfill(3), v) for t, v in pairs)


def parse_message(msg):
    out, idx = {}, 0
    while idx < len(msg):
        tag = msg[idx : idx + 2]
        size = int(msg[idx + 2 : idx + 5])
        out[tag] = msg[idx + 5 : idx + 5 + size]
        idx += 5 + size
    return out


class FakeTerminal:
    """A Caisse-AP payment terminal, on a real TCP socket.

    mode: "ok" | "refuse" | "split" | "silent"
    """

    def __init__(self, mode="ok", delay=0, fragments=1):
        self.mode = mode
        self.delay = delay
        self.fragments = fragments
        handler = self._make_handler()

        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        self.server = Server(("127.0.0.1", 0), handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def _make_handler(self):
        terminal = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                req = parse_message(self.request.recv(4096).decode("ascii"))
                if terminal.mode == "silent":
                    time.sleep(60)
                    return
                time.sleep(terminal.delay)
                answer = build_message(
                    [
                        ("CZ", req.get("CZ", "0300")),
                        ("CA", req.get("CA", "01")),
                        ("CB", req.get("CB", "0").zfill(12)),
                        ("CD", req.get("CD", "0")),
                        ("CE", req.get("CE", "978")),
                        ("AE", "01" if terminal.mode == "refuse" else "10"),
                        ("AF", "04" if terminal.mode == "refuse" else "01"),
                        ("CC", req.get("CC", "001")),
                        ("CI", "1"),
                        ("AA", "123456"),
                        ("AB", "987654321"),
                        ("AC", "00000001"),
                        ("AI", "20260814093000"),
                    ]
                ).encode("ascii")
                if terminal.mode == "split":
                    # A terminal is free to split its answer over several TCP
                    # segments: the module must reassemble them
                    cuts = [answer[:9], answer[9:25], answer[25:]]
                    for part in cuts:
                        self.request.sendall(part)
                        time.sleep(0.2)
                else:
                    self.request.sendall(answer)

        return Handler

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


@tagged("post_install", "-at_install")
class TestCaisseApIp(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        journal = cls.env["account.journal"].search(
            [("type", "in", ("bank", "cash"))], limit=1
        )
        cls.method = cls.env["pos.payment.method"].create(
            {
                "name": "Caisse-AP test terminal",
                "journal_id": journal.id,
                "use_payment_terminal": "fr-caisse_ap_ip",
                "fr_caisse_ap_ip_address": "127.0.0.1",
                "fr_caisse_ap_ip_port": 8888,
            }
        )
        cls.msg_dict = {
            "CJ": "012345678901",
            "CA": "01",
            "CE": "978",
            "CD": "0",
            "CB": "1000",
        }

    def _request_bytes(self):
        return self.method._fr_caisse_ap_ip_prepare_msg(dict(self.msg_dict)).encode(
            "ascii"
        )

    def _dialog(self, terminal, timeout=10):
        self.method.fr_caisse_ap_ip_port = terminal.port
        return _talk_to_terminal(
            self._request_bytes(), "127.0.0.1", terminal.port, timeout, "test-payment"
        )

    # --- framing ---------------------------------------------------------

    def test_answer_completeness(self):
        """A record stream is complete only when it lands on its own end."""
        self.assertTrue(_is_answer_complete("CZ0040300"))
        self.assertFalse(_is_answer_complete("CZ004030"))  # value truncated
        self.assertFalse(_is_answer_complete("CZ00"))  # header truncated
        self.assertTrue(_is_answer_complete(""))

    # --- dialog with the terminal ---------------------------------------

    def test_nominal_payment(self):
        terminal = FakeTerminal(mode="ok")
        self.addCleanup(terminal.stop)
        answer = self._dialog(terminal)
        res = self.method._fr_caisse_ap_ip_build_result(
            answer, self.msg_dict, False, "127.0.0.1", terminal.port
        )
        self.assertEqual(res["payment_status"], "success")
        self.assertIn("AA-123456", res["transaction_id"])

    def test_fragmented_answer(self):
        """Regression: a single recv() truncated the answer of the terminal.

        The payment was accepted by the terminal, yet the cashier got
        "the action status is invalid (AE=None)".
        """
        terminal = FakeTerminal(mode="split")
        self.addCleanup(terminal.stop)
        answer = self._dialog(terminal)
        res = self.method._fr_caisse_ap_ip_build_result(
            answer, self.msg_dict, False, "127.0.0.1", terminal.port
        )
        self.assertEqual(res["payment_status"], "success")
        # The trailing records must survive too, not just the status
        self.assertIn("AI-20260814093000", res["transaction_id"])

    def test_refused_payment(self):
        terminal = FakeTerminal(mode="refuse")
        self.addCleanup(terminal.stop)
        answer = self._dialog(terminal)
        res = self.method._fr_caisse_ap_ip_build_result(
            answer, self.msg_dict, False, "127.0.0.1", terminal.port
        )
        self.assertEqual(res["payment_status"], "failure")

    def test_silent_terminal(self):
        """A terminal that never answers must time out, not hang forever."""
        terminal = FakeTerminal(mode="silent")
        self.addCleanup(terminal.stop)
        start = time.monotonic()
        with self.assertRaises(socket.timeout):
            self._dialog(terminal, timeout=2)
        self.assertLess(time.monotonic() - start, 10)

    def test_unreachable_terminal(self):
        # Nothing listens on this port
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            free_port = probe.getsockname()[1]
        with self.assertRaises(OSError):
            _talk_to_terminal(self._request_bytes(), "127.0.0.1", free_port, 5, "x")

    # --- what the POS calls ---------------------------------------------

    @mute_logger("odoo.addons.l10n_fr_pos_caisse_ap_ip.models.pos_payment_method")
    def test_send_payment_returns_immediately(self):
        """The RPC must not wait for the terminal: that is the whole point."""
        terminal = FakeTerminal(mode="ok", delay=5)
        self.addCleanup(terminal.stop)
        self.method.fr_caisse_ap_ip_port = terminal.port
        start = time.monotonic()
        res = self.env["pos.payment.method"].fr_caisse_ap_ip_send_payment(
            {
                "amount": 10.0,
                "currency_id": self.env.company.currency_id.id,
                "payment_method_id": self.method.id,
                "pos_config_id": self.env["pos.config"].search([], limit=1).id,
                "payment_id": "test-immediate",
                "timeout": 20000,
            }
        )
        self.assertEqual(res["payment_status"], "waiting")
        self.assertLess(time.monotonic() - start, 1)

    def test_null_amount_is_rejected_synchronously(self):
        res = self.env["pos.payment.method"].fr_caisse_ap_ip_send_payment(
            {
                "amount": 0.0,
                "currency_id": self.env.company.currency_id.id,
                "payment_method_id": self.method.id,
                "pos_config_id": False,
                "payment_id": "test-null",
                "timeout": 20000,
            }
        )
        self.assertEqual(res["payment_status"], "issue")

    def test_answer_buffer_roundtrip(self):
        """Answers are keyed by payment and collected exactly once."""
        self.method._fr_caisse_ap_ip_store_answer(
            "pay-1", {"payment_status": "success", "payment_id": "pay-1"}
        )
        self.method._fr_caisse_ap_ip_store_answer(
            "pay-2", {"payment_status": "failure", "payment_id": "pay-2"}
        )
        model = self.env["pos.payment.method"]
        # One payment must never collect the answer of another
        self.assertEqual(
            model.fr_caisse_ap_ip_get_payment_status(self.method.id, "pay-2")[
                "payment_status"
            ],
            "failure",
        )
        self.assertEqual(
            model.fr_caisse_ap_ip_get_payment_status(self.method.id, "pay-1")[
                "payment_status"
            ],
            "success",
        )
        # Collected once: a second call finds nothing left
        self.assertEqual(
            model.fr_caisse_ap_ip_get_payment_status(self.method.id, "pay-1")[
                "payment_status"
            ],
            "waiting",
        )

    def test_unknown_payment_is_still_waiting(self):
        res = self.env["pos.payment.method"].fr_caisse_ap_ip_get_payment_status(
            self.method.id, "never-sent"
        )
        self.assertEqual(res["payment_status"], "waiting")

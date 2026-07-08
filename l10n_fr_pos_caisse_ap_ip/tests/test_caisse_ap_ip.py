# Copyright 2026 Akretion France (http://www.akretion.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import socket
import threading
import time

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


class FakeTerminal(threading.Thread):
    """A fake Caisse-AP payment terminal listening on localhost.

    It accepts one TCP connection, reads the request, builds the answer
    with the provided callback and sends it back.
    """

    def __init__(self, answer_builder, chunks=None, close_after_send=True):
        super().__init__(daemon=True)
        self.answer_builder = answer_builder
        self.chunks = chunks
        self.close_after_send = close_after_send
        self.request = None
        self.srv = socket.socket()
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(1)
        self.port = self.srv.getsockname()[1]

    @staticmethod
    def parse(data_str):
        data_dict = {}
        i = 0
        while i < len(data_str):
            tag = data_str[i : i + 2]
            size = int(data_str[i + 2 : i + 5])
            data_dict[tag] = data_str[i + 5 : i + 5 + size]
            i += 5 + size
        return data_dict

    @staticmethod
    def serialize(msg_dict):
        return "".join(
            f"{tag}{len(value):03d}{value}" for tag, value in msg_dict.items()
        )

    def run(self):
        conn, _addr = self.srv.accept()
        conn.settimeout(10)
        self.request = conn.recv(4096).decode("ascii")
        answer = self.answer_builder(self.parse(self.request))
        if isinstance(answer, dict):
            answer = self.serialize(answer)
        if self.chunks:
            for part in self.chunks(answer):
                conn.sendall(part.encode("ascii"))
                time.sleep(0.05)
        else:
            conn.sendall(answer.encode("ascii"))
        if self.close_after_send:
            conn.close()
        else:
            time.sleep(2)
            conn.close()
        self.srv.close()


@tagged("post_install", "-at_install")
class TestCaisseApIp(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.method = cls.env["pos.payment.method"].create(
            {
                "name": "Test Caisse-AP terminal",
                "use_payment_terminal": "fr-caisse_ap_ip",
                "fr_caisse_ap_ip_address": "127.0.0.1",
                "fr_caisse_ap_ip_port": 8888,
            }
        )
        cls.eur = cls.env.ref("base.EUR")
        cls.xpf = cls.env.ref("base.XPF")

    def _payment_data(self, amount, currency=None, timeout=10000):
        return {
            "amount": amount,
            "currency_id": (currency or self.eur).id,
            "payment_method_id": self.method.id,
            "payment_id": "test-uuid",
            "timeout": timeout,
        }

    def _send(self, amount, answer_builder, currency=None, chunks=None, **kw):
        terminal = FakeTerminal(answer_builder, chunks=chunks, **kw)
        terminal.start()
        self.method.fr_caisse_ap_ip_port = terminal.port
        res = self.env["pos.payment.method"].fr_caisse_ap_ip_send_payment(
            self._payment_data(amount, currency=currency)
        )
        terminal.join(timeout=10)
        return res, terminal

    @staticmethod
    def _success_answer(req):
        return {
            "CZ": req["CZ"],
            "AE": "10",
            "CA": req["CA"],
            "CB": "000" + req["CB"],  # a real terminal zero-pads the amount
            "CD": req["CD"],
            "CE": req["CE"],
            "CC": "001",
            "CI": "1",
            "AA": "1234",
            "AB": "123456",
            "AC": "20260708",
        }

    # ------------------------------------------------------------------
    # Configuration constraint
    # ------------------------------------------------------------------
    def test_constraint_missing_ip(self):
        with self.assertRaises(ValidationError):
            self.method.fr_caisse_ap_ip_address = False

    def test_constraint_invalid_port(self):
        with self.assertRaises(ValidationError):
            self.method.fr_caisse_ap_ip_port = 70000

    # ------------------------------------------------------------------
    # Message preparation and serialization
    # ------------------------------------------------------------------
    def test_prepare_msg(self):
        msg = self.method._fr_caisse_ap_ip_prepare_msg(
            {"CJ": "012345678901", "CA": "01", "CE": "978", "CD": "0", "CB": "05"}
        )
        self.assertTrue(msg.startswith("CZ0040300"))
        self.assertIn("CB00205", msg)
        self.assertIn("CE003978", msg)

    def test_prepare_msg_rejects_bad_input(self):
        for bad in (False, {"payment_status": "issue"}, {"CA": ""}, {"CA": 5}):
            with self.assertRaises(ValueError):
                self.method._fr_caisse_ap_ip_prepare_msg(bad)

    def test_prepare_message_eur(self):
        data = self._payment_data(12.34)
        msg_dict = self.method._fr_caisse_ap_ip_prepare_message(data)
        self.assertEqual(msg_dict["CB"], "1234")
        self.assertEqual(msg_dict["CD"], "0")
        self.assertEqual(msg_dict["CE"], "978")
        self.assertNotIn("CC", msg_dict)

    def test_prepare_message_small_amount_is_padded(self):
        # The protocol requires a minimum size of 2 chars for the CB tag
        data = self._payment_data(0.05)
        msg_dict = self.method._fr_caisse_ap_ip_prepare_message(data)
        self.assertEqual(msg_dict["CB"], "05")

    def test_prepare_message_reimbursement(self):
        data = self._payment_data(-10.0)
        msg_dict = self.method._fr_caisse_ap_ip_prepare_message(data)
        self.assertEqual(msg_dict["CD"], "1")
        self.assertEqual(msg_dict["CB"], "1000")

    def test_prepare_message_no_decimal_currency(self):
        data = self._payment_data(1000, currency=self.xpf)
        msg_dict = self.method._fr_caisse_ap_ip_prepare_message(data)
        self.assertEqual(msg_dict["CB"], "1000")
        self.assertEqual(msg_dict["CE"], "953")

    def test_prepare_message_check_mode(self):
        self.method.fr_caisse_ap_ip_mode = "check"
        data = self._payment_data(10.0)
        msg_dict = self.method._fr_caisse_ap_ip_prepare_message(data)
        self.assertEqual(msg_dict.get("CC"), "00C")

    def test_null_amount_returns_issue(self):
        res = self.env["pos.payment.method"].fr_caisse_ap_ip_send_payment(
            self._payment_data(0.0)
        )
        self.assertEqual(res["payment_status"], "issue")
        self.assertIn("null amount", res["error_message"])

    def test_over_maximum_amount_returns_issue(self):
        res = self.env["pos.payment.method"].fr_caisse_ap_ip_send_payment(
            self._payment_data(10**12)
        )
        self.assertEqual(res["payment_status"], "issue")
        self.assertIn("maximum", res["error_message"])

    # ------------------------------------------------------------------
    # Answer parsing
    # ------------------------------------------------------------------
    def test_answer_complete(self):
        complete = self.method._fr_caisse_ap_ip_answer_complete
        self.assertTrue(complete("CZ0040300AE00210"))
        self.assertFalse(complete("CZ0040300AE002"))
        self.assertFalse(complete("CZ0040300AE0"))
        self.assertFalse(complete(""))

    def test_parse_answer(self):
        parsed = self.method._fr_caisse_ap_ip_parse_answer(
            "CZ0040300AE00210CB00205CD0010CE003978CA00201"
        )
        self.assertEqual(
            parsed,
            {
                "CZ": "0300",
                "AE": "10",
                "CB": "05",
                "CD": "0",
                "CE": "978",
                "CA": "01",
            },
        )

    def test_parse_answer_malformed(self):
        for bad in ("CZ00X0300", "AE00", "AE00510"):
            with self.assertRaises(ValueError):
                self.method._fr_caisse_ap_ip_parse_answer(bad)

    def test_check_answer(self):
        msg_dict = {"CA": "01", "CB": "05", "CD": "0", "CE": "978"}
        answer = {"CA": "01", "CB": "0000005", "CD": "0", "CE": "978", "AE": "10"}
        self.assertIs(self.method._fr_caisse_ap_ip_check_answer(answer, msg_dict), True)
        # missing required tag: the error message must name the tag
        res = self.method._fr_caisse_ap_ip_check_answer(
            {"CA": "01", "CD": "0", "CE": "978"}, msg_dict
        )
        self.assertEqual(res["payment_status"], "issue")
        self.assertIn("CB", res["error_message"])
        # amount mismatch must be detected
        res = self.method._fr_caisse_ap_ip_check_answer(
            dict(answer, CB="0000006"), msg_dict
        )
        self.assertEqual(res["payment_status"], "issue")

    # ------------------------------------------------------------------
    # Full exchange with a fake terminal
    # ------------------------------------------------------------------
    def test_payment_success(self):
        res, terminal = self._send(10.0, self._success_answer)
        self.assertEqual(res["payment_status"], "success")
        self.assertIn("CB contact", res["card_type"])
        self.assertIn("AA-1234", res["transaction_id"])
        self.assertIn("CD-0", res["transaction_id"])
        self.assertEqual(res["ticket"], "Card type: CB contact")
        # the request sent on the wire was correct
        req = FakeTerminal.parse(terminal.request)
        self.assertEqual(req["CB"], "1000")
        self.assertEqual(req["CZ"], "0300")

    def test_payment_success_split_answer(self):
        # The answer arrives in several TCP chunks, split in the middle
        # of a field: the recv loop must reassemble it
        res, _terminal = self._send(
            10.0,
            self._success_answer,
            chunks=lambda a: [a[:7], a[7:20], a[20:]],
        )
        self.assertEqual(res["payment_status"], "success")

    def test_payment_success_connection_kept_open(self):
        # The terminal does not close the connection after answering:
        # the drain logic must still terminate the read
        res, _terminal = self._send(10.0, self._success_answer, close_after_send=False)
        self.assertEqual(res["payment_status"], "success")

    def test_payment_failure(self):
        def failure_answer(req):
            return {"CZ": req["CZ"], "AE": "01", "AF": "06"}

        res, _terminal = self._send(10.0, failure_answer)
        self.assertEqual(res["payment_status"], "failure")
        self.assertIn("Abandon", res["error_message"])

    def test_payment_garbage_answer(self):
        res, _terminal = self._send(10.0, lambda req: "GARBAGE?!")
        self.assertEqual(res["payment_status"], "issue")

    def test_payment_wrong_echo(self):
        def wrong_echo(req):
            answer = self._success_answer(req)
            answer["CE"] = "840"  # currency not matching the request
            return answer

        res, _terminal = self._send(10.0, wrong_echo)
        self.assertEqual(res["payment_status"], "issue")

    def test_payment_connection_refused(self):
        # Reserve a port and close it so that nothing listens on it
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        srv.close()
        self.method.fr_caisse_ap_ip_port = port
        res = self.env["pos.payment.method"].fr_caisse_ap_ip_send_payment(
            self._payment_data(10.0)
        )
        self.assertEqual(res["payment_status"], "issue")
        self.assertIn("127.0.0.1", res["error_message"])

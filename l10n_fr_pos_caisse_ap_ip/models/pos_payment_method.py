# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import socket
import time

from odoo import api, fields, models
from odoo.exceptions import ValidationError

logger = logging.getLogger(__name__)

try:
    import pycountry
except ImportError:
    logger.debug("Cannot import pycountry")

BUFFER_SIZE = 1024
# The Caisse-AP protocol has no length header nor end-of-message marker.
# When the buffer parses as a whole number of fields, we drain the socket
# during DRAIN_TIMEOUT to catch an answer split exactly on a field boundary.
DRAIN_TIMEOUT = 0.3
# Safety cap: a real Caisse-AP answer is well under a few KB
MAX_ANSWER_SIZE = 65536


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _get_payment_terminal_selection(self):
        res = super()._get_payment_terminal_selection()
        res.append(("fr-caisse_ap_ip", self.env._("Caisse AP over IP (France only)")))
        return res

    fr_caisse_ap_ip_mode = fields.Selection(
        [("card", "Card"), ("check", "Check")], string="Payment Mode", default="card"
    )
    fr_caisse_ap_ip_address = fields.Char(
        string="Caisse-AP Payment Terminal IP Address",
        help="IP address or DNS name of the payment terminal that support "
        "Caisse-AP protocol over IP",
    )
    fr_caisse_ap_ip_port = fields.Integer(
        string="Caisse-AP Payment Terminal Port",
        help="TCP port of the payment terminal that support Caisse-AP protocol over IP",
        default=8888,
    )

    @api.constrains(
        "use_payment_terminal", "fr_caisse_ap_ip_address", "fr_caisse_ap_ip_port"
    )
    def _check_fr_caisse_ap_ip(self):
        for method in self:
            if method.use_payment_terminal == "fr-caisse_ap_ip":
                if not method.fr_caisse_ap_ip_address:
                    raise ValidationError(
                        self.env._(
                            "Caisse-AP payment terminal IP address is not set on "
                            "payment method '%s'.",
                            method.display_name,
                        )
                    )
                if not method.fr_caisse_ap_ip_port:
                    raise ValidationError(
                        self.env._(
                            "Caisse-AP payment terminal port is not set on "
                            "payment method '%s'.",
                            method.display_name,
                        )
                    )

                if (
                    method.fr_caisse_ap_ip_port < 1
                    or method.fr_caisse_ap_ip_port > 65535
                ):
                    raise ValidationError(
                        self.env._(
                            "Port %s for the payment terminal is not a valid TCP port.",
                            method.fr_caisse_ap_ip_port,
                        )
                    )

    def _fr_caisse_ap_ip_prepare_msg(self, msg_dict):
        # Explicit checks instead of assert, so that they are not
        # skipped when Python runs in optimized mode (-O)
        if not isinstance(msg_dict, dict):
            raise ValueError("msg_dict must be a dict")
        for tag, value in msg_dict.items():
            if not isinstance(tag, str) or len(tag) != 2:
                raise ValueError(f"Tag {tag!r} must be a string of 2 chars")
            if not isinstance(value, str) or not 1 <= len(value) <= 999:
                raise ValueError(
                    f"Value {value!r} of tag '{tag}' must be a string of 1 to 999 chars"
                )
        msg_list = []
        # CZ tag: protocol version
        # Always start with tag CZ
        # the order of the other tags is unrelevant
        if "CZ" in msg_dict:
            version = msg_dict.pop("CZ")
        else:
            version = "0300"  # 0301 ??
        if len(version) != 4:
            raise ValueError(f"Version {version!r} must be a string of 4 chars")
        msg_list.append(("CZ", version))
        msg_list += list(msg_dict.items())
        msg_str = "".join(
            [
                "".join([tag, str(len(value)).zfill(3), value])
                for (tag, value) in msg_list
            ]
        )
        return msg_str

    def _fr_caisse_ap_ip_prepare_message(self, data):
        self.ensure_one()
        amount = data.get("amount")
        currency_id = data["currency_id"]
        currency = self.env["res.currency"].browse(currency_id)
        data["currency"] = currency
        cur_speed_map = {  # small speed-up, and works even if pycountry not installed
            "EUR": "978",
            "XPF": "953",
            "USD": "840",  # Only because it is the default currency
        }
        if currency.name in cur_speed_map:
            cur_num = cur_speed_map[currency.name]
        else:
            try:
                cur = pycountry.currencies.get(alpha_3=currency.name)
                cur_num = cur.numeric  # it returns a string
            except Exception as e:
                logger.error(
                    "pycountry doesn't support currency '%s'. Error: %s",
                    currency.name,
                    e,
                )
                return False
        # CJ identifiant protocole concert : no interest, but required
        # CA POS number
        msg_dict = {
            "CJ": "012345678901",
            "CA": "01",
            "CE": cur_num,
        }
        amount_compare = currency.compare_amounts(amount, 0)
        # CD Action type: 0=debit (regular payment) 1=credit (reimbursement)
        if not amount_compare:
            logger.error("Amount for payment terminal is 0")
            error_msg = self.env._(
                "You are tying to send a null amount to the payment terminal!"
            )
            res = {
                "payment_status": "issue",
                "error_message": error_msg,
            }
            return res
        elif amount_compare < 0:
            msg_dict["CD"] = "1"  # credit i.e. reimbursement
            amount_positive = amount * -1
        else:
            msg_dict["CD"] = "0"  # debit i.e. regular payment
            amount_positive = amount
        if currency.decimal_places:
            amount_cent = amount_positive * (10**currency.decimal_places)
        else:
            amount_cent = amount_positive
        amount_str = str(int(round(amount_cent)))
        data["amount_str"] = amount_str
        if len(amount_str) > 12:
            logger.error("Amount with cents %s is over the maximum.", amount_str)
            error_msg = self.env._(
                "You are tying to send amount %s cents to the payment terminal, "
                "but it is over the maximum!",
                amount_str,
            )
            res = {
                "payment_status": "issue",
                "error_message": error_msg,
            }
            return res
        # The protocol requires a minimum size of 2 chars for the CB tag
        msg_dict["CB"] = amount_str.zfill(2)
        if self.fr_caisse_ap_ip_mode == "check":
            msg_dict["CC"] = "00C"
        return msg_dict

    @api.model
    def fr_caisse_ap_ip_send_payment(self, data):
        """Method called by the JS code of this module"""
        logger.debug("fr_caisse_ap_ip_send_payment data=%s", data)
        payment_method_id = data["payment_method_id"]
        payment_method = self.browse(payment_method_id)
        msg_dict = payment_method._fr_caisse_ap_ip_prepare_message(data)
        if not msg_dict:
            return {
                "payment_status": "issue",
                "error_message": self.env._(
                    "Odoo could not prepare the message for the payment terminal. "
                    "Check the Odoo server logs for more details."
                ),
            }
        if msg_dict.get("payment_status"):
            # _fr_caisse_ap_ip_prepare_message() returned an error dict
            return msg_dict
        msg_str = self._fr_caisse_ap_ip_prepare_msg(msg_dict)
        msg_bytes = msg_str.encode("ascii")
        timeout_ms = data["timeout"]
        # For the timeout of the TCP socket to the payment terminal, we remove
        # 3 seconds from the timeout of the POS
        timeout_sec = timeout_ms / 1000 - 3
        ip_addr = payment_method.fr_caisse_ap_ip_address
        port = payment_method.fr_caisse_ap_ip_port
        logger.info(
            "Sending %s %s %s %s cents to payment terminal %s:%s",
            msg_dict["CD"] == "1" and "reimbursement" or "payment",
            msg_dict.get("CC") == "00C" and "check" or "card",
            data["currency"].name,
            data["amount_str"],
            ip_addr,
            port,
        )
        logger.debug("Data about to be sent to payment terminal: %s", msg_str)
        answer = ""
        try:
            with socket.create_connection((ip_addr, port), timeout=timeout_sec) as sock:
                sock.sendall(msg_bytes)
                # The answer may be split across several TCP packets and may
                # exceed BUFFER_SIZE: read until the terminal closes the
                # connection or the message is complete. As the protocol has
                # no length header, 'complete' can be a false positive when
                # the split falls on a field boundary: when the buffer looks
                # complete, keep reading with a short timeout (DRAIN_TIMEOUT)
                # and only stop when no more data arrives.
                deadline = time.monotonic() + timeout_sec
                while True:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(
                            "Global timeout reading the answer from the "
                            "payment terminal"
                        )
                    try:
                        chunk = sock.recv(BUFFER_SIZE)
                    except TimeoutError:
                        if answer and self._fr_caisse_ap_ip_answer_complete(answer):
                            # Drain timeout expired without extra data:
                            # the answer is really complete
                            break
                        raise
                    if not chunk:
                        # The terminal closed the connection
                        break
                    answer += chunk.decode("ascii")
                    if len(answer) > MAX_ANSWER_SIZE:
                        raise ValueError(
                            "Answer from the payment terminal exceeds "
                            f"{MAX_ANSWER_SIZE} bytes"
                        )
                    if self._fr_caisse_ap_ip_answer_complete(answer):
                        sock.settimeout(DRAIN_TIMEOUT)
                    else:
                        sock.settimeout(max(deadline - time.monotonic(), DRAIN_TIMEOUT))
                logger.debug("Answer received from payment terminal: %s", answer)
        except Exception as e:
            logger.warning("Exception raised in socket to payment terminal: %s", e)
            error_msg = self.env._(
                "Failure in the connection to the payment terminal"
                " on %(ip_addr)s port %(port)s: %(error)s.",
                ip_addr=ip_addr,
                port=port,
                error=e,
            )
            res = {
                "payment_status": "issue",
                "error_message": error_msg,
            }
            return res
        if answer:
            try:
                res = self._fr_caisse_ap_ip_answer(answer, msg_dict)
            except Exception as e:
                logger.error(
                    "Cannot parse the answer '%s' from the payment terminal: %s",
                    answer,
                    e,
                )
                res = {
                    "payment_status": "issue",
                    "error_message": self.env._(
                        "Cannot understand the answer from the payment terminal: %s",
                        answer,
                    ),
                }
        else:
            res = {
                "payment_status": "issue",
                "error_message": self.env._(
                    "Empty answer from payment terminal. This should never happen."
                ),
            }
        logger.debug("JSON sent back to POS: %s", res)
        return res

    def _fr_caisse_ap_ip_answer(self, answer, msg_dict):
        answer_dict = self._fr_caisse_ap_ip_parse_answer(answer)
        if answer_dict.get("AE") == "10":
            check_res = self._fr_caisse_ap_ip_check_answer(answer_dict, msg_dict)
            if isinstance(check_res, dict):
                return check_res
            res = self._fr_caisse_ap_ip_prepare_success(answer_dict)
        elif answer_dict.get("AE") == "01":
            res = self._fr_caisse_ap_ip_prepare_failure(answer_dict)
        else:
            error_msg = self.env._(
                "Error in the communication with the payment terminal: "
                "the action statuts is invalid (AE=%s). "
                "This should never happen!",
                answer_dict.get("AE"),
            )
            res = {
                "payment_status": "issue",
                "error_message": error_msg,
            }
        return res

    def _fr_caisse_ap_ip_check_answer(self, answer_dict, msg_dict):
        tag_dict = {
            "CA": {"fixed_size": True, "required": True, "label": "caisse"},
            "CB": {"fixed_size": False, "required": True, "label": "amount"},
            "CD": {"fixed_size": True, "required": True, "label": "action pay/reimb"},
            "CE": {"fixed_size": True, "required": True, "label": "currency"},
        }
        fail_res = {
            "payment_status": "issue",
        }
        for tag, props in tag_dict.items():
            if props["required"] and not answer_dict.get(tag):
                fail_res["error_message"] = self.env._(
                    "Caisse AP IP protocol: tag %s is required but it is "
                    "not present in the answer from the terminal. "
                    "This should never happen!",
                    tag,
                )
                return fail_res
            if (
                props["fixed_size"]
                and answer_dict.get(tag)
                and answer_dict[tag] != msg_dict[tag]
            ):
                fail_res["error_message"] = self.env._(
                    "Caisse AP IP protocol: Tag %(label)s (%(tag)s) has value "
                    "%(request_val)s in the query and %(answer_val)s in the "
                    "answer, but these values should be identical. "
                    "This should never happen!",
                    label=props["label"],
                    tag=tag,
                    request_val=msg_dict[tag],
                    answer_val=answer_dict[tag],
                )
                return fail_res
            elif not props["fixed_size"] and answer_dict.get(tag):
                # Strip the leading zeros on both sides: the terminal may
                # zero-pad the value differently from the request
                strip_answer = answer_dict[tag].lstrip("0")
                if msg_dict[tag].lstrip("0") != strip_answer:
                    fail_res["error_message"] = self.env._(
                        "Caisse AP IP protocol: Tag %(label)s (%(tag)s) has value "
                        "%(request_val)s in the request and %(answer_val)s in the "
                        "answer, but these values should be identical. "
                        "This should never happen!",
                        label=props["label"],
                        tag=tag,
                        request_val=msg_dict[tag],
                        answer_val=strip_answer,
                    )
                    return fail_res
        return True

    def _fr_caisse_ap_ip_prepare_success(self, answer_dict):
        card_type_list = []
        cc_labels = {
            "1": "CB contact",
            "B": "CB sans contact",
            "C": "Chèque",
            "2": "Amex contact",
            "D": "Amex sans contact",
            "3": "CB Enseigne",
            "5": "Cofinoga",
            "6": "Diners",
            "7": "CB-Pass",
            "8": "Franfinance",
            "9": "JCB",
            "A": "Banque Accord",
            "I": "CPEI",
            "E": "CMCIC-Pay TPE",
            "U": "CUP",
            "0": "Autres",
        }
        ci_labels = {
            "0": "indifférent",
            "1": "contact",
            "2": "sans contact",
            "3": "piste",
            "4": "saisie manuelle",
        }
        ticket = False
        if answer_dict.get("CC") and len(answer_dict["CC"]) == 3:
            cc_tag = answer_dict["CC"].lstrip("0")
            cc_label = cc_labels.get(cc_tag, self.env._("unknown"))
            card_type_list.append(
                self.env._(
                    "Application %(label)s (code %(code)s)", label=cc_label, code=cc_tag
                )
            )
            ticket = self.env._("Card type: %s", cc_label)
        if answer_dict.get("CI") and len(answer_dict["CI"]) == 1:
            card_type_list.append(
                self.env._(
                    "Read mode: %(label)s (code %(code)s)",
                    label=ci_labels.get(answer_dict["CI"], self.env._("unknown")),
                    code=answer_dict["CI"],
                )
            )

        transaction_tags = ["AA", "AB", "AC", "AI", "CD"]
        transaction_id = "|".join(
            [
                "-".join([tag, answer_dict[tag]])
                for tag in transaction_tags
                if answer_dict.get(tag)
            ]
        )

        res = {
            "payment_status": "success",
            "transaction_id": transaction_id,
            "card_type": " - ".join(card_type_list),
            "ticket": ticket,
        }
        logger.info(
            "Received success answer from payment terminal (card_type: %s)",
            res["card_type"],
        )
        logger.debug("transaction_id=%s", res["transaction_id"])
        return res

    def _fr_caisse_ap_ip_prepare_failure(self, answer_dict):
        label = None
        error_msg = self.env._("The payment transaction has failed.")
        af_labels = {
            "00": "Inconnu",
            "01": "Transaction autorisé",
            "02": "Appel phonie",
            "03": "Forçage",
            "04": "Refusée",
            "05": "Interdite",
            "06": "Abandon",
            "07": "Non aboutie",
            "08": "Opération non effectuée Time-out saisie",
            "09": "Opération non effectuée erreur format message",
            "10": "Opération non effectuée erreur sélection",
            "11": "Opération non effectuée Abandon Opérateur",
            "12": "Opération non effectuée type d’action demandé inconnu",
            "13": "Devise non supportée",
        }
        if answer_dict.get("AF") and answer_dict["AF"] in af_labels:
            label = af_labels[answer_dict["AF"]]
            error_msg = self.env._("The payment transaction has failed: %s", label)
        res = {
            "payment_status": "failure",
            "error_message": error_msg,
        }
        logger.info("Failure answer from payment terminal (failure report: %s)", label)
        return res

    @api.model
    def _fr_caisse_ap_ip_answer_complete(self, data_str):
        # A Caisse-AP message is a sequence of TAG(2 chars) SIZE(3 digits)
        # VALUE(SIZE chars) fields. Return True when data_str contains a
        # complete sequence of fields.
        i = 0
        while i < len(data_str):
            size_str = data_str[i + 2 : i + 5]
            if len(size_str) < 3 or not size_str.isdigit():
                return False
            i += 5 + int(size_str)
        return i > 0 and i == len(data_str)

    def _fr_caisse_ap_ip_parse_answer(self, data_str):
        logger.debug("Received raw data: %s", data_str)
        data_dict = {}
        i = 0
        while i < len(data_str):
            tag = data_str[i : i + 2]
            i += 2
            size_str = data_str[i : i + 3]
            if len(size_str) < 3 or not size_str.isdigit():
                raise ValueError(
                    f"Wrong size '{size_str}' for tag '{tag}': the answer from "
                    "the payment terminal is malformed or truncated."
                )
            size = int(size_str)
            i += 3
            value = data_str[i : i + size]
            if len(value) != size:
                raise ValueError(
                    f"Value of tag '{tag}' is truncated: expected {size} chars, "
                    f"got {len(value)}."
                )
            data_dict[tag] = value
            i += size
        logger.debug("Answer dict: %s", data_dict)
        return data_dict

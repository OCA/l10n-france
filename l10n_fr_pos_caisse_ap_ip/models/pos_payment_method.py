# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import socket
import threading
import time

import psycopg2

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.modules.registry import Registry

logger = logging.getLogger(__name__)

try:
    import pycountry
except ImportError:
    logger.debug("Cannot import pycountry")

BUFFER_SIZE = 1024
# Connecting to the terminal must fail fast: an unplugged or powered-off
# terminal should not make the cashier wait for the full payment timeout.
CONNECT_TIMEOUT = 10
# Quiet period on a record boundary before considering the answer over
INTER_FRAGMENT_TIMEOUT = 1
# Answers kept in the buffer, waiting to be collected by the POS
MAX_BUFFERED_ANSWERS = 5
# Concurrent writes on the payment method row are retried, not lost
WRITE_ATTEMPTS = 5
RETRY_DELAY = 0.2

# Live sockets, keyed by payment_id, so that a cancellation from the POS can
# close the connection instead of letting the thread wait for its timeout.
_ACTIVE_SOCKETS = {}
_ACTIVE_SOCKETS_LOCK = threading.Lock()


def _is_answer_complete(answer):
    """Caisse-AP answers are a stream of TAG(2) + LENGTH(3) + VALUE records.

    The answer walks complete when the records land exactly on the end of the
    buffer -- which a mere prefix of records also does, hence the quiet period
    in _read_answer.
    """
    idx = 0
    while idx < len(answer):
        if len(answer) < idx + 5:
            return False
        try:
            size = int(answer[idx + 2 : idx + 5])
        except ValueError:
            # Not parsable: stop reading and let the parser report the problem
            return True
        idx += 5 + size
    return idx == len(answer)


def _read_answer(sock, read_timeout):
    """Read the whole answer, however the terminal splits it over TCP.

    The protocol carries no total length, so a prefix of complete records is
    indistinguishable from a complete answer -- reading until the records parse
    is not enough. Two rules settle it:
      - mid-record, keep waiting with the full payment timeout;
      - on a record boundary, wait a short quiet period for a next fragment,
        and stop when none comes (or when the terminal closes).
    """
    buf = b""
    sock.settimeout(read_timeout)
    while True:
        try:
            chunk = sock.recv(BUFFER_SIZE)
        except socket.timeout:
            if not buf:
                # The terminal never answered at all
                raise
            break
        if not chunk:
            # Terminal closed the connection: nothing more is coming
            break
        buf += chunk
        sock.settimeout(
            INTER_FRAGMENT_TIMEOUT
            if _is_answer_complete(buf.decode("ascii", "replace"))
            else read_timeout
        )
    return buf.decode("ascii")


def _talk_to_terminal(msg_bytes, ip_addr, port, read_timeout, payment_id):
    """Full dialog with the terminal. Runs outside any database cursor."""
    with socket.create_connection((ip_addr, port), timeout=CONNECT_TIMEOUT) as sock:
        # create_connection's timeout covers the connection only; it is then
        # inherited by recv(). _read_answer sets the read timeout explicitly,
        # otherwise the worst case is twice the intended timeout.
        with _ACTIVE_SOCKETS_LOCK:
            _ACTIVE_SOCKETS[payment_id] = sock
        try:
            sock.sendall(msg_bytes)
            return _read_answer(sock, read_timeout)
        finally:
            with _ACTIVE_SOCKETS_LOCK:
                _ACTIVE_SOCKETS.pop(payment_id, None)


def _terminal_thread(
    dbname,
    method_id,
    config_id,
    payment_id,
    msg_bytes,
    msg_dict,
    ip_addr,
    port,
    read_timeout,
):
    """Dialog with the terminal, off the HTTP worker.

    The worker that received the RPC has already answered the POS: nothing here
    may hold it. The socket wait happens with no cursor open, and a cursor is
    taken only to buffer the result and notify the POS over the bus.
    """
    threading.current_thread().dbname = dbname
    answer = False
    error = False
    try:
        answer = _talk_to_terminal(msg_bytes, ip_addr, port, read_timeout, payment_id)
    except Exception as e:
        logger.warning("Exception raised in socket to payment terminal: %s", e)
        error = e
    for attempt in range(WRITE_ATTEMPTS):
        try:
            with Registry(dbname).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                method = env["pos.payment.method"].browse(method_id)
                res = method._fr_caisse_ap_ip_build_result(
                    answer, msg_dict, error, ip_addr, port
                )
                res["payment_id"] = payment_id
                # Buffered first: the POS must be able to collect the answer
                # even if the bus notification never reaches it
                method._fr_caisse_ap_ip_store_answer(payment_id, res)
                env["pos.config"].browse(config_id)._notify(
                    "FR_CAISSE_AP_IP_RESPONSE", res
                )
            return
        except psycopg2.OperationalError as e:
            # Two terminals answering at the same instant write the same row:
            # PostgreSQL aborts one of them, and the answer must not be lost
            logger.info("Concurrent update while recording the answer: %s", e)
            time.sleep(RETRY_DELAY * (attempt + 1))
        except Exception:
            # Never let this thread die silently: the POS would wait forever
            logger.exception(
                "Could not record the answer of payment terminal %s:%s", ip_addr, port
            )
            return
    logger.error(
        "Gave up recording the answer of payment terminal %s:%s after %s attempts",
        ip_addr,
        port,
        WRITE_ATTEMPTS,
    )


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _get_payment_terminal_selection(self):
        res = super()._get_payment_terminal_selection()
        res.append(("fr-caisse_ap_ip", _("Caisse AP over IP (France only)")))
        return res

    fr_caisse_ap_ip_mode = fields.Selection(
        [("card", "Card"), ("check", "Check"), ("ancv", "ANCV")],
        string="Payment Mode",
        default="card",
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
    fr_caisse_ap_ip_fast_payment = fields.Boolean(
        string="Auto-send Amount to Payment Terminal",
        default=True,
        help="If you want to allow several payments by cards on the same order, "
        "you should disable this option. When this option is disabled, you can "
        "change the amount and there is a button to send the amount to the "
        "payment terminal. When the option is enabled, Odoo automatically "
        "sends the total residual amount to the payment terminal.",
    )

    # Buffers the answer of the terminal until the POS collects it
    fr_caisse_ap_ip_latest_response = fields.Char(
        copy=False, groups="base.group_erp_manager"
    )

    def _is_write_forbidden(self, fields):
        # The buffer is written while a session is open, by design
        return super()._is_write_forbidden(fields - {"fr_caisse_ap_ip_latest_response"})

    @api.model
    def _load_pos_data_fields(self, config_id):
        field_list = super()._load_pos_data_fields(config_id)
        field_list.append("fr_caisse_ap_ip_fast_payment")
        return field_list

    @api.constrains(
        "use_payment_terminal", "fr_caisse_ap_ip_address", "fr_caisse_ap_ip_port"
    )
    def _check_fr_caisse_ap_ip(self):
        for method in self:
            if method.use_payment_terminal == "fr-caisse_ap_ip":
                if not method.fr_caisse_ap_ip_address:
                    raise ValidationError(
                        _(
                            "Caisse-AP payment terminal IP address is not set on "
                            "payment method '%s'."
                        )
                        % method.display_name
                    )
                if not method.fr_caisse_ap_ip_port:
                    raise ValidationError(
                        _(
                            "Caisse-AP payment terminal port is not set on "
                            "payment method '%s'."
                        )
                        % method.display_name
                    )

                if (
                    method.fr_caisse_ap_ip_port < 1
                    or method.fr_caisse_ap_ip_port > 65535
                ):
                    raise ValidationError(
                        _("Port %s for the payment terminal is not a valid TCP port.")
                        % method.fr_caisse_ap_ip_port
                    )

    @api.model
    def _fr_caisse_ap_ip_cc_map(self):
        return {
            "check": "00C",
            "ancv": "00V",
        }

    def _fr_caisse_ap_ip_prepare_msg(self, msg_dict):
        assert isinstance(msg_dict, dict)
        for tag, value in msg_dict.items():
            assert isinstance(tag, str)
            assert len(tag) == 2
            assert isinstance(value, str)
            assert len(value) >= 1
            assert len(value) <= 999
        msg_list = []
        # CZ tag: protocol version
        # Always start with tag CZ
        # the order of the other tags is unrelevant
        if "CZ" in msg_dict:
            version = msg_dict.pop("CZ")
        else:
            version = "0300"  # 0301 ??
        assert len(version) == 4
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
            error_msg = _(
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
        msg_dict["CB"] = amount_str
        if len(amount_str) < 2:
            amount_str = amount_str.zfill(2)
        elif len(amount_str) > 12:
            logger.error("Amount with cents %s is over the maximum.", amount_str)
            error_msg = (
                _(
                    "You are tying to send amount %s cents to the payment terminal, "
                    "but it is over the maximum!"
                )
                % amount_str
            )
            res = {
                "payment_status": "issue",
                "error_message": error_msg,
            }
            return res
        cc_map = self._fr_caisse_ap_ip_cc_map()
        if self.fr_caisse_ap_ip_mode in cc_map:
            msg_dict["CC"] = cc_map[self.fr_caisse_ap_ip_mode]
        return msg_dict

    @api.model
    def fr_caisse_ap_ip_send_payment(self, data):
        """Method called by the JS code of this module.

        It only prepares the request and hands the dialog over to a thread:
        talking to the terminal here would pin an HTTP worker (and a database
        connection) for as long as the customer takes to insert a card and type
        a PIN, freezing the whole Odoo instance once every worker is busy.
        """
        logger.debug("fr_caisse_ap_ip_send_payment data=%s", data)
        payment_method_id = data["payment_method_id"]
        payment_method = self.browse(payment_method_id)
        msg_dict = payment_method._fr_caisse_ap_ip_prepare_message(data)
        if not isinstance(msg_dict, dict):
            return {
                "payment_status": "issue",
                "error_message": _(
                    "Could not prepare the request for the payment terminal."
                ),
            }
        if "payment_status" in msg_dict:
            # Synchronous rejection (null amount, amount too large, ...)
            return msg_dict
        payment_id = data["payment_id"]
        msg_str = self._fr_caisse_ap_ip_prepare_msg(dict(msg_dict))
        msg_bytes = msg_str.encode("ascii")
        timeout_ms = data["timeout"]
        # For the timeout of the TCP socket to the payment terminal, we remove
        # 3 seconds from the timeout of the POS
        timeout_sec = timeout_ms / 1000 - 3
        ip_addr = payment_method.fr_caisse_ap_ip_address
        port = payment_method.fr_caisse_ap_ip_port
        cc_map = self._fr_caisse_ap_ip_cc_map()
        cc_reverse_map = {value: key for key, value in cc_map.items()}
        logger.info(
            "Sending %s %s %s %s cents to payment terminal %s:%s",
            msg_dict["CD"] == "1" and "reimbursement" or "payment",
            cc_reverse_map.get(msg_dict.get("CC"), "card"),
            data["currency"].name,
            data["amount_str"],
            ip_addr,
            port,
        )
        logger.debug("Data about to be sent to payment terminal: %s", msg_str)
        threading.Thread(
            target=_terminal_thread,
            args=(
                self.env.cr.dbname,
                payment_method_id,
                data["pos_config_id"],
                payment_id,
                msg_bytes,
                msg_dict,
                ip_addr,
                port,
                timeout_sec,
            ),
            daemon=True,
        ).start()
        return {"payment_status": "waiting", "payment_id": payment_id}

    def _fr_caisse_ap_ip_lock_buffer(self):
        """Read the buffer with the row locked, for a safe read-modify-write.

        Reading through the ORM would serve a cached value and let two writers
        overwrite each other; the lock makes them queue instead.
        """
        self.ensure_one()
        self.env.cr.execute(
            "SELECT fr_caisse_ap_ip_latest_response FROM pos_payment_method "
            "WHERE id = %s FOR UPDATE",
            (self.id,),
        )
        row = self.env.cr.fetchone()
        self.invalidate_recordset(["fr_caisse_ap_ip_latest_response"])
        return json.loads((row and row[0]) or "{}")

    def _fr_caisse_ap_ip_store_answer(self, payment_id, res):
        """Buffer the answer, keyed by payment, until the POS collects it.

        Keyed rather than a single slot: a terminal shared by two payments in a
        row (a cancelled one then its retry) must not have one answer silently
        overwrite the other.
        """
        self.ensure_one()
        buf = self._fr_caisse_ap_ip_lock_buffer()
        buf[payment_id] = res
        # Keep the buffer from growing over a whole session
        for stale in list(buf)[:-MAX_BUFFERED_ANSWERS]:
            del buf[stale]
        self.sudo().fr_caisse_ap_ip_latest_response = json.dumps(buf)

    @api.model
    def fr_caisse_ap_ip_get_payment_status(self, payment_method_id, payment_id):
        """Collect the answer of the terminal, once the thread has recorded it.

        The bus notification is the normal path; this is the safety net for a
        POS that missed it (websocket reconnection, tab woken up late). Answers
        in a few milliseconds, so it never holds a worker.
        """
        payment_method = self.browse(payment_method_id).sudo()
        buf = payment_method._fr_caisse_ap_ip_lock_buffer()
        if payment_id not in buf:
            return {"payment_status": "waiting"}
        res = buf.pop(payment_id)
        payment_method.fr_caisse_ap_ip_latest_response = json.dumps(buf)
        logger.debug("JSON sent back to POS: %s", res)
        return res

    @api.model
    def fr_caisse_ap_ip_cancel_payment(self, payment_id):
        """Close the socket of a payment the cashier gave up on."""
        with _ACTIVE_SOCKETS_LOCK:
            sock = _ACTIVE_SOCKETS.get(payment_id)
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError as e:
                logger.debug("Could not shutdown terminal socket: %s", e)
        return True

    def _fr_caisse_ap_ip_build_result(self, answer, msg_dict, error, ip_addr, port):
        """Turn what came back from the terminal into the POS answer."""
        if error:
            return {
                "payment_status": "issue",
                "error_message": _(
                    "Failure in the connection to the payment terminal"
                    " on %(ip_addr)s port %(port)s: %(error)s.",
                    ip_addr=ip_addr,
                    port=port,
                    error=error,
                ),
            }
        if not answer:
            return {
                "payment_status": "issue",
                "error_message": _(
                    "Empty answer from payment terminal. This should never happen."
                ),
            }
        logger.debug("Answer received from payment terminal: %s", answer)
        return self._fr_caisse_ap_ip_answer(answer, msg_dict)

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
            error_msg = _(
                "Error in the communication with the payment terminal: "
                "the action statuts is invalid (AE=%s). "
                "This should never happen!"
            ) % answer_dict.get("AE")
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
                fail_res["error_message"] = _(
                    "Caisse AP IP protocol: tag %s is required but it is "
                    "not present in the answer from the terminal. "
                    "This should never happen!"
                ) % answer_dict.get(tag)
                return fail_res
            if (
                props["fixed_size"]
                and answer_dict.get(tag)
                and answer_dict[tag] != msg_dict[tag]
            ):
                fail_res["error_message"] = _(
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
                strip_answer = answer_dict[tag].lstrip("0")
                if msg_dict[tag] != strip_answer:
                    fail_res["error_message"] = _(
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
            "0": "Autres",
            "1": "CB contact",
            "2": "Amex contact",
            "3": "CB Enseigne",
            "5": "Cofinoga",
            "6": "Diners",
            "7": "CB-Pass",
            "8": "Franfinance",
            "9": "JCB",
            "A": "Banque Accord",
            "B": "CB sans contact",
            "C": "Chèque",
            "D": "Amex sans contact",
            "E": "CMCIC-Pay TPE",
            "G": "QuickPass UPI sans contact Crédit Agricole",
            "I": "CPEI",
            "S": "Carte magasin",
            "U": "UPI / NX3",
            "V": "ANCV",
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
            cc_label = cc_labels.get(cc_tag, _("unknown"))
            card_type_list.append(
                _("Application %(label)s (code %(code)s)", label=cc_label, code=cc_tag)
            )
            ticket = _("Card type: %s") % cc_label
        if answer_dict.get("CI") and len(answer_dict["CI"]) == 1:
            card_type_list.append(
                _(
                    "Read mode: %(label)s (code %(code)s)",
                    label=ci_labels.get(answer_dict["CI"], _("unknown")),
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
        error_msg = _("The payment transaction has failed.")
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
            error_msg = _("The payment transaction has failed: %s") % label
        res = {
            "payment_status": "failure",
            "error_message": error_msg,
        }
        logger.info("Failure answer from payment terminal (failure report: %s)", label)
        return res

    def _fr_caisse_ap_ip_parse_answer(self, data_str):
        logger.debug("Received raw data: %s", data_str)
        data_dict = {}
        i = 0
        while i < len(data_str):
            tag = data_str[i : i + 2]
            i += 2
            size_str = data_str[i : i + 3]
            size = int(size_str)
            i += 3
            value = data_str[i : i + size]
            data_dict[tag] = value
            i += size
        logger.debug("Answer dict: %s", data_dict)
        return data_dict

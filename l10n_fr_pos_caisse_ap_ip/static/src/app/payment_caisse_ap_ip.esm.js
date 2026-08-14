/*
    Copyright 2023 Akretion France (http://www.akretion.com/)
    @author: Alexis de Lattre <alexis.delattre@akretion.com>
    @author: Rémi de Lattre <remi@miluni.fr>
    @author: Pierrick Brun <pierrick.brun@akretion.com>
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/

import {AlertDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {PaymentInterface} from "@point_of_sale/app/payment/payment_interface";
import {_t} from "@web/core/l10n/translation";

// Safety net when the bus notification never arrives, in ms
const POLL_INTERVAL = 5000;
// Timeout used in the POS and in the back-end, in ms
const PAYMENT_TIMEOUT = 180000;

export class PaymentCaisseAPIP extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        // Pending payments, keyed by payment line uuid
        this.pendingPayments = {};
    }

    async send_payment_cancel(order, uuid) {
        super.send_payment_cancel(...arguments);
        if (this.pendingPayments[uuid]) {
            this.pos.data
                .silentCall("pos.payment.method", "fr_caisse_ap_ip_cancel_payment", [
                    uuid,
                ])
                .catch(() => {
                    // Nothing to do: the terminal keeps the last word
                });
        }
        this._show_error(
            _t(
                "Press the red button on the payment terminal to cancel the transaction."
            )
        );
        return true;
    }

    _handle_caisse_ap_ip_response(pay_line, response) {
        if (response.payment_status === "success") {
            pay_line.card_type = response.card_type;
            pay_line.transaction_id = response.transaction_id;
            if ("ticket" in response) {
                pay_line.set_receipt_info(response.ticket);
            }
            return true;
        }
        return this._handle_error(response.error_message);
    }

    _handle_caisse_ap_ip_unexpected_response(pay_line) {
        // The response cannot be understood
        // We let the cashier handle it manually (force or cancel)
        pay_line.set_payment_status("force_done");
        return Promise.reject();
    }

    get fast_payments() {
        var fast_payment = this.payment_method_id.fr_caisse_ap_ip_fast_payment || false;
        return fast_payment;
    }

    async send_payment_request(uuid) {
        await super.send_payment_request(...arguments);
        const order = this.pos.get_order();
        const pay_line = order.get_selected_paymentline();
        const data = {
            amount: pay_line.amount,
            currency_id: this.pos.currency.id,
            payment_method_id: this.payment_method_id.id,
            pos_config_id: this.pos.config.id,
            payment_id: uuid,
            timeout: PAYMENT_TIMEOUT,
        };
        pay_line.set_payment_status("waitingCard");
        return this.pos.data
            .silentCall("pos.payment.method", "fr_caisse_ap_ip_send_payment", [data])
            .then((response) => {
                if (!(response instanceof Object) || !("payment_status" in response)) {
                    return this._handle_caisse_ap_ip_unexpected_response(pay_line);
                }
                if (response.payment_status !== "waiting") {
                    // Rejected before the terminal was even contacted
                    return this._handle_caisse_ap_ip_response(pay_line, response);
                }
                // The server talks to the terminal in the background: the answer
                // comes back over the bus, so no HTTP worker is held meanwhile
                return this._wait_for_answer(pay_line, uuid);
            })
            .catch(() => {
                const error_msg = _t(
                    "No answer from the payment terminal in the given time."
                );
                return this._handle_error(error_msg);
            });
    }

    _wait_for_answer(pay_line, uuid) {
        const deadline = Date.now() + PAYMENT_TIMEOUT;
        return new Promise((resolve) => {
            const pending = {pay_line: pay_line, resolve: resolve};
            this.pendingPayments[uuid] = pending;
            pending.poll = setInterval(() => {
                // Safety net: a missed bus notification must not leave the
                // cashier in front of a screen that never moves
                this.pos.data
                    .silentCall(
                        "pos.payment.method",
                        "fr_caisse_ap_ip_get_payment_status",
                        [this.payment_method_id.id, uuid]
                    )
                    .then((response) => {
                        if (
                            response instanceof Object &&
                            response.payment_status &&
                            response.payment_status !== "waiting"
                        ) {
                            this.handleTerminalResponse(response, uuid);
                        } else if (Date.now() > deadline) {
                            this._give_up(uuid);
                        }
                    })
                    .catch(() => {
                        if (Date.now() > deadline) {
                            this._give_up(uuid);
                        }
                    });
            }, POLL_INTERVAL);
        });
    }

    handleTerminalResponse(response, uuid) {
        const payment_id = uuid || response.payment_id;
        const pending = this.pendingPayments[payment_id];
        if (!pending) {
            // Answer of a payment this interface is not waiting for
            return;
        }
        this._clear_pending(payment_id);
        pending.resolve(
            this._handle_caisse_ap_ip_response(pending.pay_line, response)
        );
    }

    _give_up(uuid) {
        const pending = this.pendingPayments[uuid];
        if (!pending) {
            return;
        }
        this._clear_pending(uuid);
        // Let the cashier force or cancel rather than wait forever
        pending.resolve(
            this._handle_caisse_ap_ip_unexpected_response(pending.pay_line)
        );
    }

    _clear_pending(uuid) {
        const pending = this.pendingPayments[uuid];
        if (pending && pending.poll) {
            clearInterval(pending.poll);
        }
        delete this.pendingPayments[uuid];
    }

    _handle_error(msg) {
        this._show_error(msg);
        return false;
    }

    _show_error(msg, title) {
        this.env.services.dialog.add(AlertDialog, {
            title: title || _t("Payment Terminal Error"),
            body: msg,
        });
    }
}

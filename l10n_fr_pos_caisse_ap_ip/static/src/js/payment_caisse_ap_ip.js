/*
    Copyright 2023 Akretion France (http://www.akretion.com/)
    @author: Alexis de Lattre <alexis.delattre@akretion.com>
    @author: Rémi de Lattre <remi@miluni.fr>
    @author: Pierrick Brun <pierrick.brun@akretion.com>
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/

odoo.define("l10n_fr_pos_caisse_ap_ip.payment", function (require) {
    "use strict";

    var core = require("web.core");
    var rpc = require("web.rpc");
    var PaymentInterface = require("point_of_sale.PaymentInterface");
    const {Gui} = require("point_of_sale.Gui");

    var _t = core._t;

    // Delay between two polls of the payment status, in ms
    const POLL_INTERVAL = 2000;

    var PaymentCaisseApIp = PaymentInterface.extend({
        init: function () {
            this._super.apply(this, arguments);
            this.polling = null;
            this.pending_payment_id = null;
        },

        send_payment_cancel: function () {
            this._super.apply(this, arguments);
            var payment_id = this.pending_payment_id;
            this._stop_polling();
            if (payment_id) {
                rpc.query(
                    {
                        model: "pos.payment.method",
                        method: "fr_caisse_ap_ip_cancel_payment",
                        args: [payment_id],
                    },
                    {shadow: true}
                ).catch(() => {
                    // Nothing to do: the terminal keeps the last word
                });
            }
            this._show_error(
                _t(
                    "Press the red button on the payment terminal to cancel the transaction."
                )
            );
            return true;
        },
        _stop_polling: function () {
            if (this.polling) {
                clearInterval(this.polling);
                this.polling = null;
            }
            this.pending_payment_id = null;
        },
        _handle_caisse_ap_ip_response: function (pay_line, response) {
            if (response.payment_status === "success") {
                pay_line.card_type = response.card_type;
                pay_line.transaction_id = response.transaction_id;
                if ("ticket" in response) {
                    pay_line.set_receipt_info(response.ticket);
                }
                return true;
            }
            return this._handle_error(response.error_message);
        },
        _handle_caisse_ap_ip_unexpected_response: function (pay_line) {
            // The response cannot be understood
            // We let the cashier handle it manually (force or cancel)
            pay_line.set_payment_status("force_done");
            return Promise.reject();
        },
        send_payment_request: function (cid) {
            this._super.apply(this, arguments);
            var order = this.pos.get_order();
            var pay_line = order.selected_paymentline;
            var currency = this.pos.currency;
            // Define the timout used in the pos and in the back-end (in ms)
            const timeout = 180000;
            var data = {
                amount: pay_line.amount,
                currency_id: currency.id,
                payment_method_id: this.payment_method.id,
                payment_id: cid,
                timeout: timeout,
            };
            pay_line.set_payment_status("waitingCard");
            return rpc
                .query(
                    {
                        model: "pos.payment.method",
                        method: "fr_caisse_ap_ip_send_payment",
                        args: [data],
                    },
                    {shadow: true}
                )
                .then((response) => {
                    if (!(response instanceof Object) || !("payment_status" in response)) {
                        return this._handle_caisse_ap_ip_unexpected_response(pay_line);
                    }
                    if (response.payment_status !== "waiting") {
                        // Rejected before the terminal was even contacted
                        return this._handle_caisse_ap_ip_response(pay_line, response);
                    }
                    // The server talks to the terminal in the background: poll
                    // for the answer instead of holding an HTTP worker
                    return this._poll_for_answer(pay_line, cid, timeout);
                })
                .catch(() => {
                    const error_msg = _t(
                        "No answer from the payment terminal in the given time."
                    );
                    return this._handle_error(error_msg);
                });
        },

        _poll_for_answer: function (pay_line, cid, timeout) {
            this._stop_polling();
            this.pending_payment_id = cid;
            const deadline = Date.now() + timeout;
            return new Promise((resolve) => {
                const done = (value) => {
                    this._stop_polling();
                    resolve(value);
                };
                this.polling = setInterval(() => {
                    rpc.query(
                        {
                            model: "pos.payment.method",
                            method: "fr_caisse_ap_ip_get_payment_status",
                            args: [this.payment_method.id, cid],
                        },
                        {shadow: true}
                    )
                        .then((response) => {
                            if (
                                response instanceof Object &&
                                response.payment_status &&
                                response.payment_status !== "waiting"
                            ) {
                                done(
                                    this._handle_caisse_ap_ip_response(
                                        pay_line,
                                        response
                                    )
                                );
                            } else if (Date.now() > deadline) {
                                // The answer never came: let the cashier force
                                // or cancel rather than wait forever
                                done(
                                    this._handle_caisse_ap_ip_unexpected_response(
                                        pay_line
                                    )
                                );
                            }
                        })
                        .catch(() => {
                            if (Date.now() > deadline) {
                                done(
                                    this._handle_error(
                                        _t(
                                            "No answer from the payment terminal in the given time."
                                        )
                                    )
                                );
                            }
                            // Otherwise: transient error, next poll retries
                        });
                }, POLL_INTERVAL);
            });
        },

        _handle_error: function (msg) {
            this._show_error(msg);
            return false;
        },
        _show_error: function (msg, title) {
            Gui.showPopup("ErrorPopup", {
                title: title || _t("Payment Terminal Error"),
                body: msg,
            });
        },
    });
    return PaymentCaisseApIp;
});

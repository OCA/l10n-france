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

    var PaymentCaisseApIp = PaymentInterface.extend({
        init: function () {
            this._super.apply(this, arguments);
        },

        send_payment_cancel: function () {
            this._super.apply(this, arguments);
            this._show_error(
                _t(
                    "Press the red button on the payment terminal to cancel the transaction."
                )
            );
            return true;
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
                    {
                        timeout: timeout,
                        shadow: true,
                    }
                )
                .then((response) => {
                    if (response instanceof Object && "payment_status" in response) {
                        // The response is a valid object
                        return this._handle_caisse_ap_ip_response(pay_line, response);
                    }
                    return this._handle_caisse_ap_ip_unexpected_response(pay_line);
                })
                .catch(() => {
                    // It should be a request timeout
                    const error_msg = _t(
                        "No answer from the payment terminal in the given time."
                    );
                    return this._handle_error(error_msg);
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

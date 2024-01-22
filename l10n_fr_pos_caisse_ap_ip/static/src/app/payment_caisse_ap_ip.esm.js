/** @odoo-module */
/*
    Copyright 2023 Akretion France (http://www.akretion.com/)
    @author: Alexis de Lattre <alexis.delattre@akretion.com>
    @author: Rémi de Lattre <remi@miluni.fr>
    @author: Pierrick Brun <pierrick.brun@akretion.com>
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/

import {ErrorPopup} from "@point_of_sale/app/errors/popups/error_popup";
import {PaymentInterface} from "@point_of_sale/app/payment/payment_interface";
import {_t} from "@web/core/l10n/translation";

export class PaymentCaisseAPIP extends PaymentInterface {
    setup() {
        super.setup(...arguments);
    }

    async send_payment_cancel() {
        super.send_payment_cancel(...arguments);
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

    async send_payment_request(cid) {
        await super.send_payment_request(...arguments);
        const order = this.pos.get_order();
        const pay_line = order.selected_paymentline;
        // Define the timout used in the POS and in the back-end (in ms)
        const timeout = 180000;
        const data = {
            amount: pay_line.amount,
            currency_id: this.pos.currency.id,
            payment_method_id: this.payment_method.id,
            payment_id: cid,
            timeout: timeout,
        };
        pay_line.set_payment_status("waitingCard");
        return this.env.services.orm.silent
            .call("pos.payment.method", "fr_caisse_ap_ip_send_payment", [data])
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
    }

    _handle_error(msg) {
        this._show_error(msg);
        return false;
    }

    _show_error(msg, title) {
        this.env.services.popup.add(ErrorPopup, {
            title: title || _t("Payment Terminal Error"),
            body: msg,
        });
    }
}

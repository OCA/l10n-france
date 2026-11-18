/*
    Copyright 2023 Akretion France (http://www.akretion.com/)
    @author: Alexis de Lattre <alexis.delattre@akretion.com>
    @author: Rémi de Lattre <remi@miluni.fr>
    @author: Pierrick Brun <pierrick.brun@akretion.com>
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/

import {AlertDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {PaymentInterface} from "@point_of_sale/app/utils/payment/payment_interface";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";

export class PaymentCaisseAPIP extends PaymentInterface {
    setup() {
        super.setup(...arguments);
    }

    async sendPaymentCancel() {
        super.sendPaymentCancel(...arguments);
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
            if (response.ticket) {
                pay_line.setCashierReceipt(response.ticket);
            }
            return true;
        }
        return this._handle_error(response.error_message);
    }

    _handle_caisse_ap_ip_unexpected_response() {
        // The response cannot be understood
        // We let the cashier handle it manually (force or cancel)
        this._show_error(
            _t(
                "The terminal response is unclear. Check the terminal receipt before completing the payment manually."
            )
        );
        return Promise.reject();
    }

    async sendPaymentRequest(pay_line) {
        await super.sendPaymentRequest(...arguments);
        // Define the timeout used in the POS and in the back-end (in ms)
        const timeout = 180000;
        const data = {
            amount: pay_line.amount,
            currency_id: pay_line.currency.id,
            payment_method_id: this.payment_method_id.id,
            payment_id: pay_line.uuid,
            timeout: timeout,
        };
        pay_line.setPaymentStatus("waitingCard");
        return this.callPaymentMethod("fr_caisse_ap_ip_send_payment", [data])
            .then((response) => {
                if (response instanceof Object && "payment_status" in response) {
                    // The response is a valid object
                    return this._handle_caisse_ap_ip_response(pay_line, response);
                }
                return this._handle_caisse_ap_ip_unexpected_response();
            })
            .catch((error) => {
                if (error === undefined) {
                    return Promise.reject();
                }
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
        this.env.services.dialog.add(AlertDialog, {
            title: title || _t("Payment Terminal Error"),
            body: msg,
        });
    }
}

registry.category("pos_payment_providers").add("fr-caisse_ap_ip", PaymentCaisseAPIP);

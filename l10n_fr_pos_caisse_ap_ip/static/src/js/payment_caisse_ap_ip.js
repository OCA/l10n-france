/*
    Copyright 2023 Akretion France (http://www.akretion.com/)
    @author: Alexis de Lattre <alexis.delattre@akretion.com>
    @author: Rémi de Lattre <remi@miluni.fr>
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/

odoo.define("pos_caisse_ap_ip.payment", function (require) {
    "use strict";

    var core = require("web.core");
    var rpc = require('web.rpc');
    var PaymentInterface = require("point_of_sale.PaymentInterface");
    const {Gui} = require("point_of_sale.Gui");

    var _t = core._t;

    var PaymentCaisseApIp = PaymentInterface.extend({
        init: function () {
            this._super.apply(this, arguments);
        },

        send_payment_request: function (cid) {
            console.log('send_payment_request');
            this._super.apply(this, arguments);
            // check that this.payment_method.use_payment_terminal is ??
            return this._caisse_ap_ip_pay(cid);
        },

        send_payment_cancel: function (order, cid) {
            console.log('send_payment_cancel');
            this._super.apply(this, arguments);
            this._show_error(
                _t(
                    "Please press the red button on the payment terminal to cancel the transaction."
                )
            );
            return Promise.reject();
        },

        _caisse_ap_ip_pay: function (cid) {
            console.log('_caisse_ap_ip_pay===== cid=');
            console.log(cid);
            var order = this.pos.get_order();
            var pay_line = order.selected_paymentline;
            var currency = this.pos.currency;
            console.log('Currency=');
            console.log('THIS1====');
            console.log(this);
            console.log(currency);
            var data = {
                amount: pay_line.amount,
                currency_id: currency.id,
                payment_method_id: this.payment_method.id,
                payment_id: cid,
                //order_id: order.name,
            };
            console.log('data====');
            console.log(data);
/*            if (this.payment_method.oca_payment_terminal_id) {
                data.terminal_id = this.payment_method.oca_payment_terminal_id;
            }  */
            return this._caisse_ap_ip_request(data).then((response) => {
                if (response === false) {
                    this._show_error(
                        _t(
                            "Failed to send the amount to pay to the payment terminal. Press the red button on the payment terminal and try again."
                        )
                    );
                    // There was an error, let the user retry.
                    return false;
                } else if (response instanceof Object && "transaction_id" in response) {
                    // The response has a terminal transaction identifier:
                    // return a promise that polls for transaction status.
                    pay_line.set_payment_status("waitingCard");
                    this._caisse_ap_ip_update_payment_line_terminal_transaction_status(
                        pay_line,
                        response
                    );
                    return new Promise((resolve, reject) => {
                        this._caisse_ap_ip_poll_for_transaction_status(
                            pay_line,
                            resolve,
                            reject
                        );
                    });
                }

                // The transaction was started, but the terminal driver
                // does not report status, so we won't know the
                // transaction result: we let the user enter the
                // outcome manually. This is done by rejecting the
                // promise as explained in the send_payment_request()
                // documentation.
                pay_line.set_payment_status("force_done");
                return Promise.reject();
            });
        },

        _caisse_ap_ip_poll_for_transaction_status: function (pay_line, resolve, reject) {
            var timerId = setInterval(() => {
                // Query the driver status more frequently than the regular POS
                // proxy, to get faster feedback when the transaction is
                // complete on the terminal.
                var status_params = {};
                if (this.payment_method.oca_payment_terminal_id) {
                    status_params.terminal_id =
                        this.payment_method.oca_payment_terminal_id;
                }
                this.pos.env.proxy.connection
                    .rpc("/hw_proxy/status_json", status_params, {
                        shadow: true,
                        timeout: 1000,
                    })
                    .then((drivers_status) => {
                        for (var driver_name in drivers_status) {
                            // Look for a driver that is a payment terminal and has
                            // transactions.
                            var driver = drivers_status[driver_name];
                            if (!driver.is_terminal || !("transactions" in driver)) {
                                continue;
                            }
                            for (var transaction_id in driver.transactions) {
                                var transaction = driver.transactions[transaction_id];
                                if (
                                    transaction.transaction_id ===
                                    pay_line.terminal_transaction_id
                                ) {
                                    // Look for the transaction corresponding to
                                    // the payment line.
                                    this._caisse_ap_ip_update_payment_line_terminal_transaction_status(
                                        pay_line,
                                        transaction
                                    );
                                    if (
                                        pay_line.terminal_transaction_success !== null
                                    ) {
                                        resolve(pay_line.terminal_transaction_success);
                                        // Stop the loop
                                        clearInterval(timerId);
                                    }
                                }
                            }
                        }
                    })
                    .catch(() => {
                        console.error("Error querying terminal driver status");
                        // We could not query the transaction status so we
                        // won't know the transaction result: we let the user
                        // enter the outcome manually. This is done by
                        // rejecting the promise as explained in the
                        // send_payment_request() documentation.
                        pay_line.set_payment_status("force_done");
                        reject();
                        // Stop the loop
                        clearInterval(timerId);
                    });
            }, 1000);
        },

        _caisse_ap_ip_update_payment_line_terminal_transaction_status: function (
            pay_line,
            transaction
        ) {
            pay_line.terminal_transaction_id = transaction.transaction_id;
            pay_line.terminal_transaction_success = transaction.success;
            pay_line.terminal_transaction_status = transaction.status;
            pay_line.terminal_transaction_status_details = transaction.status_details;
            // Payment transaction reference, for accounting reconciliation purposes.
            pay_line.transaction_id = transaction.reference;
        },

        _caisse_ap_ip_request: function (data) {
            console.log('_caisse_ap_ip_payment_terminal_request data=');
            console.log(data);
            var self = this;
            console.log('this===');
            console.log(this);
            rpc.query({
                model: "pos.payment.method",
                method: "caisse_ap_ip_send_payment",
                args: [data],
            }, {
            timeout: 5000,
            shadow: true,
        }).then((response) => {
                    return response;
                })
                .catch(() => {
                    console.error("Error starting payment transaction");
                    return false;
                })
                ;
/*
            return this.pos.env.proxy
                .message("payment_terminal_transaction_start", {
                    payment_info: JSON.stringify(data),
                })
                .then((response) => {
                    return response;
                })
                .catch(() => {
                    console.error("Error starting payment transaction");
                    return false;
                });  */
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

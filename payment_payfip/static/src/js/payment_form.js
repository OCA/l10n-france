odoo.define("payment_payfip.payment_form", function (require) {
    "use strict";

    const PaymentForm = require("payment.payment_form");
    const Core = require("web.core");
    const ajax = require("web.ajax");
    const _t = Core._t;

    PaymentForm.include({

        /**
         * PayFIP requires the payment processor tab to be in a popup, and doesn't
         * redirect the user back to the redirect url.
         *
         * @override
         */
        payEvent: function(ev) {
            let checked_radio = this.$('input[type="radio"]:checked');
            if (
                checked_radio.length === 1
                && $(checked_radio).data("provider") == "payfip"
                && this.isFormPaymentRadio(checked_radio)
            ) {
                return this._payEventPayFIP(ev);
            } else {
                return this._super.apply(this, arguments);
            }
        },

        /**
         * Most lines are just copied from the core method
         * Similar to how form payments are handled in core, however we want to:
         * - display it in a popup instead
         * - block the ui while the popup is open
         * - redirect to /payment/processing after the popup is closed
         */
        _payEventPayFIP: function(ev) {
            const self = this;
            let button = ev.target;
            let checked_radio = this.$('input[type="radio"]:checked')[0];
            let acquirer_id = this.getAcquirerIdFromRadio(checked_radio);
            let acquirer_form = this.$('#o_payment_form_acq_' + acquirer_id);
            let $tx_url = this.$el.find('input[name="prepare_tx_url"]');
            this.disableButton(button);
            // if there's a prepare tx url set
            if ($tx_url.length === 1) {
                // if the user wants to save his credit card info
                var form_save_token = acquirer_form.find('input[name="o_payment_form_save_token"]').prop('checked');
                // then we call the route to prepare the transaction
                return ajax.jsonRpc($tx_url[0].value, 'call', {
                    'acquirer_id': parseInt(acquirer_id),
                    'save_token': form_save_token,
                    'access_token': self.options.accessToken,
                    'success_url': self.options.successUrl,
                    'error_url': self.options.errorUrl,
                    'callback_method': self.options.callbackMethod,
                    'order_id': self.options.orderId,
                }).then(function (result) {
                    if (result) {
                        // If the server sent us the html form, we create a form element
                        // Al of these lines are exactly the same than in core, except for commeted parts
                        var newForm = document.createElement('form');
                        newForm.setAttribute("method", "post");
                        newForm.setAttribute("provider", checked_radio.dataset.provider);
                        newForm.hidden = true;
                        newForm.innerHTML = result;
                        var action_url = $(newForm).find('input[name="data_set"]').data('actionUrl');
                        newForm.setAttribute("action", action_url);
                        $(document.getElementsByTagName('body')[0]).append(newForm);
                        $(newForm).find('input[data-remove-me]').remove();
                        if (action_url) {
                            // Handle form in a popup, special case for payfip
                            // Create a new window tab with recommended settings in payfip documentation
                            const width = Math.max(900, Math.min(1200, window.top.outerWidth * 0.9));
                            const height = Math.max(700, Math.min(1000, window.top.outerHeight * 0.9));
                            const payfipPopupSettings = [
                                "width=" + width,
                                "height=" + height,
                                "left=" + (window.top.outerWidth / 2 + window.top.screenX - (width / 2)),
                                "top=" + (window.top.outerHeight / 2 + window.top.screenY - (height / 2)),
                                "toolbar=no",
                                "menubar=no",
                                "scrollbars=no",
                                "resizeable=yes",
                                "location=no",
                                "directories=no",
                                "status=no",
                            ]
                            const payfipPopup = window.open('', 'payfip-popup', payfipPopupSettings.join(","));
                            newForm.setAttribute("target", "payfip-popup");
                            // Submit the form
                            newForm.submit();
                            if (payfipPopup.focus) { payfipPopup.focus(); }
                            // Block the UI
                            $.blockUI({
                                'message': (
                                    '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/></h2>'
                                    + '<h2 class="text-white">' + _t("Please proceed with payment..") + '</h2>'
                                    + '<p class="text-center text-white">'
                                    + _t("After payment is done, you'll be redirected to ")
                                    + '<a class="text-white" href="/payment/process">' + _t("payment processing") + '</a></p>'
                                    + '<p class="text-center text-white">' + _t("If the popup doesn't open, please check your browser settings.") + '</p>'
                                )
                            });
                            // Keep a timer checking when the popup is closed and redirect to /payment/process
                            // Simply hooking to the unload event doesn't work in some browsers, apparently.
                            let timer = setInterval(function() {   
                                if (payfipPopup.closed) {                             
                                    clearInterval(timer);
                                    if (window.focus) { window.focus(); }
                                    window.location.href = "/payment/process";
                                }  
                            }, 1000); 
                            return $.Deferred();
                        }
                    } else {
                        self.displayError(
                            _t('Server Error'),
                            _t("We are not able to redirect you to the payment form.")
                        );
                        self.enableButton(button);
                    }
                }).fail(function (error, event) {
                    self.displayError(
                        _t('Server Error'),
                        _t("We are not able to redirect you to the payment form. ") +
                            error.data.message
                    );
                    self.enableButton(button);
                });
            } else {
                // we append the form to the body and send it.
                this.displayError(
                    _t("Cannot set-up the payment"),
                    _t("We're unable to process your payment.")
                );
            }
        },
    })

    return PaymentForm;

});

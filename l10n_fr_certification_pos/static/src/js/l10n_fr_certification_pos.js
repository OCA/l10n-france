/******************************************************************************
    Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
    Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
    @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 *****************************************************************************/
'use strict';

openerp.l10n_fr_certification_pos = function(instance, local) {

    var module = instance.point_of_sale;
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;
    var round_pr = instance.web.round_precision;

    /*************************************************************************
        Promise that will be resolved, when the hash of the saved order is
        known
    */
    var certification_deferred = null;

    /*************************************************************************
        Function that return certification text, depending of a hash
    */
    var prepare_certification_text = function(hash, setting){
        if (setting === 'no'){
            return false;
        }
        if (hash){
            return _t('Certification Number: ') + hash.substring(0, 10) + '...' + hash.substring(hash.length - 10);
        }
        return _t("Because of a network problem," +
            " this ticket could not be certified." +
            " You can ask later for a certified ticket.");
    };

    /*************************************************************************
        Extend module.Order:
            Add a new certification_text field that will content a text and
            the hash of the PoS Order, or a warning if hash has not been
            recovered.
    */
    var moduleOrderParent = module.Order;
    module.Order = module.Order.extend({
        set_hash: function(hash, setting) {
            this.set({
                hash: hash,
                certification_text: prepare_certification_text(hash, setting),
            });
        },

        export_for_printing: function(attributes){
            var order = moduleOrderParent.prototype.export_for_printing.apply(this, arguments);
            if (this.pos.config.l10n_fr_prevent_print === 'no'){
                order.certification_text = false;
            } else {
                // We add a tag that will be replaced after, because
                // when export_for_printing is called, hash is unknown
                order.certification_text = "__CERTIFICATION_TEXT__";
            }
            return order;
        },

        export_as_JSON: function() {
            var order = moduleOrderParent.prototype.export_as_JSON.apply(this, arguments);
            order.certification_text = this.get('certification_text');
            return order;
        },

    });

    /*************************************************************************
        Extend module.PosModel:
            Overload _save_to_server and store if the order has been
            correctly created in the promise 'last_orders'
    */
    var PosModelParent = module.PosModel;
    module.PosModel = module.PosModel.extend({
        _save_to_server: function (orders, options) {
            var self = this;

            // Get PoS Config Settings
            var setting = self.config.l10n_fr_prevent_print;

            if (setting === 'no'){
                return PosModelParent.prototype._save_to_server.apply(this, arguments);
            }
            // Create a new promise that will resolved after the call to get the hash
            certification_deferred = new $.Deferred();

            var current_order = self.get('selectedOrder');
            // Init hash (and description that will be used, if server is unreachable)
            current_order.set_hash(false, setting);

            return PosModelParent.prototype._save_to_server.apply(this, arguments).then(function(server_ids) {
                if (server_ids) {
                    if (server_ids.length > 0){
                        // Try to get hash of saved orders, if required
                        var posOrderModel = new instance.web.Model('pos.order');
                        return posOrderModel.call(
                            'get_certification_information', [server_ids], false
                        ).then(function (results) {
                            var hash = false;
                            _.each(results, function(result){
                                if (result.pos_reference.indexOf(current_order.uid) > 0) {
                                    hash = result.l10n_fr_hash;
                                    current_order.set_hash(hash, setting);
                                }
                            });
                            certification_deferred.resolve(hash);
                            return server_ids;
                        }).fail(function (error, event){
                            certification_deferred.reject();
                            return server_ids;
                        });
                    }
                    certification_deferred.resolve(false);
                    return server_ids;
                }
                certification_deferred.reject();
            }, function error() {
                certification_deferred.reject();
            });
        },
    });

    /*************************************************************************
        Extend ReceiptScreenWidgetParent:
            if iface_print_via_proxy IS NOT enabled,
            if certification security is enabled, wait for result,
            before printing. Display an error message if hash has not
            been recovered and setting is set to 'block'.
    */
    var ReceiptScreenWidgetParent = module.ReceiptScreenWidget;
    module.ReceiptScreenWidget = module.ReceiptScreenWidget.extend({

        // Overload Function
        show: function(){
            var self = this;
            var setting = this.pos.config.l10n_fr_prevent_print;
            if (setting === 'no'){
                // Direct Call
                self.show_certification(setting);
            } else {
                // Wait for Promise
                certification_deferred.then(function success(order_id) {
                    self.show_certification(setting);
                }, function error() {
                    self.show_certification(setting);
                });
            }
        },

        // New Function
        show_certification: function(setting){
            if (!this.pos.get('selectedOrder').get('hash') && setting === 'block') {
                // mark the bill as printed to avoid a useless window.print call
                this.pos.get('selectedOrder')._printed = true;

                // Call super, to display 'Next order' Button, and finish the workflow
                ReceiptScreenWidgetParent.prototype.show.apply(this, []);

                // hide the ticket to avoid manual printing
                this.$('.pos-sale-ticket').hide();

                this.pos.pos_widget.screen_selector.show_popup('error', {
                    message: _t('Connection required'),
                    comment: _t('Can not print the bill because your point of sale is currently offline'),
                });
            } else {
                // Display the bill for printing
                ReceiptScreenWidgetParent.prototype.show.apply(this, []);
            }
            certification_deferred = null;
        },
    });

    /*************************************************************************
        Extend module.ProxyDevice:
            if iface_print_via_proxy IS enabled,
            if certification security is enabled, wait for result,
            before printing. Display an error message if hash has not
            been recovered and setting is set to 'block'.
    */
    var ProxyDeviceParent = module.ProxyDevice;
    module.ProxyDevice = module.ProxyDevice.extend({

        // Overload Function
        print_receipt: function(receipt){
            var self = this;
            var setting = this.pos.config.l10n_fr_prevent_print;
            if (receipt){
                if (setting === 'no'){
                    self.print_receipt_certification(receipt, setting, false);
                } else {
                    certification_deferred.then(function success(hash) {
                        self.print_receipt_certification(receipt, setting, hash);
                    }, function error() {
                        self.print_receipt_certification(receipt, setting, false);
                    });
                }
            } else {
                // Weird core feature, print_receipt is called regularly
                // without receipt
                ProxyDeviceParent.prototype.print_receipt.apply(this, [receipt]);
            }
        },

        print_receipt_certification: function(receipt, setting, hash){
            if (!hash && setting === 'block') {
                // block the printing
                this.pos.pos_widget.screen_selector.show_popup('error', {
                    message: _t('Connection required'),
                    comment: _t('Can not print the bill because your point of sale is currently offline'),
                });
            } else {
                // Add the according text
                var changed_receipt = receipt.replace("__CERTIFICATION_TEXT__", prepare_certification_text(hash, setting));
                // Print the bill
                ProxyDeviceParent.prototype.print_receipt.apply(this, [changed_receipt]);
            }
            certification_deferred = null;
        },
    });

};

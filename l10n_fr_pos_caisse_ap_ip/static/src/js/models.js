/*
    Copyright 2023 Akretion (www.akretion.com)
    @author: Alexis de Lattre <alexis.delattre@akretion.com>
    @author: Rémi de Lattre <remi@miluni.fr>
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/

odoo.define("l10n_fr_pos_caisse_ap_ip.models", function (require) {
    "use strict";

    var models = require("point_of_sale.models");
    var CaisseAPIP = require("l10n_fr_pos_caisse_ap_ip.payment");
    models.register_payment_method("fr-caisse_ap_ip", CaisseAPIP);
});

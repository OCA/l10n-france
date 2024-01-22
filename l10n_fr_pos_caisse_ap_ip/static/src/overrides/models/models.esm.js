/** @odoo-module */
/*
    Copyright 2023 Akretion (www.akretion.com)
    @author: Alexis de Lattre <alexis.delattre@akretion.com>
    @author: Rémi de Lattre <remi@miluni.fr>
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/

import {PaymentCaisseAPIP} from "@l10n_fr_pos_caisse_ap_ip/app/payment_caisse_ap_ip.esm";
import {register_payment_method} from "@point_of_sale/app/store/pos_store";

register_payment_method("fr-caisse_ap_ip", PaymentCaisseAPIP);

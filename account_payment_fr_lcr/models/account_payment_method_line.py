# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    fr_lcr_type = fields.Selection(
        [
            ("not_accepted", "Lettre de change non acceptée (LCR directe)"),
            ("accepted", "Lettre de change acceptée"),
            ("promissory_note", "Billet à ordre"),
        ],
        compute="_compute_fr_lcr_type",
        store=True,
        readonly=False,
        precompute=True,
        string="Bill of Exchange Type",
    )
    fr_lcr_default_collection_option = fields.Selection(
        "_fr_lcr_collection_option_selection",
        string="Default Collection Option",
        default="due_date",
    )
    fr_lcr_dailly = fields.Boolean(string="Dailly Convention")
    fr_lcr_default_dailly_option = fields.Selection(
        "_fr_lcr_dailly_option_selection",
        default="none",
        string="Default Dailly Option",
    )
    # It seems this field is only used for Dailly... but not 100% sure
    # For the moment, we only display it for Dailly
    fr_lcr_convention_type = fields.Char(
        string="Convention Type",
        size=6,
        help="Field C1 'Convention Type' in CFONB header line, 6 characters maximum.",
    )

    @api.model
    def _fr_lcr_collection_option_selection(self):
        sel = [
            ("due_date", "Encaissement, crédit forfaitaire après l’échéance"),
            (
                "due_date_fixed_delay",
                "Encaissement, crédit après expiration d’un délai forfaitaire",
            ),
            ("cash_discount", "Escompte"),
            # "Escompte en valeur" is also called "Escompte en compte"
            # Great explaination here https://www.netpme.fr/conseil/escompte/
            # click on "2. Modalités de fonctionnement de l’escompte"
            ("value_cash_discount", "Escompte en valeur"),
        ]
        return sel

    @api.model
    def _fr_lcr_dailly_option_selection(self):
        sel = [
            ("none", "Pas d’indication"),
            ("cash_discount", "Cession escompte dans le cadre d’une convention Dailly"),
            (
                "debt_pledge",
                "Nantissement de créance dans le cadre d’une convention Dailly",
            ),
            ("out_of_agreement", "Cession ou nantissement hors convention Dailly"),
        ]
        return sel

    @api.depends("payment_method_id")
    def _compute_fr_lcr_type(self):
        for line in self:
            fr_lcr_type = False
            if line.payment_method_id and line.payment_method_id.code == "fr_lcr":
                fr_lcr_type = "not_accepted"
            line.fr_lcr_type = fr_lcr_type

    @api.constrains("payment_method_id", "fr_lcr_type")
    def _check_fr_lcr(self):
        for line in self:
            if (
                line.payment_method_id
                and line.payment_method_id.code == "fr_lcr"
                and not line.fr_lcr_type
            ):
                raise ValidationError(
                    _(
                        "The field 'Bill of Exchange Type' must be set on "
                        "payment mode '%s'."
                    )
                    % line.display_name
                )

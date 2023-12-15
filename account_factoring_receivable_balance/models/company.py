# © 2022 David BEAL @ Akretion
# © 2022 Alexis DE LATTRE @ Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tests.common import Form


class ResCompany(models.Model):
    _inherit = "res.company"

    factor_config_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Facto Currency",
        help="Use to configure account and journal",
    )

    @api.model
    def _create_french_company(self, company_name=None):
        "Can be called from Odoo Shell"
        demo_cpny_name = "BPCE demo"
        previous_cpny = self.search([("name", "=", demo_cpny_name)], limit=1)
        previous_cpny.write({"name": "Company %s" % previous_cpny.id})
        company = self.create(
            {
                "name": company_name or demo_cpny_name,
                "street": "42 rue du logiciel libre",
                "zip": "69009",
                "city": "Lyon",
                "country_id": self.env.ref("base.fr").id,
                "siret": "77788899100018",
                "vat": "FR51777888991",
            }
        )
        self.env.ref("l10n_fr.l10n_fr_pcg_chart_template")._load(20.0, 20.0, company)
        self.env.ref("base.user_admin").company_ids = [Command.link(company.id)]
        return company

    def _prepare_data_for_factor(self, move_type="out_invoice"):
        self.ensure_one()
        move_form = Form(
            self.env["account.move"]
            .with_company(self.env.company)
            .with_context(
                default_move_type=move_type,
                account_predictive_bills_disable_prediction=True,
            )
        )
        move_form.invoice_date = fields.Date.from_string("2022-10-03")
        move_form.date = move_form.invoice_date
        move_form.partner_id = self.env.ref("base.res_partner_2")

    def ui_populate_data_for_factor(self):
        raise UserError(_("Not yet implemented"))
        # self._prepare_data_for_factor()

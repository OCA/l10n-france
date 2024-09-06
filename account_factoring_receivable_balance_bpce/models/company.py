# © 2022 David BEAL @ Akretion
# © 2022 Alexis DE LATTRE @ Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.tests import Form

logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    factor_config_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Facto Currency",
        help="Use to configure account and journal",
    )
    bpce_factor_code = fields.Char(size=6, help="N° de compte chez PBCE")
    bpce_start_date = fields.Date(
        string="Start Date",
        tracking=True,
        help="No account move will be selected before this date",
    )

    @api.model
    def _create_french_company(self, company_name=None):
        """
        Method to use with the cmd line (demo purpose)
        Can be called from Odoo Shell
        """
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
        logger.info("Company %s" % company.name)
        for currency in self.env["res.currency"].search([]):
            logger.info("Journal and account for factor to create")
            company._configure_bpce_factoring(currency=currency.name)
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

    def ui_configure_bpce_factoring_balance(self):
        self.ensure_one()
        if not self.factor_config_currency_id:
            raise UserError(_("You must select a currency to begin configuration"))
        self._configure_bpce_factoring(currency=self.factor_config_currency_id.name)
        bpce_journals = self.env["account.journal"].search(
            [("factor_type", "=", "bpce"), ("company_id", "=", self.id)]
        )
        action_id = self.env.ref("account.action_account_journal_form").id
        active_ids = ",".join([str(x) for x in bpce_journals.ids])

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Configuration réussie",
                "type": "success",  # warning/success
                "message": "Consulter les journaux et comptes configurés",
                "links": [
                    {
                        "label": "Voir les journaux",
                        "url": f"#action={action_id}&model=account.journal"
                        f"&active_ids={active_ids}",
                    }
                ],
                "sticky": True,  # True/False will display for few seconds if false
                "next": action_id,
            },
        }

    @api.model
    def _configure_bpce_factoring(self, currency):
        """Mainly copied from l10n_fr_account_vat_return
        The code is created here and not in the test,
        because it can be very useful for demos too

        This method can be called to configure actual company or a new one
        """
        self = self.sudo()
        self.ensure_one()
        currency = self.env.ref("base.%s" % currency.upper(), raise_if_not_found=False)
        if not currency:
            # pylint: disable=C8107
            raise UserError("La devise '%s' est inconnue" % currency.name)
        if self.env["account.journal"].search(
            [
                ("factor_type", "=", "bpce"),
                ("company_id", "=", self.id),
                ("currency_id", "=", currency.id),
            ]
        ):
            # pylint: disable=C8107
            raise UserError(
                "Un journal BPCE avec la devise '%s' existe déjà. Configuration annulée"
                % currency.name
            )
        fr_chart_template = self.env.ref("l10n_fr.l10n_fr_pcg_chart_template")
        company = self
        if self.chart_template_id != fr_chart_template:
            action = self.env.ref("account.action_account_config").read()[0]
            action["name"] = "Configure accounting chart in '%s' company" % self.name
            raise RedirectWarning(
                _(
                    "The accounting chart installed in this company "
                    "is not the french one. Install it first"
                ),
                action,
                _("Go to accounting chart configuration"),
                {"active_ids": [self.env.company.id]},
            )
        if self.env["account.journal"].search(
            [
                ("factor_type", "=", "bpce"),
                ("currency_id", "=", currency.id),
                ("company_id", "=", company.id),
            ]
        ):
            raise UserError(
                _(
                    "BPCE Journal with currency '%s' already exist. "
                    "Configuration aborted"
                )
                % currency.name
            )
        vals = {"reconcile": False, "tax_ids": False, "company_id": company.id}
        acc = {}
        revenue_type_id = self.env.ref("account.data_account_type_revenue").id
        for acco in (
            ["4115", "Factoring Receivable", revenue_type_id],
            ["4671", "Factoring Current", revenue_type_id],
            ["4672", "Factoring Holdback", revenue_type_id],
            ["4673", "Factoring Recharging", revenue_type_id],
        ):
            code = f"{acco[0]}{currency.symbol}"
            values = {"code": code, "name": acco[1], "user_type_id": acco[2]}
            values.update(vals)
            acc[code] = self.env["account.account"].create(values)
        expense_acc = self.env["account.account"].search(
            [("code", "=", "622500"), ("company_id", "=", company.id)]
        )
        self.env["account.journal"].create(
            {
                "name": "BPCE %s" % currency.symbol,
                "type": "general",
                "factor_type": "bpce",
                "code": "BPCE%s" % currency.symbol,
                "currency_id": currency.id,
                "company_id": company.id,
                "factoring_receivable_account_id": acc["4115%s" % currency.symbol].id,
                "factoring_current_account_id": acc["4671%s" % currency.symbol].id,
                "factoring_holdback_account_id": acc["4672%s" % currency.symbol].id,
                "factoring_pending_recharging_account_id": acc[
                    "4673%s" % currency.symbol
                ].id,
                "factoring_expense_account_id": expense_acc.id,
            }
        )
        return company

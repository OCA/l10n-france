# Copyright 2024 Moka (https://moka.cloud).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    tax_calculation_method = fields.Selection(
        [('margin', 'Margin'), ('normal', 'Normal')],
        string="Tax Calculation Method",
        help="Method used for calculating tax",
        default='normal',
    )

    amount_type = fields.Selection(
        selection_add=[('margin_percentage', 'Margin Percentage')],
        ondelete={'margin_percentage': 'cascade'},
    )

    vat_on_margin = fields.Boolean(
        string="VAT on Margin",
        help="Check this box if the tax is a VAT on margin.",
    )

    def _get_tax_vals(self, company, tax_template_to_tax):
        """Carry the margin flags over to the generated tax.

        The generic helper only copies the fields it knows about, so without
        this the taxes Odoo generates for a company would silently lose
        vat_on_margin and compute a regular VAT on the whole price.
        _get_tax_vals_complete() delegates here, so both generation paths are
        covered by this single override.
        """
        vals = super()._get_tax_vals(company, tax_template_to_tax)
        vals.update({
            'vat_on_margin': self.vat_on_margin,
            'tax_calculation_method': self.tax_calculation_method,
        })
        return vals

# Copyright 2017-2020 Akretion France (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    fr_chorus_invoice_format = fields.Selection(selection_add=[
        ('xml_cii', 'CII 16B XML'),
        ('pdf_factur-x', 'Factur-X PDF'),
        ])

    @api.constrains('fr_chorus_invoice_format', 'xml_format_in_pdf_invoice')
    def check_chorus_facturx_config(self):
        for company in self:
            if (
                    company.fr_chorus_invoice_format == 'pdf_factur-x' and
                    company.xml_format_in_pdf_invoice != 'factur-x'):
                raise ValidationError(_(
                    "For company %s, if you select Factur-X as Chorus "
                    "Invoice Format, then you should also select Factur-X as "
                    "Format in the section 'Electronic Invoices'.")
                    % company.display_name)

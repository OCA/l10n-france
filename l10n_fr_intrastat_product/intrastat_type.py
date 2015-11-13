# -*- coding: utf-8 -*-
##############################################################################
#
#    L10n FR intrastat product module for Odoo
#    Copyright (C) 2010-2015 Akretion (http://www.akretion.com/)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError

# If you modify the line below, please also update intrastat_type_view.xml
# (form view of report.intrastat.type, field transaction_code
fiscal_only_tuple = ('25', '26', '31')


class IntrastatTransaction(models.Model):
    _inherit = "intrastat.transaction"

    fr_object_type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Supplier Invoice'),
        ('out_refund', 'Customer Refund'),
        ('none', 'None'),
        ], string='Possible on', select=True, required=True)
    # procedure_code = fields.Selection([ => code
    fr_transaction_code = fields.Selection([
        ('', '-'),
        ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'),
        ('19', '19'),
        ('21', '21'), ('22', '22'), ('23', '23'), ('29', '29'),
        ('30', '30'),
        ('41', '41'), ('42', '42'),
        ('51', '51'), ('52', '52'),
        ('70', '70'),
        ('80', '80'),
        ('91', '91'), ('99', '99'),
        ], string='Transaction code',
        help="For the 'DEB' declaration to France's customs "
        "administration, you should enter the number 'nature de la "
        "transaction' here.")
    fr_is_fiscal_only = fields.Boolean(
        string='Is fiscal only ?',
        help="Only fiscal data should be provided for this procedure code.")
    fr_fiscal_value_multiplier = fields.Integer(
        string='Fiscal value multiplier',
        help="'0' for procedure codes 19 and 29, "
        "'-1' for procedure code 25, '1' for all the others. "
        "This multiplier is used to compute the total fiscal value of "
        "the declaration.")
    fr_is_vat_required = fields.Boolean(
        string='Is partner VAT required?',
        help="True for all procedure codes except 11, 19 and 29. "
        "When False, the VAT number should not be filled in the "
        "Intrastat product line.")
    fr_intrastat_product_type = fields.Char(
        # TODO : see with Luc if we can move it to intrastat_product
        string='Intrastat product type',
        help="Decides on which kind of Intrastat product report "
        "('Import' or 'Export') this Intrastat type can be selected.")

    _sql_constraints = [(
        'code_invoice_type_uniq',
        'unique(code, fr_transaction_code, company_id)',
        'An Intrastat Transaction already exists for this company with the '
        'same code and the same procedure code.'
        )]

    @api.one
    @api.constrains('code', 'fr_transaction_code')
    def _code_check(self):
        if self.company_id.country_id and self.company_id.country_id == 'FR':
            if self.fr_object_type == 'out' and self.fr_procedure_code != '29':
                raise ValidationError(
                    _("Procedure code must be '29' for an Outgoing products."))
            elif (
                    self.fr_object_type == 'in' and
                    self.fr_procedure_code != '19'):
                raise ValidationError(
                    _("Procedure code must be '19' for an Incoming products."))
            if (
                    self.fr_procedure_code not in fiscal_only_tuple and
                    not self.fr_transaction_code):
                raise ValidationError(
                    _('You must enter a value for the transaction code.'))
            if (
                    self.fr_procedure_code in fiscal_only_tuple and
                    self.fr_transaction_code):
                raise ValidationError(_(
                    "You should not set a transaction code when the "
                    "Code (i.e. Procedure Code) is '25', '26' or '31'."))

    @api.onchange('code')
    def procedure_code_on_change(self):
        if self.code in fiscal_only_tuple:
            self.fr_transaction_code = False

    @api.one
    @api.depends('code', 'description', 'fr_transaction_code')
    def _compute_display_name(self):
        display_name = self.code
        if self.fr_transaction_code:
            display_name += '/%s' % self.fr_transaction_code
        if self.description:
            display_name += ' ' + self.description
        self.display_name = len(display_name) > 55 \
            and display_name[:55] + '...' \
            or display_name

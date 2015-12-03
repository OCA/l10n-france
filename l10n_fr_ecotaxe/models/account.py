# -*- coding: utf-8 -*-
###############################################################################
#
#   Module for OpenERP
#   Copyright (C) 2015 Akretion (http://www.akretion.com).
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

__author__ = 'mourad.elhadj.mimoune'

from openerp import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    is_ecotaxe = fields.Boolean('Ecotaxe',
                                help="Warning : To include Ecotaxe "
                                "in the VAT tax check this :\n"
                                "1: check  \"included in base amount \"\n"
                                "2: The Ecotaxe sequence must be less then "
                                "VAT tax (in sale and purchase)")

    @api.onchange('is_ecotaxe')
    def onchange_is_ecotaxe(self):
        import pdb; pdb.set_trace()
        if self.is_ecotaxe:
            self.type = 'code'
            self.include_base_amount = True
            self.python_compute = """
# price_unit
# product: product.product object or None
# partner: res.partner object or None
result = product.computed_ecotaxe or 0.0
            """
            self.python_compute_inv = self.python_compute


class AccountEcotaxeClassification(models.Model):
    _name = 'account.ecotaxe.classification'

    # Default Section
    def _default_company_id(self):
        return self.env['res.users']._get_company()

    name = fields.Char('Name')
    code = fields.Char('Code')
    ecotaxe_type = fields.Selection(
        [
            ('fixed', u'Fixed'),
            ('weight_based', 'Weight based'),
        ],
        string='Ecotaxe Type',
        help="If ecotaxe is weight based,"
        "the ecotaxe coef must take into account\n"
        "the weight unit of measure (kg by default)"
        )
    ecotaxe_coef = fields.Float('Ecotaxe Coef')
    fixed_ecotaxe = fields.Float(
        'Fixed Ecotaxe',
        help="fixed ecotaxe amount.\n"
        )
    sale_ecotaxe_id = fields.Many2one(
        'account.tax',
        string="Sale EcoTaxe",
        domain=[
            ('is_ecotaxe', '=', True),
            ('parent_id', '=', False),
            ('type_tax_use', 'in', ['sale', 'all'])])
    purchase_ecotaxe_id = fields.Many2one(
        'account.tax',
        string="Purchase EcoTaxe",
        domain=[
            ('is_ecotaxe', '=', True),
            ('parent_id', '=', False),
            ('type_tax_use', 'in', ['purchase', 'all'])])
    active = fields.Boolean(default=True,)

    company_id = fields.Many2one(
        comodel_name='res.company', default=_default_company_id,
        string='Company', help="Specify a company"
        " if you want to define this Ecotaxe Classification only for specific"
        " company. Otherwise, this Fiscal Classification will be available"
        " for all companies.")

    @api.onchange('ecotaxe_type')
    def onchange_ecotaxe_type(self):
        if self.ecotaxe_type == 'weight_based':
            self.fixed_ecotaxe = 0
        if self.ecotaxe_type == 'fixed':
            self.ecotaxe_coef = 0


class account_invoice_tax(models.Model):
    _inherit = "account.invoice.tax"

    @api.depends('tax_code_id', 'base_code_id', 'account_id', 'invoice_id')
    def _compute_generic_base(self):
        for tax_line in self:
            generic_base = 0.0
            for line in tax_line.invoice_id.invoice_line:
                ecotaxe_ids = [tax.id for tax in line.invoice_line_tax_id
                          if tax.is_ecotaxe]
                for ecotaxe_id in self.env['account.tax'].browse(ecotaxe_ids):
                    tax_acc_id = ecotaxe_id.account_paid_id
                    if tax_line.invoice_id.type in ('out_invoice','in_invoice'):
                        tax_acc_id = ecotaxe_id.account_collected_id
                    if ecotaxe_id.tax_code_id == tax_line.tax_code_id and \
                            ecotaxe_id.base_code_id == tax_line.base_code_id  and \
                            (not tax_acc_id or tax_acc_id == tax_line.account_id):
                        if line.product_id:
                            for ecotaxe_classif_id in line.product_id.ecotaxe_classification_ids : 
                                related_tax_id = ecotaxe_classif_id.purchase_ecotaxe_id
                                if tax_line.invoice_id.type in ('out_invoice','in_invoice'):
                                    related_tax_id = ecotaxe_classif_id.sale_ecotaxe_id                                

                                if ecotaxe_classif_id.ecotaxe_type == 'fixed' and \
                                        ecotaxe_id == related_tax_id:
                                    generic_base += line.quantity
                                elif ecotaxe_classif_id.ecotaxe_type == 'weight_based' and \
                                        ecotaxe_id == related_tax_id:
                                     generic_base += line.product_id.weight_net * line.quantity

            tax_line.generic_base = generic_base or tax_line.base
            
    generic_base = fields.Float(string='Generic base',
        compute='_compute_generic_base',
        help="Generic base is used to get different base "
        "depending on ecotaxe type. For fixed taxe generic base "
        "is the qty sum of all product liable to this taxe. "
        "For wight base ecotaxe the geneic base is the weight sum of "
        "all product liable to this taxe", store=True)
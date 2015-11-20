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
    purchase_ecotaxe_id = fields.Many2many(
        'account.tax',
        string="Purchase EcoTaxe",
        domain=[
            ('is_ecotaxe', '=', True),
            ('parent_id', '=', False),
            ('type_tax_use', 'in', ['purchase', 'all'])])
    active = fields.Boolean()
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

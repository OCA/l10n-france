# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
#    Copyright (C) 2015-TODAY Akretion <http://www.akretion.com>.
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

from openerp import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ecotaxe_classification_ids = fields.Many2many(
        'account.ecotaxe.classification',
        'product_template_rel_ecotaxe_classif',
        string='Ecotaxe Classification',)

    @api.onchange('ecotaxe_classification_ids')
    def onchange_ecotaxe_classification_ids(self):
        if self.ecotaxe_classification_ids:
            sale_taxes = self.taxes_id.ids or []
            purchase_taxes = self.supplier_taxes_id.ids or []
            for ecotaxe_classif_id in self.ecotaxe_classification_ids:
                sale_taxes +=\
                    ecotaxe_classif_id.sale_ecotaxe_id.ids
                purchase_taxes +=\
                    ecotaxe_classif_id.purchase_ecotaxe_id.ids
            self.taxes_id = [(6, 0, sale_taxes)]
            self.supplier_taxes_id = [(6, 0, purchase_taxes)]


class ProductProduct(models.Model):
    _inherit = 'product.product'

    fixed_ecotaxe = fields.Float('Fixed Ecotaxe', compute='_compute_ecotaxe',
                                 help="Fixed ecotaxe of the "
                                 "Ecotaxe Classification\n")
    computed_ecotaxe = fields.Float('Coputed Ecotaxe',
                                    compute='_compute_ecotaxe',
                                    help="Ecotaxe value :\n"
                                    "product weight * ecotaxe coef of "
                                    "Ecotaxe Classification\n")

    @api.depends('ecotaxe_classification_ids',
                 'ecotaxe_classification_ids.ecotaxe_type',
                 'ecotaxe_classification_ids.ecotaxe_coef',
                 'ecotaxe_classification_ids.fixed_ecotaxe', 'weight')
    def _compute_ecotaxe(self):
        for prod in self:
            prod.computed_ecotaxe = 0.0
            prod.fixed_ecotaxe = 0.0
            for ecotaxe_classif_id in prod.ecotaxe_classification_ids:
                if ecotaxe_classif_id.ecotaxe_type ==\
                        'weight_based':
                    weight = prod.weight_net or 0.0
                    prod.computed_ecotaxe +=\
                        ecotaxe_classif_id.ecotaxe_coef * weight
                else:
                    prod.fixed_ecotaxe += ecotaxe_classif_id.fixed_ecotaxe

    # Somme product has a taxe different of template
    @api.onchange('ecotaxe_classification_ids')
    def onchange_ecotaxe_classification_ids(self):
        if self.ecotaxe_classification_ids:
            sale_taxes = self.taxes_id.ids or []
            purchase_taxes = self.supplier_taxes_id.ids or []
            for ecotaxe_classif_id in self.ecotaxe_classification_ids:
                sale_taxes +=\
                    ecotaxe_classif_id.sale_ecotaxe_id.ids
                purchase_taxes +=\
                    ecotaxe_classif_id.purchase_ecotaxe_id.ids
            self.taxes_id = [(6, 0, sale_taxes)]
            self.supplier_taxes_id = [(6, 0, purchase_taxes)]


class ProductCategory(models.Model):
    _inherit = 'product.category'
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
    default_fixed_ecotaxe = fields.Float(
        'Fixed Ecotaxe',
        help="Default value of fixed ecotaxe.\n"
        "This value is set when you choise the category \n"
        "on creating a new product (triged by on change product category)\n"
        "Set this field to 0 if you want not default value")

    @api.onchange('ecotaxe_type')
    def onchange_ecotaxe_type(self):
        if self.ecotaxe_type == 'weight_based':
            self.default_fixed_ecotaxe = 0
        if self.ecotaxe_type == 'fixed':
            self.ecotaxe_coef = 0

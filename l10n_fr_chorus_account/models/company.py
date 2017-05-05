# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from openerp import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    fr_vat_scheme = fields.Selection(related='partner_id.fr_vat_scheme')

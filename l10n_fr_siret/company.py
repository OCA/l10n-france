# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2011 Numérigraphe SARL.
#    Copyright (C) 2014 Akretion (http://www.akretion.com)
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

from openerp import models, fields


class ResCompany(models.Model):
    """Replace the company's fields for SIRET/RC with the partner's"""
    _inherit = 'res.company'

    # siret field is defined in l10n_fr module
    siret = fields.Char(
        string='SIRET', related='partner_id.siret', store=True)
    siren = fields.Char(
        string='SIREN', related='partner_id.siren', store=True)
    nic = fields.Char(
        string='NIC', related='partner_id.nic', store=True)
    # company_registry field is definied in base module
    company_registry = fields.Char(
        string='Company Registry', related='partner_id.company_registry',
        store=True)

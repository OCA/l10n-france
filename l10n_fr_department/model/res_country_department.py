# -*- coding: utf-8 -*-
##############################################################################
#
#    l10n FR Departments module for Odoo
#    Copyright (C) 2013-2014 GRAP (http://www.grap.coop)
#    Copyright (C) 2015 Akretion (http://www.akretion.com)
#    @author Sylvain LE GAL (https://twitter.com/legalsylvain)
#    @author Alexis de Lattre (alexis.delattre@akretion.com)
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

from openerp import models, fields, _


class ResCountryDepartment(models.Model):
    _description = "Department"
    _name = 'res.country.department'
    _order = 'country_id, code'

    state_id = fields.Many2one(
        'res.country.state', string='State', required=True,
        help='State related to the current department')
    country_id = fields.Many2one(
        'res.country', related='state_id.country_id',
        string='Country', readonly=True,
        store=True, help='Country of the related state')
    name = fields.Char(
        string='Department Name', size=128, required=True)
    code = fields.Char(
        string='Departement Code', size=3, required=True,
        help="""The department code."""
        """(ISO 3166-2 Codification)""")

    _sql_constraints = [
        ('code_uniq', 'unique (code)',
            _("""You cannot have two departments with the same code!""")),
    ]

# © 2013-2016 GRAP (http://www.grap.coop)
# © 2015-2016 Akretion (http://www.akretion.com)
# @author Sylvain LE GAL (https://twitter.com/legalsylvain)
# @author Alexis de Lattre (alexis.delattre@akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    department_ids = fields.One2many(
        'res.country.department', 'state_id', string='Departments',
        help='Departments related to this state')

# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat product module for OpenERP
#    Copyright (C) 2010-2011 Akretion (http://www.akretion.com). All Rights Reserved
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

from osv import osv, fields
from tools.translate import _

class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _columns = {
        'intrastat_transport' : fields.selection([(1, 'Transport maritime'), \
            (2, 'Transport par chemin de fer'), \
            (3, 'Transport par route'), \
            (4, 'Transport par air'), \
            (5, 'Envois postaux'), \
            (7, 'Installations de transport fixes'), \
            (8, 'Transport par navigation intérieure'), \
            (9, 'Propulsion propre')], 'Type of transport', \
            help="Select the type of transport. This information is required for the product intrastat report (DEB).")
            }

# Do we put a default value, taken from res_company ?

    def action_invoice_create(self, cr, uid, ids, journal_id=False,
        group=False, type='out_invoice', context=None):
        '''Copy transport from picking to invoice'''

        res = super(stock_picking, self).action_invoice_create(cr, uid, ids,
            journal_id=journal_id, group=group, type=type, context=context)
        invoice_obj = self.pool.get('account.invoice')
        for picking_id in res:
            picking = self.read(cr, uid, picking_id, ['intrastat_transport'], context=context)
            if picking['intrastat_transport']:
                invoice_obj.write(cr, uid, res[picking_id], {
                    'intrastat_transport': picking['intrastat_transport'],
                 }, context=context)
        return res

stock_picking()


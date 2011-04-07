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


class stock_warehouse(osv.osv):
    _inherit = "stock.warehouse"
    _columns = {
        'intrastat_department' : fields.char('Department', size=2, help="France's department where the warehouse is located. This parameter is required for the DEB (Déclaration d'Echange de Biens)."),
            }

    def _check_intrastat_department(self, cr, uid, ids):
        dpt_list = []
        for dpt_to_check in self.read(cr, uid, ids, ['intrastat_department']):
            dpt_list.append(dpt_to_check['intrastat_department'])
        return self.pool.get('res.company').real_department_check(dpt_list)

    _constraints = [
        (_check_intrastat_department, "Error msg is in raise", ['intrastat_department']),
    ]

stock_warehouse()


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
            picking = self.browse(cr, uid, picking_id, context=context)
            if picking.intrastat_transport:
                invoice_obj.write(cr, uid, res[picking_id], {
                    'intrastat_transport': picking.intrastat_transport,
                 }, context=context)

            location_to_search = False
            if picking.move_lines:
                if picking.type == 'out':
                    location_to_search = picking.move_lines[0].location_id
                if picking.type == 'in':
                    location_to_search = picking.move_lines[0].location_dest_id
            warehouse_obj = self.pool.get('stock.warehouse')
            warehouse_all_ids = warehouse_obj.search(cr, uid, [], context=context)
            dpt_to_copy = False
            for warehouse in warehouse_obj.browse(cr, uid, warehouse_all_ids, context=context):
                if (picking.type == 'out' and location_to_search == warehouse.lot_stock_id) or (picking.type == 'in' and location_to_search == warehouse.lot_input_id):
                    dpt_to_copy = warehouse.intrastat_department
                    break
            if dpt_to_copy:
                invoice_obj.write(cr, uid, res[picking_id], {
                    'intrastat_department': dpt_to_copy,
                }, context=context)

        return res

stock_picking()


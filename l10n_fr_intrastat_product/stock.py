# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat product module for OpenERP
#    Copyright (C) 2010-2013 Akretion (http://www.akretion.com)
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

from openerp.osv import osv, fields

class stock_location(osv.Model):
    _inherit = "stock.location"
    _columns = {
        'intrastat_department' : fields.char('Department', size=2, help="France's department where the stock location is located. This parameter is required for the DEB (Déclaration d'Echange de Biens)."),
    }


    def _check_intrastat_department(self, cr, uid, ids):
        dpt_list = []
        for dpt_to_check in self.read(cr, uid, ids, ['intrastat_department']):
            dpt_list.append(dpt_to_check['intrastat_department'])
        return self.pool.get('res.company').real_department_check(dpt_list)

    _constraints = [
        (_check_intrastat_department, "Error msg is in raise", ['intrastat_department']),
    ]

stock_location()


class stock_picking(osv.Model):
    _inherit = "stock.picking"

    def _compute_department(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for picking in self.browse(cr, uid, ids, context=context):
            result[picking.id] = False
            start_point = False
            if picking.move_lines:
                if picking.type == 'out' and picking.move_lines[0].location_dest_id.usage == 'customer':
                    start_point = picking.move_lines[0].location_id
                elif picking.type == 'in' and picking.move_lines[0].location_dest_id.usage == 'internal':
                    start_point = location_to_search = picking.move_lines[0].location_dest_id
                while start_point:
                    if start_point.intrastat_department:
                        result[picking.id] = start_point.intrastat_department
                        break
                    elif start_point.location_id:
                        start_point = start_point.location_id
                        continue
                    else:
                        break
        #print "_compute_department result=", result
        return result

    def _get_picking_from_move_lines(self, cr, uid, ids, context=None):
        #print "invalid function dpt ids=", ids
        return self.pool.get('stock.picking').search(cr, uid, [('move_lines', 'in', ids)], context=context)

    _columns = {
        'intrastat_transport' : fields.selection([
            (1, 'Transport maritime'),
            (2, 'Transport par chemin de fer'),
            (3, 'Transport par route'),
            (4, 'Transport par air'),
            (5, 'Envois postaux'),
            (7, 'Installations de transport fixes'),
            (8, 'Transport par navigation intérieure'),
            (9, 'Propulsion propre')], 'Type of transport',
            help="Select the type of transport of the goods. This information is required for the product intrastat report (DEB)."),
        'intrastat_department': fields.function(_compute_department, method=True, type='char', size=2, string='Intrastat department', store={
            'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['type'], 10),
            'stock.move': (_get_picking_from_move_lines, ['location_dest_id', 'location_id', 'picking_id'], 20),
            }, help='Compute the source departement for an Outgoing product, or the destination department for an Incoming product.'),
            }


    def _prepare_invoice(self, cr, uid, picking, partner, inv_type, journal_id, context=None):
        '''Copy transport from picking to invoice'''

        invoice_vals = super(stock_picking, self)._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id, context=context)
        invoice_vals.update({
            'intrastat_transport': picking.intrastat_transport,
            'intrastat_department': picking.intrastat_department,
        })
        if picking.address_id and picking.address_id.country_id:
            invoice_vals['intrastat_country_id'] = picking.address_id.country_id.id
        return invoice_vals

stock_picking()


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

class sale_order(osv.osv):
    _inherit = "sale.order"

    def action_invoice_create(self, cr, uid, ids, grouped=False, states=['confirmed','done','exception']):
        '''Copy destination country and departure department on invoice'''
        print "action_invoice_create ids=", ids
        res = super(sale_order,self).action_invoice_create(cr, uid, ids, grouped, states)
        for sale in self.browse(cr, uid, ids):
            for rel_invoice in sale.invoice_ids:
                dico_write = {}
                if sale.partner_shipping_id and sale.partner_shipping_id.country_id:
                    dico_write['intrastat_country_id'] = sale.partner_shipping_id.country_id.id
                if sale.picking_ids:
                    dico_write['intrastat_department'] = sale.picking_ids[0].intrastat_department
                self.pool.get('account.invoice').write(cr, uid, rel_invoice.id, dico_write)
        return res

sale_order()


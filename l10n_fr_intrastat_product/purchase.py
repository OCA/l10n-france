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

class purchase_order(osv.osv):
    _inherit = "purchase.order"

    def action_invoice_create(self, cr, uid, ids, *args):
        '''Copy country of partner_address_id =("origin country") and arrival department on invoice'''
        print "action_invoice_create ids=", ids
        res = super(purchase_order,self).action_invoice_create(cr, uid, ids, *args)
        for purchase in self.browse(cr, uid, ids):
            dico_write = {}
            if purchase.partner_address_id and purchase.partner_address_id.country_id:
                dico_write['intrastat_country_id'] = purchase.partner_address_id.country_id.id
            if purchase.picking_ids:
                dico_write['intrastat_department'] = purchase.picking_ids[0].intrastat_department
            self.pool.get('account.invoice').write(cr, uid, purchase.invoice_id.id, dico_write)
            print "write all !"
        return res

purchase_order()


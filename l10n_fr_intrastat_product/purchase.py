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

from openerp.osv import orm


class purchase_order(orm.Model):
    _inherit = "purchase.order"

    def action_invoice_create(self, cr, uid, ids, context=None):
        '''Copy country of partner_id =("origin country") and arrival department on invoice'''
        res = super(purchase_order, self).action_invoice_create(cr, uid, ids, context=context)
        for purchase in self.browse(cr, uid, ids, context=context):
            for rel_invoice in purchase.invoice_ids:
                dico_write = {}
                if purchase.partner_id and purchase.partner_id.country_id:
                    dico_write['intrastat_country_id'] = purchase.partner_id.country_id.id
                if purchase.picking_ids:
                    dico_write['intrastat_department'] = purchase.picking_ids[0].intrastat_department
                self.pool.get('account.invoice').write(cr, uid, rel_invoice.id, dico_write, context=context)
        return res

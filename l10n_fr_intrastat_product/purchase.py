# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat product module for OpenERP
#    Copyright (C) 2010-2014 Akretion (http://www.akretion.com)
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

    def _prepare_invoice(self, cr, uid, order, line_ids, context=None):
        '''Copy country of partner_id =("origin country") and '''
        '''arrival department on invoice'''
        invoice_vals = super(purchase_order, self)._prepare_invoice(
            cr, uid, order, line_ids, context=context)
        if order.partner_id.country_id:
            invoice_vals['intrastat_country_id'] = \
                order.partner_id.country_id.id
        if order.picking_ids:
            invoice_vals['intrastat_department'] = \
                order.picking_ids[0].intrastat_department
        return invoice_vals

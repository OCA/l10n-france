# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat base module for OpenERP
#    Copyright (C) 2010-2011 Akretion (http://www.akretion.com/) All Rights Reserved
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


class report_intrastat_type(osv.osv):
    _name = "report.intrastat.type"
    _description = "Intrastat type"
    _order = "name"
    _columns = {
        'name': fields.char('Name',size=64,help="Name which appear when you select the Intrastat type on the invoice."),
        'active' : fields.boolean('Active', help="The active field allows you to hide the Intrastat type without deleting it."),
        'invoice_type' : fields.selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Supplier Invoice'),
            ('out_refund','Customer Refund'),
            ('in_refund','Supplier Refund'),
        ], 'Invoice type', select=True),
        'procedure_code': fields.integer('Procedure code', required=True, help="For the 'DEB' declaration to France's customs administration, you should enter the 'code régime' here."),
        'transaction_code': fields.integer('Transaction code', required=True, help="For the 'DEB' declaration to France's customs administration, you should enter the number 'nature de la transaction' here."),
    }

    _defaults = {
        'active': lambda *a: 1,
    }

    _sql_constraints = [
        ('invoice_type_uniq', 'unique(invoice_type)', 'You can only create one intrastat type per invoice type !'),
    ]

    def _code_check(self, cr, uid, ids):
    # Procedure_code and transaction codes are an integers, so they always have a value
        for intrastat_type in self.read(cr, uid, ids, ['procedure_code', 'transaction_code']):
            if not 10 <= intrastat_type['procedure_code'] <= 99:
                raise osv.except_osv(_('Error :'), _('Procedure code must be between 10 and 99'))
            if not 10 <= intrastat_type['transaction_code'] <= 99:
                raise osv.except_osv(_('Error :'), _('Transaction code must be between 10 and 99'))
        return True

    _constraints = [
        (_code_check, "Error msg in raise", ['procedure_code', 'transaction_code']),
    ]

report_intrastat_type()


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
from tools.translate import _

class report_intrastat_type(osv.osv):
    _name = "report.intrastat.type"
    _description = "Intrastat type"
    _order = "procedure_code, transaction_code"
    _columns = {
        'name': fields.char('Name', size=64, help="Description of the Intrastat type."),
        'active' : fields.boolean('Active', help="The active field allows you to hide the Intrastat type without deleting it."),
        'invoice_type' : fields.selection([
            ('out_invoice', 'Customer Invoice'),
            ('in_invoice', 'Supplier Invoice'),
            ('out_refund', 'Customer Refund'),
            ('none', 'None'),
        ], 'Invoice type', select=True),
        'procedure_code': fields.char('Procedure code', required=True, size=2, help="For the 'DEB' declaration to France's customs administration, you should enter the 'code régime' here."),
        'transaction_code': fields.char('Transaction code', size=2, help="For the 'DEB' declaration to France's customs administration, you should enter the number 'nature de la transaction' here."),
        'is_fiscal_only': fields.boolean('Is fiscal only ?', help="Only fiscal data should be provided for this procedure code."),
    }

    _defaults = {
        'active': lambda *a: 1,
    }

    _sql_constraints = [
        ('code_invoice_type_uniq', 'unique(procedure_code, transaction_code)', 'The pair (procedure code, transaction code) must be unique.'),
    ]

    def real_code_check(self, codes):
        if not codes['procedure_code']:
            raise osv.except_osv(_('Error :'), _('You must enter a value for the procedure code.'))
        if not codes['procedure_code'].isdigit():
            raise osv.except_osv(_('Error :'), _('Procedure code must be a number.'))
        if len(codes['procedure_code']) != 2:
            raise osv.except_osv(_('Error :'), _('Procedure code must have 2 digits.'))
        if codes['transaction_code']:
            if not codes['transaction_code'].isdigit():
                raise osv.except_osv(_('Error :'), _('Transaction code must be a number.'))
            if len(codes['transaction_code']) != 2:
                raise osv.except_osv(_('Error :'), _('Transaction code must have 2 digits.'))
        return True


    def _code_check(self, cr, uid, ids):
        for intrastat_type in self.read(cr, uid, ids, ['procedure_code', 'transaction_code', 'is_fiscal_only']):
            self.real_code_check(intrastat_type)
        return True

    _constraints = [
        (_code_check, "Error msg in raise", ['procedure_code', 'transaction_code']),
    ]

    def is_fiscal_only_on_change(self, cr, uid, ids, is_fiscal_only=False):
        result = {}
        result['value'] = {}
        if is_fiscal_only:
            result['value'].update({'transaction_code': False})
        return result

report_intrastat_type()


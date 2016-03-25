# -*- encoding: utf-8 -*-
##############################################################################
#
#    l10n FR HR Expense Private Car module for OpenERP
#    Copyright (C) 2014 Akretion (http://www.akretion.com)
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

from openerp.osv import orm, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime


# I had to choose between several ideas when I developped this module :
# 1) constraint on product_id in expense line
# Idea : we put a constraint on the field product_id of the expense line
# and, if it's a private_car_expense_ok=True product but it's not the private
# car expense product of the employee, we block
# Drawback : not convenient for the employee because he has to select the
# right private car expense product by himself

# 2) single product, dedicated object for prices
# Idea : we create only one "private car expense" product, and we
# create a new object to store the price depending on the CV, etc...
# Drawback : need to create a new object

# 3) single generic "My private car" product selectable by the user ;
# several specific private car products NOT selectable by the user
# Idea : When the user selects the generic "My private car" product,
# it is automatically replaced by the specific one via the on_change
# Drawback : none ? :)
# => that's what is implemented in this module


class product_template(orm.Model):
    _inherit = 'product.template'

    _columns = {
        'private_car_expense_ok': fields.boolean('Private Car Expense'),
        }


class product_product(orm.Model):
    _inherit = 'product.product'

    def _check_private_car_expense(self, cr, uid, ids):
        for product in self.browse(cr, uid, ids):
            if product.private_car_expense_ok:
                if product.hr_expense_ok:
                    raise orm.except_orm(
                        _('Error:'),
                        _("The product '%s' cannot have both the properties "
                            "'Can be Expensed' and 'Private Car Expense'.")
                        % product.name)
                uom_model, km_uom_id = \
                    self.pool['ir.model.data'].get_object_reference(
                        cr, uid, 'product', 'product_uom_km')
                assert uom_model == 'product.uom', 'Wrong model'
                if product.uom_id.id != km_uom_id:
                    raise orm.except_orm(
                        _('Error:'),
                        _("The product '%s' is a Private Car Expense, so "
                            "it's unit of measure must be kilometers (KM).")
                        % product.name)
                if not product.standard_price:
                    raise orm.except_orm(
                        _('Error:'),
                        _("The product '%s' is a Private Car Expense, so it "
                            "must have a Cost Price.")
                        % product.name)
        return True

    _constraints = [(
        _check_private_car_expense,
        "Error msg in raise",
        [
            'private_car_expense_ok',
            'hr_expense_ok',
            'uom_id',
            'standard_price',
        ])]

    def onchange_private_car_expense_ok(
            self, cr, uid, ids, private_car_expense_ok, context=None):
        res = {'value': {}}
        if private_car_expense_ok:
            uom_model, km_uom_id = \
                self.pool['ir.model.data'].get_object_reference(
                    cr, uid, 'product', 'product_uom_km')
            assert uom_model == 'product.uom', 'Wrong model'
            res['value'] = {
                'type': 'service',
                'list_price': 0.0,
                'hr_expense_ok': False,
                'sale_ok': False,
                'purchase_ok': False,
                'uom_id': km_uom_id,
                'po_uom_id': km_uom_id,
                'taxes_id': False,
                'supplier_taxes_id': False,
                }
        return res


class hr_employee(orm.Model):
    _inherit = 'hr.employee'

    def _compute_private_car(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for employee_id in ids:
            res[employee_id] = 0.0
        private_car_pp_ids = self.pool['product.product'].search(
            cr, uid, [('private_car_expense_ok', '=', True)], context=context)
        today = fields.date.context_today(self, cr, uid, context=context)
        today_dt = datetime.strptime(today, DEFAULT_SERVER_DATE_FORMAT)
        cr.execute("""
            SELECT ee.employee_id, sum(el.unit_quantity)
            FROM hr_expense_line el
            LEFT JOIN hr_expense_expense ee ON ee.id=el.expense_id
            WHERE state IN ('done', 'paid', 'accepted')
            AND ee.employee_id IN %s
            AND el.product_id IN %s
            AND EXTRACT(year FROM ee.date) = %s
            GROUP BY ee.employee_id
            """, (tuple(ids), tuple(private_car_pp_ids), today_dt.year))
        for line in cr.dictfetchall():
            res[line['employee_id']] = line['sum']
        return res

    _columns = {
        'private_car_plate': fields.char(
            'Private Car Plate', size=32,
            help="This field will be copied on the expenses of this employee."
            ),
        'private_car_product_id': fields.many2one(
            'product.product', 'Private Car Product',
            domain=[('private_car_expense_ok', '=', True)],
            help="This field will be copied on the expenses of this employee."
            ),
        'private_car_total_km_this_year': fields.function(
            _compute_private_car, type='float',
            string="Total KM with Private Car This Year", readonly=True,
            help="Number of kilometers (KM) with private car for this "
            "employee in expenses in Approved, Waiting Payment or Paid "
            "state in the current civil year. This is usefull to check or "
            "estimate if the Private Card Product selected for this "
            "employee is compatible with the number of kilometers "
            "reimbursed to this employee during the civil year."),
        }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({
            'private_car_plate': False,
            'private_car_product_id': False,
            })
        return super(hr_employee, self).copy(
            cr, uid, id, default=default, context=context)


class hr_expense_expense(orm.Model):
    _inherit = 'hr.expense.expense'

    _columns = {
        'private_car_plate': fields.char(
            'Private Car Plate', size=32, readonly=True,
            states={'draft': [('readonly', False)]}),
        'private_car_product_id': fields.many2one(
            'product.product', 'Private Car Product',
            domain=[('private_car_expense_ok', '=', True)]),
        }

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = super(hr_expense_expense, self).onchange_employee_id(
            cr, uid, ids, employee_id, context=context)
        private_car_plate = False
        private_car_product_id = False
        if employee_id:
            employee = self.pool['hr.employee'].browse(
                cr, uid, employee_id, context=context)
            private_car_plate = employee.private_car_plate
            private_car_product_id = \
                employee.private_car_product_id.id or False
        res['value']['private_car_plate'] = private_car_plate
        res['value']['private_car_product_id'] = private_car_product_id
        return res

    def onchange_private_car_product_id(
            self, cr, uid, ids, private_car_product_id, employee_id,
            context=None):
        res = {'warning': {}, 'value': {}}
        if employee_id:
            employee = self.pool['hr.employee'].browse(
                cr, uid, employee_id, context=context)
            ori_private_car_product_id = \
                employee.private_car_product_id.id or False
            if employee.private_car_product_id.id != private_car_product_id:
                if self.pool['res.users'].has_group(
                        cr, uid, 'account.group_account_manager'):
                    res['warning'] = {
                        'title': _('Warning - Private Car Product'),
                        'message': _(
                            "You should not change the Private "
                            "Car Product on expenses. You should change the "
                            "Private Car Product on the Employee form and "
                            "then select again the Employee on the "
                            "expense.\n\nBut, as you are in the group "
                            "'Account Manager', we suppose that you know "
                            "what you are doing, so the original product "
                            "was not restored.")}
                else:
                    res['warning'] = {
                        'title': _('Warning - Private Car Product'),
                        'message': _(
                            "You should not change the Private "
                            "Car Product on expenses. You should change the "
                            "Private Car Product on the Employee form and "
                            "then select again the Employee on the expense. "
                            "The original Private Car Product has been "
                            "restored.\n\nOnly users in the 'Account Manager' "
                            "group are allowed to change the Private Car "
                            "Product on expenses manually.")}
                    res['value']['private_car_product_id'] = \
                        ori_private_car_product_id
        return res


class hr_expense_line(orm.Model):
    _inherit = 'hr.expense.line'

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        if context is None:
            context = {}
        if product_id:
            product_model, generic_private_car_product_id =\
                self.pool['ir.model.data'].get_object_reference(
                    cr, uid, 'l10n_fr_hr_expense_private_car',
                    'generic_private_car_expense')
            assert product_model == 'product.product', 'Wrong model'
            if product_id == generic_private_car_product_id:
                private_car_product_id = context.get('private_car_product_id')
                if not private_car_product_id:
                    raise orm.except_orm(
                        _('Error:'),
                        _("Missing 'Private Car Product' on the current "
                            "expense."))
                product_id = private_car_product_id
        res = super(hr_expense_line, self).onchange_product_id(
            cr, uid, ids, product_id, context=context)
        res['value']['product_id'] = product_id
        return res

    def onchange_unit_amount(
            self, cr, uid, ids, unit_amount, unit_quantity,
            product_id, employee_id, context=None):
        res = super(hr_expense_line, self).onchange_unit_amount(
            cr, uid, ids, unit_amount, unit_quantity,
            product_id, employee_id, context=context)
        if product_id:
            product = self.pool['product.product'].browse(
                cr, uid, product_id, context=context)
            if product.private_car_expense_ok:
                original_unit_amount = product.price_get(
                    'standard_price')[product.id]
                if int(original_unit_amount * 1000) != int(unit_amount * 1000):
                    if self.pool['res.users'].has_group(
                            cr, uid, 'account.group_account_manager'):
                        res['warning'] = {
                            'title': _('Warning - Private Car Expense'),
                            'message': _(
                                "You should not change the unit amount "
                                "for private car expenses. You should change "
                                "the Private Car Product or update the Cost "
                                "Price of the selected Private Car Product "
                                "and re-create the Expense Line.\n\nBut, as "
                                "you are in the group 'Account Manager', we "
                                "suppose that you know what you are doing, "
                                "so the original unit amount was not "
                                "restored.")}
                    else:
                        res['warning'] = {
                            'title': _('Warning - Private Car Expense'),
                            'message': _(
                                "You should not change the unit amount "
                                "for private car expenses. The original unit "
                                "amount has been restored.\n\nOnly users in "
                                "the 'Account Manager' group are allowed to "
                                "change the unit amount for private car "
                                "expenses manually.")}
                        res['value']['unit_amount'] = original_unit_amount
        return res

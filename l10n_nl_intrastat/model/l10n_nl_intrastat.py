# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP Report intrastat for NL
#    Copyright (C) 2012 - 2013 Therp BV <http://therp.nl>
#
#    Based on and containing code snippets from lp:new-report-intrastat
#    by Alexis de Lattre <alexis.delattre@akretion.com>,
#    Copyright (C) 2010-2011 Akretion (http://www.akretion.com). All Rights Reserved
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
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools.translate import _
from openerp.addons.decimal_precision import decimal_precision as dp


class l10n_nl_report_intrastat(orm.Model):
    _name = "l10n_nl.report.intrastat"
    _description = "Declaration of intracommunautary transactions (ICP)"
    _order = "period_id desc"
    _rec_name = 'period_id'

    _columns = {
        'line_ids': fields.one2many(
            'l10n_nl.report.intrastat.line',
            'report_id',
            'ICP line',
            readonly=True),
        'period_id': fields.many2one(
            'account.period',
            'Period',
            states={'done': [('readonly', True)]}),
        'company_id': fields.many2one(
            'res.company', 'Company', required=True,
            states={'done': [('readonly',True)]},
            help="Related company."),
        'total_amount': fields.float(
            'Total amount',
            digits_compute=dp.get_precision('Account'),
            readonly=True,
            help="Total amount in company currency of the declaration."),
        'state' : fields.selection(
            [
                ('draft','Draft'),
                ('done','Done'),
                ], 'State', select=True, readonly=True,
            help=("State of the declaration. When the state is set to 'Done', "
                  "the parameters become read-only.")),
        'date_done' : fields.date(
            'Date done', readonly=True,
            help=("Last date when the intrastat declaration was converted to "
                  "'Done' state.")),
        'notes' : fields.text(
            'Notes',
            help="You can add some comments here if you want."),
        }

    def get_period(self, cr, uid, context=None):
        """
        By default, take the previous period relative to the
        current date. Courtesy of Alexis.
        """
        date = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=-1), '%Y-%m-%d')
        period_ids = self.pool.get('account.period').find(
            cr, uid, dt=date, context=context)
        return period_ids and period_ids[0] or False

    _defaults = {
        'period_id': get_period,
        'state': 'draft',
        'company_id': lambda self, cr, uid, context: \
            self.pool.get('res.users').browse(
                cr, uid, uid, context=context).company_id.id,
        }

    def set_draft(self, cr, uid, ids, context=None):
        return self.write(
            cr, uid, ids, {'state': 'draft'}, context=context)

    def generate_lines(self, cr, uid, ids, context=None):
        """
        Collect the data lines for the given report.
        Unlink any existing lines first.
        """
        report_line_obj = self.pool.get('l10n_nl.report.intrastat.line')
        currency_obj = self.pool.get('res.currency')
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')

        total_amount = 0.0
        partner_amounts_map = {}
        localcontext = context and context.copy() or {}

        # Remove existing lines
        line_ids = report_line_obj.search(
            cr, uid, [('report_id', '=', ids[0])], context=context)
        report_line_obj.unlink(cr, uid, line_ids, context=context)
        report = self.browse(cr, uid, ids[0], context=context)

        if report.state != 'draft':
            raise orm.except_orm(
                _('Error'),
                _('Cannot generate reports lines in a non-draft state'))

        invoice_domain = [
                ('type', 'in', ('out_invoice', 'out_refund')),
                ('period_id', '=', report.period_id.id),
                ('state', 'in', ('open', 'paid')),
                ('company_id', '=', report.company_id.id),
                ('address_invoice_id.country_id.id', '!=',
                 report.company_id.country_id.id),
                ]

        # Signal invoices without a country
        invalid_invoice_ids = invoice_obj.search(
            cr, uid, 
            invoice_domain + [
                ('address_invoice_id.country_id', '=', False)],
            context=context)
        if invalid_invoice_ids:
            invoices = invoice_obj.read(
                cr, uid,
                invalid_invoice_ids, ['partner_id'],
                context=context)
            raise orm.except_orm(
                _('Error'), 
                _("Missing country on the invoice addresses of the following "
                  "partners:\n%s") % (
                        "\n".join([inv['partner_id'][1] for inv in invoices])
                        ))

        invoice_ids = invoice_obj.search(
            cr, uid,
            invoice_domain + [
                ('address_invoice_id.country_id.intrastat', '=', True)],
            context=context)
        invoice_line_ids = invoice_line_obj.search(
            cr, uid, [('invoice_id', 'in', invoice_ids)], context=context)

        # Gather amounts from invoice lines
        for line in invoice_line_obj.browse(
            cr, uid, invoice_line_ids, context=context):
            if any(
                tax.exclude_from_intrastat_if_present
                for tax in line.invoice_line_tax_id):
                continue           
            localcontext['date'] = line.invoice_id.date_invoice
            if line.invoice_id.partner_id.id not in partner_amounts_map:
                partner_amounts_map[line.invoice_id.partner_id.id] = {
                    'amount_product': 0.0,
                    'amount_service': 0.0,
                    }
            amounts = partner_amounts_map[line.invoice_id.partner_id.id]
            if line.product_id and (
                line.product_id.type == 'service'
                or line.product_id.is_accessory_cost):
                amount_type = 'amount_service'
            else:
                amount_type = 'amount_product'
            sign = line.invoice_id.type == 'out_refund' and -1 or 1
            amount = sign * line.price_subtotal
            if (line.invoice_id.currency_id
                and line.invoice_id.currency_id.id !=
                report.company_id.currency_id.id):
                amount = currency_obj.compute(
                    cr, uid, line.invoice_id.currency_id.id,
                    report.company_id.currency_id.id,
                    amount, context=localcontext)
            amounts[amount_type] += amount
            total_amount += amount
            
        # Create report lines
        for (partner_id, vals) in partner_amounts_map.items():
            if not (vals['amount_service'] or vals['amount_product']):
                continue
            vals.update({
                    'partner_id': partner_id,
                    'report_id': report.id
                    })
            report_line_obj.create(
                cr, uid, vals, context=context)

        return self.write(
            cr, uid, report.id, {
                'total_amount': total_amount,
                'date_done': fields.date.context_today(
                    self, cr, uid, context=context),
                'state': 'done',
                }, context=context)

    def unlink(self, cr, uid, ids, context=None):
        """
        Do not allow unlinking of confirmed reports
        """
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]
        if self.search(
            cr, uid,
            [('id', 'in', ids), ('state', '!=', 'draft')],
            context=context):
            raise orm.except_orm(
                _('Error'),
                _('Cannot remove IPC reports in a non-draft state'))
        return super(l10n_nl_report_intrastat, self).unlink(
            cr, uid, ids, context=context)


class l10n_nl_report_intrastat_line(orm.Model):
    _name = "l10n_nl.report.intrastat.line"
    _description = "ICP report line"
    _order = "report_id, country_code"
    _rec_name = 'partner_id'

    _columns = {
        'report_id': fields.many2one(
            'l10n_nl.report.intrastat',
            'ICP report',
            readonly=True,
            required=True,
            ondelete="CASCADE"),
        'partner_id': fields.many2one(
            'res.partner', 'Partner',
            readonly=True,
            required=True),
        'vat': fields.related(
            'partner_id', 'vat',
            type='char', size=32,
            string='VAT',
            store=True,
            readonly=True),
        'country_code': fields.related(
            'partner_id', 'country', 'code',
            type='char', size=2,
            string='Country Code',
            store=True,
            readonly=True,
            ),
        'amount_product': fields.float(
            'Amount products',
            digits_compute=dp.get_precision('Account'),
            readonly=True),
        'amount_service': fields.float(
            'Amount services',
            digits_compute=dp.get_precision('Account'),
            readonly=True),
        }

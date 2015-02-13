# -*- encoding: utf-8 -*-
"""Define intrastat report (ICP) for dutch tax authorities."""
##############################################################################
#
#    OpenERP Report intrastat for NL
#    Copyright (C) 2012 - 2015 Therp BV <http://therp.nl>
#
#    Based on and containing code snippets from lp:new-report-intrastat
#    by Alexis de Lattre <alexis.delattre@akretion.com>,
#    Copyright (C) 2010-2011 Akretion (http://www.akretion.com).
#    All Rights Reserved
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
from openerp import api, models, fields, _
from openerp.exceptions import Warning
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.addons.decimal_precision import decimal_precision as dp


class ReportIntrastat(models.Model):
    """Define intrastat report (ICP) for dutch tax authorities."""
    _name = "l10n_nl.report.intrastat"
    _description = "Declaration of intracommunautary transactions (ICP)"
    _order = "period_id desc"
    _rec_name = 'period_id'

    def _default_period_id(self):
        """
        By default, take the previous period relative to the
        current date. Courtesy of Alexis.
        """
        period_model = self.env['account.period']
        date = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=-1), '%Y-%m-%d')
        period_ids = period_model.find(dt=date)
        return period_ids and period_ids[0] or False

    def _default_company_id(self):
        """Default company is active user company."""
        return self.env.user.company_id.id

    period_id = fields.Many2one(
        string='Period',
        comodel_name='account.period',
        states={'done': [('readonly', True)]},
        default=_default_period_id,
    )
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',
        required=True,
        states={'done': [('readonly', True)]},
        help="Related company.",
        default=_default_company_id,
    )
    total_amount = fields.Float(
        string='Total amount',
        readonly=True,
        help="Total amount in company currency of the declaration.",
        digits=dp.get_precision('Account'),
    )
    state = fields.Selection(
        string='State',
        selection=[
            ('draft', 'Draft'),
            ('done', 'Done'),
        ],
        default='draft',
        readonly=True,
        help=(
            "State of the declaration. When the state is set to 'Done', "
            "the parameters become read-only."
        ),
    )
    date_done = fields.Date(
        string='Date done',
        readonly=True,
        help=(
            "Last date when the intrastat declaration was converted to "
            "'Done' state."
        ),
    )
    notes = fields.Text(
        string='Notes',
        help="You can add some comments here if you want.",
    )
    line_ids = fields.One2many(
        string='ICP line',
        comodel_name='l10n_nl.report.intrastat.line',
        inverse_name='report_id',
        readonly=True,
    )

    @api.one
    def set_draft(self):
        """
        Reset report state to draft.
        """
        return self.write({'state': 'draft'})

    @api.one
    def generate_lines(self):
        """
        Collect the data lines for the given report.
        Unlink any existing lines first.
        """
        # Generating lines is only allowed for report in draft state:
        if self.state != 'draft':
            raise Warning(_(
                'Cannot generate reports lines in a non-draft state'))
        # Other models:
        report_line_model = self.env['l10n_nl.report.intrastat.line']
        currency_model = self.env['res.currency']
        invoice_model = self.env['account.invoice']
        invoice_line_model = self.env['account.invoice.line']

        total_amount = 0.0
        partner_amounts_map = {}
        # Check wether all configuration done to generate report
        self.env['report.intrastat.common']._check_generate_lines(self)

        # Remove existing lines
        for line_obj in self.line_ids:
            line_obj.unlink()
        # Define search for invoices for period and company:
        company_obj = self.company_id  # simplify access
        invoice_domain = [
            ('type', 'in', ('out_invoice', 'out_refund')),
            ('period_id', '=', self.period_id.id),
            ('state', 'in', ('open', 'paid')),
            ('company_id', '=', company_obj.id),
        ]
        # Signal invoices without a country
        # (Should not happen, as country_id on parter is set to required)
        invalid_invoices = invoice_model.search_read(
            domain=invoice_domain + [('partner_id.country_id', '=', False)],
            fields=['partner_id']
        )
        if invalid_invoices:
            raise Warning(
                _(
                    "Missing country on the invoice addresses of the"
                    " following partners:\n%s"
                ) % "\n".join(
                    inv['partner_id'][1] for inv in invalid_invoices)
            )
        # Search invoices that need intrastat reporting:
        invoice_records = invoice_model.search(
            invoice_domain + [
                ('partner_id.country_id.intrastat', '=', True),
                ('partner_id.country_id.id', '!=', company_obj.country_id.id),
            ]
        )
        invoice_ids = [inv['id'] for inv in invoice_records]
        invoice_line_records = invoice_line_model.search(
            [('invoice_id', 'in', invoice_ids)])

        # Gather amounts from invoice lines
        for line in invoice_line_records:
            # Ignore invoiceline if taxes should not be included in intrastat:
            if any(
                    tax.exclude_from_intrastat_if_present
                    for tax in line.invoice_line_tax_id):
                continue
            # Report is per commercial partner:
            commercial_partner_id = (
                line.invoice_id.partner_id.commercial_partner_id.id)
            if commercial_partner_id not in partner_amounts_map:
                partner_amounts_map[commercial_partner_id] = {
                    'amount_product': 0.0,
                    'amount_service': 0.0,
                }
            amounts = partner_amounts_map[commercial_partner_id]
            # Determine product or service:
            if (line.product_id
                    and (
                        line.product_id.type == 'service'
                        or line.product_id.is_accessory_cost)):
                amount_type = 'amount_service'
            else:
                amount_type = 'amount_product'
            sign = line.invoice_id.type == 'out_refund' and -1 or 1
            amount = sign * line.price_subtotal
            # Convert currency amount if necessary:
            line_currency_obj = line.invoice_id.currency_id  # simplify
            invoice_date = line.invoice_id.date_invoice
            if (line_currency_obj
                    and line_currency_obj.id != company_obj.currency_id.id):
                amount = (
                    line_currency_obj.with_context(date=invoice_date).compute(
                        amount, company_obj.currency_id, round=True)
                )
            # Accumulate totals:
            amounts[amount_type] += amount  # per partner and type
            total_amount += amount  # grand total

        # Create report lines
        for (partner_id, vals) in partner_amounts_map.items():
            if not (vals['amount_service'] or vals['amount_product']):
                continue
            vals.update({
                'partner_id': partner_id,
                'report_id': self.id
            })
            report_line_model.create(vals)

        return self.write({
            'total_amount': total_amount,
            'date_done': fields.Date.today(),
            'state': 'done',
        })

    def unlink(self, cr, uid, ids, context=None):
        """
        Do not allow unlinking of confirmed reports
        """
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]
        non_draft_ids = self.search(
            cr, uid,
            [('id', 'in', ids), ('state', '!=', 'draft')],
            context=context
        )
        if non_draft_ids:
            raise Warning(_('Cannot remove IPC reports in a non-draft state'))
        return super(ReportIntrastat, self).unlink(
            cr, uid, ids, context=context)


class ReportIntrastatLine(models.Model):
    """Lines for dutch ICP report."""
    _name = "l10n_nl.report.intrastat.line"
    _description = "ICP report line"
    _order = "report_id, country_code"
    _rec_name = 'partner_id'

    report_id = fields.Many2one(
        string='ICP report',
        comodel_name='l10n_nl.report.intrastat',
        readonly=True,
        required=True,
        ondelete="CASCADE"
    )
    partner_id = fields.Many2one(
        string='Partner',
        comodel_name='res.partner',
        readonly=True,
        required=True,
    )
    vat = fields.Char(
        string='VAT',
        related='partner_id.vat',
        store=True,
        readonly=True,
    )
    country_code = fields.Char(
        string='Country Code',
        related='partner_id.country_id.code',
        store=True,
        readonly=True,
    )
    amount_product = fields.Float(
        string='Amount products',
        readonly=True,
        digits=dp.get_precision('Account'),
    )
    amount_service = fields.Float(
        string='Amount services',
        readonly=True,
        digits=dp.get_precision('Account'),
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

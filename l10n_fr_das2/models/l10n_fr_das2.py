# -*- coding: utf-8 -*-
# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from dateutil.relativedelta import relativedelta


class L10nFrDas2(models.Model):
    _name = 'l10n.fr.das2'
    _inherit = ['mail.thread']
    _order = 'date_start desc'
    _description = 'DAS2'

    date_range_id = fields.Many2one(
        'date.range', string='Fiscal Year', ondelete='restrict', copy=False,
        required=True, domain="[('type_id.fiscal_year', '=', True)]",
        states={'done': [('readonly', True)]}, track_visibility='onchange',
        default=lambda self: self._default_date_range())
    date_start = fields.Date(
        related='date_range_id.date_start', store=True, readonly=True)
    date_end = fields.Date(
        related='date_range_id.date_end', store=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ], default='draft', readonly=True, string='State')
    company_id = fields.Many2one(
        'res.company', string='Company',
        ondelete='cascade', required=True,
        states={'done': [('readonly', True)]},
        default=lambda self: self.env['res.company']._company_default_get())
    total_amount = fields.Monetary(
        compute='_compute_total_amount', currency_field='currency_id',
        string='Total Amount To Declare', store=True, readonly=True,
        track_visibility='onchange')
    currency_id = fields.Many2one(
        related='company_id.currency_id', readonly=True, store=True,
        string='Company Currency')
    source_journal_ids = fields.Many2many(
        'account.journal',
        string='Source Journals', required=True,
        default=lambda self: self._default_source_journals(),
        states={'done': [('readonly', True)]})
    line_ids = fields.One2many(
        'l10n.fr.das2.line', 'parent_id', string='Lines',
        states={'done': [('readonly', True)]})
    # option for draft moves ?

    _sql_constraints = [(
        'fiscal_year_company_uniq',
        'unique(company_id, date_range_id)',
        'A DAS2 already exists for this fiscal year!')]

    def _default_source_journals(self):
        res = []
        src_journals = self.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', self.env.user.company_id.id)])
        if src_journals:
            res = src_journals.ids
        return res

    @api.depends('line_ids.amount')
    def _compute_total_amount(self):
        rg_res = self.env['l10n.fr.das2.line'].read_group(
            [('parent_id', 'in', self.ids), ('to_declare', '=', True)],
            ['parent_id', 'amount'], ['parent_id'])
        mapped_data = dict([(x['parent_id'][0], x['amount']) for x in rg_res])
        for rec in self:
            rec.total_amount = mapped_data.get(rec.id, 0)

    @api.model
    def _default_date_range(self):
        date_range = self.env['date.range'].search([
            ('company_id', '=', self.env.user.company_id.id),
            ('type_id.fiscal_year', '=', True),
            ('date_end', '<', fields.Date.context_today(self)),
            ], order='date_end desc', limit=1)
        return date_range

    def done(self):
        self.state = 'done'
        return

    def back2draft(self):
        self.state = 'draft'
        return

    def generate_lines(self):
        self.ensure_one()
        smo = self.env['account.move']
        lfdlo = self.env['l10n.fr.das2.line']
        if not self.company_id.country_id:
            raise UserError(_(
                "Country not set on company '%s'.")
                % self.company_id.display_name)
        if (
                self.company_id.country_id.code not in
                ('FR', 'GP', 'MQ', 'GF', 'RE', 'YT')):
            raise UserError(_(
                "Company '%s' is configured in country '%s'. The DAS2 is "
                "only for France and it's oversea territories.")
                % (self.company_id.display_name,
                   self.company_id.country_id.name))
        if self.company_id.currency_id != self.env.ref('base.EUR'):
            raise UserError(_(
                "Company '%s' is configured with currency '%s'. "
                "It should be EUR.")
                % (self.company_id.display_name,
                   self.company_id.currency_id.name))
        if self.company_id.fr_das2_partner_declare_threshold <= 0:
            raise UserError(_(
                "The DAS2 partner declaration threshold is not set on "
                "company '%s'.") % self.company_id.display_name)
        threshold = self.company_id.fr_das2_partner_declare_threshold
        das2_accounts = self.env['account.account'].search([
            ('company_id', '=', self.company_id.id),
            ('fr_das2', '=', True),
            ])
        if not das2_accounts:
            raise UserError(_(
                "There are no accounts flagged for DAS2 in company '%s'.")
                % self.company_id.display_name)
        # delete existing lines
        self.line_ids.unlink()
        date_end_scan_dt = fields.Date.from_string(self.date_end)\
            + relativedelta(months=5)
        date_start_scan_dt = fields.Date.from_string(self.date_start)\
            - relativedelta(years=1)
        rg_res = self.env['account.move.line'].read_group([
            ('company_id', '=', self.company_id.id),
            ('date', '>=', fields.Date.to_string(date_start_scan_dt)),
            ('date', '<=', fields.Date.to_string(date_end_scan_dt)),
            ('account_id', 'in', das2_accounts.ids),
            ('journal_id', 'in', self.source_journal_ids.ids),
            ], ['move_id'], ['move_id'])
        payable_acc_type = self.env.ref('account.data_account_type_payable')
        res = {}
        for rg_re in rg_res:
            move_id = rg_re['move_id'][0]
            move = smo.browse(move_id)
            for line in move.line_ids:
                if (
                        line.account_id.user_type_id == payable_acc_type and
                        line.partner_id and
                        line.full_reconcile_id):
                    for rec_line in line.full_reconcile_id.reconciled_line_ids:
                        if (
                                rec_line != line and
                                rec_line.journal_id.type in ('bank', 'cash')
                                and
                                rec_line.date >= self.date_start and
                                rec_line.date <= self.date_end and
                                rec_line.partner_id == line.partner_id):
                            if rec_line.partner_id in res:
                                res[rec_line.partner_id] += rec_line.balance
                            else:
                                res[rec_line.partner_id] = rec_line.balance
        for partner, amount in res.items():
            vals = {
                'parent_id': self.id,
                'partner_id': partner.id,
                'amount': amount,
                }
            if partner.siren and partner.nic:
                vals['partner_siret'] = partner.siret
            if float_compare(amount, threshold, precision_digits=0) >= 0:
                vals['to_declare'] = True
            lfdlo.create(vals)

    def generate_file(self):
        self.ensure_one()
        raise UserError(_("This feature is not implemented yet."))

    def button_lines_fullscreen(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window'].for_xml_id(
            'l10n_fr_das2', 'l10n_fr_das2_line_action')
        action.update({
            'domain': [('parent_id', '=', self.id)],
            'views': False,
            })
        return action


class L10nFrDas2Line(models.Model):
    _name = 'l10n.fr.das2.line'
    _description = 'DAS2 line'

    parent_id = fields.Many2one(
        'l10n.fr.das2', string='DAS2 Report', ondelete='cascade')
    partner_id = fields.Many2one(
        'res.partner', string='Supplier', ondelete='restrict',
        states={'done': [('readonly', True)]}, required=True)
    partner_siret = fields.Char(
        string='Partner SIRET', states={'done': [('readonly', True)]})
    currency_id = fields.Many2one(
        related='parent_id.company_id.currency_id', store=True, readonly=True,
        string='Company Currency')
    amount = fields.Monetary(states={'done': [('readonly', True)]})
    to_declare = fields.Boolean(
        string='To Declare', states={'done': [('readonly', True)]})
    state = fields.Selection(
        related='parent_id.state', store=True, readonly=True)

    _sql_constraints = [(
        'amount_positive',
        'CHECK(amount >= 0)',
        'The amount of a DAS2 line must be positive!')]

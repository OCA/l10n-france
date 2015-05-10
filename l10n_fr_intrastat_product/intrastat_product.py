# -*- encoding: utf-8 -*-
##############################################################################
#
#    L10n FR Report intrastat product module for Odoo
#    Copyright (C) 2009-2015 Akretion (http://www.akretion.com)
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

from openerp import models, fields, api, _
from openerp.exceptions import Warning, ValidationError
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
from lxml import etree

logger = logging.getLogger(__name__)


class L10nFrReportIntrastatProduct(models.Model):
    _name = "l10n.fr.report.intrastat.product"
    _description = "Intrastat Product for France (DEB)"
    _rec_name = "start_date"
    _inherit = ['mail.thread', 'report.intrastat.common']
    _order = "start_date desc, type"
    _track = {
        'state': {
            'l10n_fr_intrastat_product.l10n_fr_declaration_done':
            lambda self, cr, uid, obj, ctx=None: obj['state'] == 'done',
            }
        }

    @api.one
    @api.depends(
        'intrastat_line_ids', 'intrastat_line_ids.amount_company_currency',
        'intrastat_line_ids.intrastat_type_id')
    def _compute_total_fiscal_amount(self):
        total_fiscal_amount = 0.0
        for line in self.intrastat_line_ids:
            total_fiscal_amount +=\
                line.amount_company_currency *\
                line.intrastat_type_id.fiscal_value_multiplier
        self.total_fiscal_amount = total_fiscal_amount

    @api.model
    def _default_type(self):
        if self.company_id.import_obligation_level == 'none':
            return 'export'
        else:
            return False

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        states={'done': [('readonly', True)]},
        default=lambda self: self.env['res.company']._company_default_get(
            'l10n.fr.report.intrastat.product'))
    start_date = fields.Date(
        string='Start Date', required=True,
        states={'done': [('readonly', True)]}, copy=False,
        default=
        lambda self: datetime.today() + relativedelta(day=1, months=-1),
        help="Start date of the declaration. Must be the first day of "
        "a month.")
    end_date = fields.Date(
        compute='_compute_dates', string='End Date', readonly=True, store=True,
        help="End date for the declaration. Is the last day of the "
        "month of the start date.")
    year_month = fields.Char(
        compute='_compute_dates', string='Month', readonly=True,
        track_visibility='always', store=True,
        help="Year and month of the declaration.")
    type = fields.Selection([
        ('import', 'Import'),
        ('export', 'Export')
        ], 'Type', required=True, states={'done': [('readonly', True)]},
        default=_default_type,
        track_visibility='always', help="Select the type of DEB.")
    obligation_level = fields.Selection([
        ('detailed', 'Detailed'),
        ('simplified', 'Simplified')
        ], string='Obligation Level', required=True, track_visibility='always',
        states={'done': [('readonly', True)]},
        help="Your obligation level for a certain type of DEB "
        "(Import or Export) depends on the total value that you export "
        "or import per year. Note that the obligation level 'Simplified' "
        "doesn't exist for an Import DEB.")
    intrastat_line_ids = fields.One2many(
        'l10n.fr.report.intrastat.product.line',
        'parent_id', string='Report Intrastat Product Lines',
        states={'done': [('readonly', True)]})
    num_lines = fields.Integer(
        compute='_compute_numbers', string='Number of Lines', store=True,
        track_visibility='always', help="Number of lines in this declaration.")
    total_amount = fields.Float(
        compute='_compute_numbers', digits=dp.get_precision('Account'),
        string='Total Amount', store=True,
        help="Total amount in company currency of the declaration.")
    total_fiscal_amount = fields.Float(
        compute='_compute_total_fiscal_amount',
        digits=dp.get_precision('Account'),
        string='Total Fiscal Amount', track_visibility='always', store=True,
        help="Total fiscal amount in company currency of the declaration. "
        "This is the total amount that is displayed on the Prodouane website.")
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True,
        string='Currency')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ], string='State', readonly=True, track_visibility='onchange',
        copy=False, default='draft',
        help="State of the declaration. When the state is set to 'Done', "
        "the parameters become read-only.")
    # No more need for date_done, because chatter does the job

    @api.multi
    def type_on_change(
            self, company_id=False, type=False, context=None):
        result = {}
        result['value'] = {}
        if type and company_id:
            company = self.env['res.company'].browse(company_id)
            if type == 'import':
                if company.import_obligation_level:
                    if company.import_obligation_level == 'detailed':
                        result['value']['obligation_level'] =\
                            company.import_obligation_level
                    elif company.import_obligation_level == 'none':
                        result['warning'] = {
                            'title': _("Warning on the Obligation Level"),
                            'message':
                            _("You are tying to make an "
                                "Intrastat Product of type 'Import', "
                                "but the Import Obligation Level set "
                                "for your company is 'None'. If this "
                                "parameter on your company is correct, "
                                "you should NOT create an Import Intrastat "
                                "Product."),
                        }
            if type == 'export':
                if company.export_obligation_level:
                    result['value']['obligation_level'] =\
                        company.export_obligation_level
        return result

    @api.constrains('start_date')
    def _product_check_start_date(self):
        self._check_start_date()

    @api.one
    @api.constrains('type', 'obligation_level')
    def _check_obligation_level(self):
        if self.type == 'import' and self.obligation_level == 'simplified':
            raise ValidationError(
                _("Obligation level can't be 'Simplified' for Import"))

    _sql_constraints = [(
        'date_company_type_uniq',
        'unique(start_date, company_id, type)',
        'A DEB of the same type already exists for this month !')]

    @api.multi
    def create_intrastat_product_lines(self, invoice, parent_values):
        """This function is called for each invoice"""
        self.ensure_one()
        line_obj = self.env['l10n.fr.report.intrastat.product.line']
        weight_uom_categ = self.env.ref('product.product_uom_categ_kgm')
        kg_uom = self.env.ref('product.product_uom_kgm')
        pce_uom_categ = self.env.ref('product.product_uom_categ_unit')
        pce_uom = self.env.ref('product.product_uom_unit')

        lines_to_create = []
        total_invoice_cur_accessory_cost = 0.0
        total_invoice_cur_product_value = 0.0
        for line in invoice.invoice_line:
            line_qty = line.quantity
            source_uom = line.uos_id

            # We don't do anything when there is no product_id...
            # this may be a problem... but i think a raise would be too violent
            if not line.product_id:
                continue

            if line.product_id.exclude_from_intrastat:
                continue

            if not line_qty:
                continue

            # If type = "service" and is_accessory_cost=True, then we keep
            # the line (it will be skipped later on)
            if (
                    line.product_id.type not in ('product', 'consu')
                    and not line.product_id.is_accessory_cost):
                continue

            skip_this_line = False
            for line_tax in line.invoice_line_tax_id:
                if line_tax.exclude_from_intrastat_if_present:
                    skip_this_line = True
            if skip_this_line:
                continue
            if (
                    line.product_id.is_accessory_cost
                    and line.product_id.type == 'service'):
                total_invoice_cur_accessory_cost += line.price_subtotal
                continue
            # END OF "continue" instructions
            ## AFTER THIS POINT, we are sure to have real products that
            ## have to be declared to DEB
            amount_product_value_inv_cur_to_write = line.price_subtotal
            total_invoice_cur_product_value += line.price_subtotal
            invoice_currency_id_to_write = invoice.currency_id.id

            if not parent_values['is_fiscal_only']:

                if not source_uom:
                    raise Warning(
                        _("Missing unit of measure on the line with %d "
                            "product(s) '%s' on invoice '%s'.")
                        % (line_qty, line.product_id.name, invoice.number))
                else:
                    source_uom_id_to_write = source_uom.id

                if source_uom == kg_uom:
                    weight_to_write = line_qty
                elif source_uom.category_id == weight_uom_categ:
                    weight_to_write = self.env['product.uom']._compute_qty_obj(
                        source_uom, line_qty, kg_uom)
                elif source_uom.category_id == pce_uom_categ:
                    if not line.product_id.weight_net:
                        raise Warning(
                            _("Missing net weight on product '%s'.")
                            % (line.product_id.name))
                    if source_uom == pce_uom:
                        weight_to_write = line.product_id.weight_net * line_qty
                    else:
                        # Here, I suppose that, on the product, the
                        # weight is per PCE and not per uom_id
                        weight_to_write = line.product_id.weight_net * \
                            self.env['product.uom']._compute_qty_obj(
                                source_uom, line_qty, pce_uom)

                else:
                    raise Warning(
                        _("Conversion from unit of measure '%s' to 'Kg' "
                            "is not implemented yet.")
                        % (source_uom.name))

                product_intrastat_code = line.product_id.intrastat_id
                if not product_intrastat_code:
                    # If the H.S. code is not set on the product,
                    # we check if it's set on it's related category
                    product_intrastat_code =\
                        line.product_id.categ_id.intrastat_id
                    if not product_intrastat_code:
                        raise Warning(
                            _("Missing H.S. code on product '%s' or on it's "
                                "related category '%s'.") % (
                                line.product_id.name,
                                line.product_id.categ_id.complete_name))
                intrastat_code_id_to_write = product_intrastat_code.id

                if not product_intrastat_code.intrastat_code:
                    raise Warning(
                        _("Missing intrastat code on H.S. code '%s' (%s).") % (
                            product_intrastat_code.name,
                            product_intrastat_code.description))
                else:
                    intrastat_code_to_write =\
                        product_intrastat_code.intrastat_code

                if not product_intrastat_code.intrastat_uom_id:
                    intrastat_uom_id_to_write = False
                    quantity_to_write = False
                else:
                    intrastat_uom_id_to_write =\
                        product_intrastat_code.intrastat_uom_id.id
                    if intrastat_uom_id_to_write == source_uom_id_to_write:
                        quantity_to_write = line_qty
                    elif (
                            source_uom.category_id ==
                            product_intrastat_code.intrastat_uom_id.
                            category_id):
                        quantity_to_write =\
                            self.pool['product.uom']._compute_qty_obj(
                                source_uom, line_qty,
                                product_intrastat_code.intrastat_uom_id)
                    else:
                        raise Warning(
                            _("On invoice '%s', the line with product '%s' "
                                "has a unit of measure (%s) which can't be "
                                "converted to UoM of it's intrastat "
                                "code (%s).") % (
                                invoice.number,
                                line.product_id.name,
                                source_uom_id_to_write,
                                intrastat_uom_id_to_write))

                # The origin country should only be declated on Import
                if self.type == 'export':
                    product_country_origin_id_to_write = False
                elif line.product_id.origin_country_id:
                # If we have the country of origin on the product -> take it
                    product_country_origin_id_to_write =\
                        line.product_id.origin_country_id.id
                else:
                    # If we don't, look on the product supplier info
                    origin_partner_id =\
                        parent_values.get('origin_partner_id', False)
                    if origin_partner_id:
                        supplieri_obj = self.env['product.supplierinfo']
                        suppliers = supplieri_obj.search([
                            ('name', '=', origin_partner_id),
                            (
                                'product_tmpl_id',
                                '=',
                                line.product_id.product_tmpl_id.id),
                            ('origin_country_id', '!=', False)
                            ])
                        if not suppliers:
                            raise Warning(
                                _("Missing country of origin on product '%s' "
                                    "or on it's supplier information for "
                                    "partner '%s'.") % (
                                    line.product_id.name,
                                    parent_values.get(
                                        'origin_partner_name', 'none')))
                        else:
                            product_country_origin_id_to_write =\
                                suppliers[0].origin_country_id.id
                    else:
                        raise Warning(
                            _("Missing country of origin on product '%s' "
                                "(it's not possible to get the country of "
                                "origin from the 'supplier information' in "
                                "this case because we don't know the "
                                "supplier of this product for the "
                                "invoice '%s').")
                            % (line.product_id.name, invoice.number))

            else:
                weight_to_write = False
                source_uom_id_to_write = False
                intrastat_code_id_to_write = False
                intrastat_code_to_write = False
                quantity_to_write = False
                intrastat_uom_id_to_write = False
                product_country_origin_id_to_write = False

            create_new_line = True
            #print "lines_to_create =", lines_to_create
            for line_to_create in lines_to_create:
                #print "line_to_create =", line_to_create
                if (
                        line_to_create.get('intrastat_code_id', False) ==
                        intrastat_code_id_to_write
                        and line_to_create.get('source_uom_id', False) ==
                        source_uom_id_to_write
                        and line_to_create.get('intrastat_type_id', False) ==
                        parent_values['intrastat_type_id_to_write']
                        and line_to_create.get(
                            'product_country_origin_id', False) ==
                        product_country_origin_id_to_write):
                    create_new_line = False
                    line_to_create['quantity'] += quantity_to_write
                    line_to_create['weight'] += weight_to_write
                    line_to_create['amount_product_value_inv_cur'] +=\
                        amount_product_value_inv_cur_to_write
                    break
            if create_new_line:
                lines_to_create.append({
                    'parent_id': self.id,
                    'invoice_id': invoice.id,
                    'quantity': quantity_to_write,
                    'source_uom_id': source_uom_id_to_write,
                    'intrastat_uom_id': intrastat_uom_id_to_write,
                    'partner_country_id':
                    parent_values['partner_country_id_to_write'],
                    'intrastat_code': intrastat_code_to_write,
                    'intrastat_code_id': intrastat_code_id_to_write,
                    'weight': weight_to_write,
                    'product_country_origin_id':
                    product_country_origin_id_to_write,
                    'transport': parent_values['transport_to_write'],
                    'department': parent_values['department_to_write'],
                    'intrastat_type_id':
                    parent_values['intrastat_type_id_to_write'],
                    'procedure_code': parent_values['procedure_code_to_write'],
                    'transaction_code':
                    parent_values['transaction_code_to_write'],
                    'partner_id': parent_values['partner_id_to_write'],
                    'invoice_currency_id': invoice_currency_id_to_write,
                    'amount_product_value_inv_cur':
                    amount_product_value_inv_cur_to_write,
                    'is_fiscal_only': parent_values['is_fiscal_only'],
                })
        # End of the loop on invoice lines

        # Why do I manage the Partner VAT number only here and not earlier
        # in the code ?
        # Because, if I sell to a physical person in the EU with VAT, then
        # the corresponding partner will not have a VAT number, and the entry
        # will be skipped because line_tax.exclude_from_intrastat_if_present
        # is always True
        # So we should not block with a raise before the end of the loop on the
        # invoice lines
        if lines_to_create:
            if parent_values['is_vat_required']:
                # If I have invoice.intrastat_country_id and the invoice
                # partner is outside the EU, then I look for the fiscal rep
                # of the partner
                if (
                        invoice.intrastat_country_id
                        and not invoice.partner_id.country_id.intrastat):
                    if not invoice.partner_id.intrastat_fiscal_representative:
                        raise Warning(
                            _("Missing fiscal representative for partner "
                                "'%s'. It is required for invoice '%s' which "
                                "has an invoice partner outside the EU but "
                                "the goods were delivered to or received "
                                "from inside the EU.")
                            % (invoice.partner_id.name, invoice.number))
                    else:
                        parent_values['partner_vat_to_write'] =\
                            invoice.partner_id.\
                            intrastat_fiscal_representative.vat
                # Otherwise, I just read the vat number on the partner
                # of the invoice
                else:

                    if not invoice.partner_id.vat:
                        raise Warning(
                            _("Missing VAT number on partner '%s'.")
                            % invoice.partner_id.name)
                    else:
                        parent_values['partner_vat_to_write'] =\
                            invoice.partner_id.vat
            else:
                parent_values['partner_vat_to_write'] = False

        for line_to_create in lines_to_create:
            line_to_create['partner_vat'] =\
                parent_values['partner_vat_to_write']

            if not total_invoice_cur_accessory_cost:
                line_to_create['amount_accessory_cost_inv_cur'] = 0
            else:
                if total_invoice_cur_product_value:
                    # The accessory costs are added at the pro-rata of value
                    line_to_create['amount_accessory_cost_inv_cur'] =\
                        total_invoice_cur_accessory_cost *\
                        line_to_create['amount_product_value_inv_cur']\
                        / total_invoice_cur_product_value
                else:
                    # The accessory costs are added at the pro-rata
                    # of the number of lines
                    line_to_create['amount_accessory_cost_inv_cur'] =\
                        total_invoice_cur_accessory_cost / len(lines_to_create)

            line_to_create['amount_invoice_currency'] =\
                line_to_create['amount_product_value_inv_cur'] +\
                line_to_create['amount_accessory_cost_inv_cur']

            # We do currency conversion NOW
            if invoice.currency_id.name != 'EUR':
                # for currency conversion
                line_to_create['amount_company_currency'] =\
                    self.env['res.currency'].with_context(
                        date=invoice.date_invoice).compute(
                        invoice.currency_id,
                        self.company_id.currency_id,
                        line_to_create['amount_invoice_currency'])
            else:
                line_to_create['amount_company_currency'] =\
                    line_to_create['amount_invoice_currency']
            # We round
            line_to_create['amount_company_currency'] = int(
                round(line_to_create['amount_company_currency']))
            if line_to_create['amount_company_currency'] == 0:
                # p20 of the BOD :
                # lines with value rounded to 0 mustn't be declared
                continue
            for value in ['quantity', 'weight']:  # These 2 fields are char
                if line_to_create[value]:
                    line_to_create[value] = str(
                        int(round(line_to_create[value], 0)))
            line_obj.create(line_to_create)
        return True

    @api.multi
    def compute_invoice_values(self, invoice, parent_values):
        self.ensure_one()
        intrastat_type = self.env['report.intrastat.type'].browse(
            parent_values['intrastat_type_id_to_write'])
        parent_values['procedure_code_to_write'] =\
            intrastat_type.procedure_code
        parent_values['transaction_code_to_write'] =\
            intrastat_type.transaction_code
        parent_values['is_fiscal_only'] = intrastat_type.is_fiscal_only
        parent_values['is_vat_required'] = intrastat_type.is_vat_required

        if self.obligation_level == 'simplified':
            # force to is_fiscal_only
            parent_values['is_fiscal_only'] = True

        if not parent_values['is_fiscal_only']:
            if not invoice.intrastat_transport:
                if not self.company_id.default_intrastat_transport:
                    raise Warning(
                        _("The mode of transport is not set on invoice "
                            "'%s' nor the default mode of transport on "
                            "the company '%s'.")
                        % (invoice.number, self.company_id.name))
                else:
                    parent_values['transport_to_write'] =\
                        self.company_id.default_intrastat_transport
            else:
                parent_values['transport_to_write'] =\
                    invoice.intrastat_transport

            if not invoice.intrastat_department:
                if not self.company_id.default_intrastat_department:
                    raise Warning(
                        _("The intrastat department hasn't been set on "
                            "invoice '%s' and the default intrastat "
                            "department is missing on the company '%s'.")
                        % (invoice.number, self.company_id.name))
                else:
                    parent_values['department_to_write'] =\
                        self.company_id.default_intrastat_department
            else:
                parent_values['department_to_write'] =\
                    invoice.intrastat_department
        else:
            parent_values['department_to_write'] = False
            parent_values['transport_to_write'] = False
            parent_values['transaction_code_to_write'] = False
            parent_values['partner_country_id_to_write'] = False
        #print "parent_values =", parent_values
        return parent_values

    @api.multi
    def generate_product_lines_from_invoice(self):
        '''Function called by the button on form view'''
        self.ensure_one()
        self._check_generate_lines()
        line_obj = self.env['l10n.fr.report.intrastat.product.line']
        to_remove_lines = line_obj.search([
            ('parent_id', '=', self.id),
            ('invoice_id', '!=', False)])
        if to_remove_lines:
            to_remove_lines.unlink()

        invoice_obj = self.env['account.invoice']
        invoice_type = False
        if self.type == 'import':
            # Les régularisations commerciales à l'HA ne sont PAS déclarées
            # dans la DEB, cf page 50 du BOD 6883 du 06 janvier 2011
            invoice_type = ('in_invoice', )
        elif self.type == 'export':
            invoice_type = ('out_invoice', 'out_refund')
        invoices = invoice_obj.search([
            ('type', 'in', invoice_type),
            ('date_invoice', '<=', self.end_date),
            ('date_invoice', '>=', self.start_date),
            ('state', 'in', ('open', 'paid')),
            ('company_id', '=', self.company_id.id)
            ], order='date_invoice')
        #print "invoice_ids=", invoice_ids
        for invoice in invoices:
            #print "INVOICE num =", invoice.number
            parent_values = {}

            # We should always have a country on partner_id
            if not invoice.partner_id.country_id:
                raise Warning(
                    _("Missing country on partner '%s'.")
                    % invoice.partner_id.name)

            # If I have no invoice.intrastat_country_id, which is the
            # case the first month of the deployment of the module,
            # then I use the country on invoice partner
            if not invoice.intrastat_country_id:
                if not invoice.partner_id.country_id.intrastat:
                    continue
                elif (
                        invoice.partner_id.country_id ==
                        self.company_id.country_id):
                    continue
                else:
                    parent_values['partner_country_id_to_write'] =\
                        invoice.partner_id.country_id.id

            # If I have invoice.intrastat_country_id, which should be
            # the case after the first month of use of the module, then
            # I use invoice.intrastat_country_id
            else:
                if not invoice.intrastat_country_id.intrastat:
                    continue
                elif (
                        invoice.intrastat_country_id ==
                        self.company_id.country_id):
                    continue
                else:
                    parent_values['partner_country_id_to_write'] =\
                        invoice.intrastat_country_id.id
            if not invoice.intrastat_type_id:
                if invoice.type == 'out_invoice':
                    if self.company_id.default_intrastat_type_out_invoice:
                        parent_values['intrastat_type_id_to_write'] =\
                            self.company_id.\
                            default_intrastat_type_out_invoice.id
                    else:
                        raise Warning(
                            _("The intrastat type hasn't been set on "
                                "invoice '%s' and the 'default intrastat "
                                "type for customer invoice' is missing "
                                "for the company '%s'.")
                            % (invoice.number, self.company_id.name))
                elif invoice.type == 'out_refund':
                    if self.company_id.default_intrastat_type_out_refund:
                        parent_values['intrastat_type_id_to_write'] =\
                            self.company_id.\
                            default_intrastat_type_out_refund.id
                    else:
                        raise Warning(
                            _("The intrastat type hasn't been set on refund "
                                "'%s' and the 'default intrastat type for "
                                "customer refund' is missing for the "
                                "company '%s'.")
                            % (invoice.number, self.company_id.name))
                elif invoice.type == 'in_invoice':
                    if self.company_id.default_intrastat_type_in_invoice:
                        parent_values['intrastat_type_id_to_write'] =\
                            self.company_id.\
                            default_intrastat_type_in_invoice.id
                    else:
                        raise Warning(
                            _("The intrastat type hasn't been set on "
                                "invoice '%s' and the 'Default intrastat "
                                "type for supplier invoice' is missing "
                                "for the company '%s'.")
                            % (invoice.number, self.company_id.name))

            else:
                parent_values['intrastat_type_id_to_write'] =\
                    invoice.intrastat_type_id.id

            if (
                    invoice.intrastat_country_id
                    and not invoice.partner_id.country_id.intrastat
                    and invoice.partner_id.intrastat_fiscal_representative):
                # fiscal rep
                parent_values['partner_id_to_write'] =\
                    invoice.partner_id.intrastat_fiscal_representative.id
            else:
                parent_values['partner_id_to_write'] = invoice.partner_id.id

            # Get partner on which we will check the 'country of origin'
            # on product_supplierinfo
            parent_values['origin_partner_id'] = invoice.partner_id.id
            parent_values['origin_partner_name'] = invoice.partner_id.name

            parent_values = self.compute_invoice_values(invoice, parent_values)

            self.create_intrastat_product_lines(invoice, parent_values)
        return True

    @api.multi
    def done(self):
        self.write({'state': 'done'})
        return True

    @api.multi
    def back2draft(self):
        self.write({'state': 'draft'})
        return True

    @api.multi
    def generate_xml(self):
        '''Generate the INSTAT XML file export.'''
        self.ensure_one()
        start_date_str = self.start_date
        start_date_datetime = fields.Date.from_string(start_date_str)

# TODO        self.pool.get('report.intrastat.common')._check_generate_xml(cr, uid, intrastat, context=context)

        my_company_vat = self.company_id.partner_id.vat.replace(' ', '')

        if not self.company_id.siret:
            raise Warning(
                _("The SIRET is not set on company '%s'.")
                % self.company_id.name)
        my_company_identifier = my_company_vat + self.company_id.siret[9:]

        my_company_currency = self.company_id.currency_id.name

        root = etree.Element('INSTAT')
        envelope = etree.SubElement(root, 'Envelope')
        envelope_id = etree.SubElement(envelope, 'envelopeId')
        if not self.company_id.customs_accreditation:
            raise Warning(
                _("The customs accreditation identifier is not set "
                    "for the company '%s'.") % self.company_id.name)
        envelope_id.text = self.company_id.customs_accreditation
        create_date_time = etree.SubElement(envelope, 'DateTime')
        create_date = etree.SubElement(create_date_time, 'date')
        create_date.text = datetime.strftime(datetime.today(), '%Y-%m-%d')
        create_time = etree.SubElement(create_date_time, 'time')
        create_time.text = datetime.strftime(datetime.today(), '%H:%M:%S')
        party = etree.SubElement(
            envelope, 'Party', partyType="PSI", partyRole="PSI")
        party_id = etree.SubElement(party, 'partyId')
        party_id.text = my_company_identifier
        party_name = etree.SubElement(party, 'partyName')
        party_name.text = self.company_id.name
        software_used = etree.SubElement(envelope, 'softwareUsed')
        software_used.text = 'OpenERP'
        declaration = etree.SubElement(envelope, 'Declaration')
        declaration_id = etree.SubElement(declaration, 'declarationId')
        declaration_id.text = datetime.strftime(start_date_datetime, '%Y%m')
        reference_period = etree.SubElement(declaration, 'referencePeriod')
        reference_period.text = datetime.strftime(start_date_datetime, '%Y-%m')
        psi_id = etree.SubElement(declaration, 'PSIId')
        psi_id.text = my_company_identifier
        function = etree.SubElement(declaration, 'Function')
        function_code = etree.SubElement(function, 'functionCode')
        function_code.text = 'O'
        declaration_type_code = etree.SubElement(
            declaration, 'declarationTypeCode')
        assert self.obligation_level in ('detailed', 'simplified'),\
            "Invalid obligation level"
        if self.obligation_level == 'detailed':
            declaration_type_code.text = '1'
        elif self.obligation_level == 'simplified':
            declaration_type_code.text = '4'
        flow_code = etree.SubElement(declaration, 'flowCode')

        assert self.type in ('export', 'import'),\
            "The DEB must be of type 'Import' or 'Export'"
        if self.type == 'export':
            flow_code.text = 'D'
        elif self.type == 'import':
            flow_code.text = 'A'
        currency_code = etree.SubElement(declaration, 'currencyCode')
        assert my_company_currency == 'EUR', "Company currency must be 'EUR'"
        currency_code.text = my_company_currency

        # TODO : to CONTINUE
        # THEN, the fields which vary from a line to the next
        line = 0
        for pline in self.intrastat_line_ids:
            line += 1  # increment line number
            #print "line =", line
            assert pline.intrastat_type_id, "Missing Intrastat Type"
            intrastat_type = pline.intrastat_type_id
            item = etree.SubElement(declaration, 'Item')
            item_number = etree.SubElement(item, 'itemNumber')
            item_number.text = str(line)
            # START of elements which are only required in "detailed" level
            if (
                    self.obligation_level == 'detailed'
                    and not intrastat_type.is_fiscal_only):
                cn8 = etree.SubElement(item, 'CN8')
                cn8_code = etree.SubElement(cn8, 'CN8Code')
                if not pline.intrastat_code:
                    raise Warning(
                        _('Missing Intrastat code on line %d.') % line)
                cn8_code.text = pline.intrastat_code
                # We fill SUCode only if the H.S. code requires it
                if pline.intrastat_uom_id:
                    su_code = etree.SubElement(cn8, 'SUCode')
                    if not pline.intrastat_uom_id.intrastat_label:
                        raise Warning(
                            _('Missing Intrastat UoM on line %d.') % line)
                    su_code.text = pline.intrastat_uom_id.intrastat_label
                    destination_country = etree.SubElement(
                        item, 'MSConsDestCode')
                    if self.type == 'import':
                        country_origin = etree.SubElement(
                            item, 'countryOfOriginCode')
                    weight = etree.SubElement(item, 'netMass')
                    quantity_in_SU = etree.SubElement(item, 'quantityInSU')

                    if not pline.quantity:
                        raise Warning(
                            _('Missing quantity on line %d.') % line)
                    quantity_in_SU.text = pline.quantity
                else:
                    destination_country = etree.SubElement(
                        item, 'MSConsDestCode')
                    if self.type == 'import':
                        country_origin = etree.SubElement(
                            item, 'countryOfOriginCode')
                    weight = etree.SubElement(item, 'netMass')
                if not pline.partner_country_code:
                    raise Warning(
                        _('Missing partner country on line %d.') % line)
                destination_country.text = pline.partner_country_code
                if self.type == 'import':
                    if not pline.product_country_origin_code:
                        raise Warning(
                            _('Missing product country of origin on line %d.')
                            % line)
                    country_origin.text = pline.product_country_origin_code
                if not pline.weight:
                    raise Warning(
                        _('Missing weight on line %d.') % line)
                weight.text = pline.weight

            # START of elements that are part of all DEBs
            invoiced_amount = etree.SubElement(item, 'invoicedAmount')
            if not pline.amount_company_currency:
                raise Warning(
                    _('Missing fiscal value on line %d.') % line)
            invoiced_amount.text = str(pline.amount_company_currency)
            # Partner VAT is only declared for export when code régime != 29
            if (
                    self.type == 'export'
                    and pline.intrastat_type_id.is_vat_required):
                partner_id = etree.SubElement(item, 'partnerId')
                if not pline.partner_vat:
                    raise Warning(
                        _("Missing VAT number on partner '%s'.")
                        % pline.partner_id.name)
                partner_id.text = pline.partner_vat.replace(' ', '')
            # Code régime is on all DEBs
            statistical_procedure_code = etree.SubElement(
                item, 'statisticalProcedureCode')
            statistical_procedure_code.text = pline.procedure_code

            # START of elements which are only required in "detailed" level
            if (
                    self.obligation_level == 'detailed'
                    and not intrastat_type.is_fiscal_only):
                transaction_nature = etree.SubElement(
                    item, 'NatureOfTransaction')
                transaction_nature_a = etree.SubElement(
                    transaction_nature, 'natureOfTransactionACode')
                transaction_nature_a.text = pline.transaction_code[0]
                transaction_nature_b = etree.SubElement(
                    transaction_nature, 'natureOfTransactionBCode')
                if len(pline.transaction_code) != 2:
                    raise Warning(
                        _('Transaction code on line %d should have 2 digits.')
                        % line)
                transaction_nature_b.text = pline.transaction_code[1]
                mode_of_transport_code = etree.SubElement(
                    item, 'modeOfTransportCode')
                if not pline.transport:
                    raise Warning(
                        _('Mode of transport is not set on line %d.') % line)
                mode_of_transport_code.text = str(pline.transport)
                region_code = etree.SubElement(item, 'regionCode')
                if not pline.department:
                    raise Warning(
                        _('Department code is not set on line %d.') % line)
                region_code.text = pline.department

        xml_string = etree.tostring(
            root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
        # We validate the XML file against the official XML Schema Definition
        # Because we may catch some problems with the content
        # of the XML file this way
        self._check_xml_schema(
            root, xml_string, 'l10n_fr_intrastat_product/data/deb.xsd')
        # Attach the XML file to the current object
        attach_id = self._attach_xml_file(xml_string, 'deb')
        return self._open_attach_view(attach_id, title="DEB XML file")

    @api.model
    def _scheduler_reminder(self):
        previous_month = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=-1), '%Y-%m')
        # I can't search on [('country_id', '=', ..)]
        # because it is a fields.function not stored and without fnct_search
        companies = self.env['res.company'].search([])
        logger.info('Starting the Intrastat Product reminder')
        for company in companies:
            if company.country_id.code != 'FR':
                continue
            for type in ['import', 'export']:
                if (
                        type == 'import'
                        and company.import_obligation_level == 'none'):
                    continue
                # Check if a declaration already exists for month N-1
                intrastats = self.search([
                    ('year_month', '=', previous_month),
                    ('type', '=', type),
                    ('company_id', '=', company.id)
                    ])
                if intrastats:
                    # if it already exists, we don't do anything
                    logger.info(
                        'An %s Intrastat Product for month %s already '
                        'exists for company %s'
                        % (type, previous_month, company.name))
                    continue
                else:
                    # If not, we create one for month N-1
                    obligation_level = eval(
                        'company.%s_obligation_level' % type)
                    if not obligation_level:
                        logger.warning(
                            "Missing obligation level for %s "
                            "on company '%s'." % (type, company.name))
                        continue
                    intrastat = self.create({
                        'company_id': company.id,
                        'type': type,
                        'obligation_level': obligation_level,
                        })
                    logger.info(
                        'An %s Intrastat Product for month %s '
                        'has been created by Odoo for company %s'
                        % (type, previous_month, company.name))
                    try:
                        intrastat.generate_product_lines_from_invoice()
                    except Warning as e:
                        intrastat = intrastat.with_context(
                            exception=True, error_msg=e)
                    # send the reminder e-mail
                    # TODO : how could we translate ${object.type}
                    # in the mail tpl ?
                    intrastat.send_reminder_email(
                        'l10n_fr_intrastat_product.'
                        'intrastat_product_reminder_email_template')
        return True


class L10nFrReportIntrastatProductLine(models.Model):
    _name = "l10n.fr.report.intrastat.product.line"
    _description = "Intrastat Product Lines for France"
    _order = 'id'

    parent_id = fields.Many2one(
        'l10n.fr.report.intrastat.product', string='Intrastat Product Ref',
        ondelete='cascade', readonly=True)
    company_id = fields.Many2one(
        'res.company', related='parent_id.company_id', string="Company",
        readonly=True)
    type = fields.Selection([
        ('import', 'Import'),
        ('export', 'Export'),
        ], related='parent_id.type', string="Type", readonly=True)
    company_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id',
        string="Company currency", readonly=True)
    invoice_id = fields.Many2one(
        'account.invoice', string='Invoice ref', readonly=True)
    quantity = fields.Char(string='Quantity', size=10)
    source_uom_id = fields.Many2one(
        'product.uom', string='Source UoM', readonly=True)
    intrastat_uom_id = fields.Many2one(
        'product.uom', string='Intrastat UoM')
    partner_country_id = fields.Many2one(
        'res.country', string='Partner Country')
    partner_country_code = fields.Char(
        related='partner_country_id.code', string='Partner Country Code',
        readonly=True)
    intrastat_code = fields.Char(string='Intrastat Code', size=9)
    intrastat_code_id = fields.Many2one(
        'report.intrastat.code', string='Intrastat Code (not used in XML)')
    # Weight should be an integer... but I want to be able to display
    # nothing in tree view when the value is False (if weight is an
    # integer, a False value would be displayed as 0), that's why weight
    # is a char !
    weight = fields.Char(string='Weight', size=10)
    amount_company_currency = fields.Integer(
        string='Fiscal value in company currency',
        required=True,
        help="Amount in company currency to write in the declaration. "
        "Amount in company currency = amount in invoice currency "
        "converted to company currency with the rate of the invoice date "
        "and rounded at 0 digits")
    amount_invoice_currency = fields.Float(
        string='Fiscal value in invoice currency',
        digits=dp.get_precision('Account'), readonly=True,
        help="Amount in invoice currency = amount of product value in "
        "invoice currency + amount of accessory cost in invoice currency "
        "(not rounded)")
    amount_accessory_cost_inv_cur = fields.Float(
        string='Amount of accessory costs in invoice currency',
        digits=dp.get_precision('Account'), readonly=True,
        help="Amount of accessory costs in invoice currency = total amount "
        "of accessory costs of the invoice broken down into each product "
        "line at the pro-rata of the value")
    amount_product_value_inv_cur = fields.Float(
        string='Amount of product value in invoice currency',
        digits=dp.get_precision('Account'), readonly=True,
        help="Amount of product value in invoice currency ; it is the "
        "amount of the invoice line or group of invoice lines.")
    invoice_currency_id = fields.Many2one(
        'res.currency', string="Invoice Currency", readonly=True)
    product_country_origin_id = fields.Many2one(
        'res.country', string='Product country of origin')
    # TODO rename product_origin_country_id
    product_country_origin_code = fields.Char(
        related='product_country_origin_id.code',
        string='Product Country of Origin', readonly=True)
    transport = fields.Selection([
        (1, '1. Transport maritime'),
        (2, '2. Transport par chemin de fer'),
        (3, '3. Transport par route'),
        (4, '4. Transport par air'),
        (5, '5. Envois postaux'),
        (7, '7. Installations de transport fixes'),
        (8, '8. Transport par navigation intérieure'),
        (9, '9. Propulsion propre')
        ], string='Type of transport')
    department = fields.Char(string='Department', size=2)
    intrastat_type_id = fields.Many2one(
        'report.intrastat.type', string='Intrastat Type', required=True)
    is_vat_required = fields.Boolean(
        related='intrastat_type_id.is_vat_required',
        string='Is Partner VAT required ?', readonly=True)
        # Is fiscal_only is not fields.related because,
        # if obligation_level = simplified, is_fiscal_only is always true
    is_fiscal_only = fields.Boolean(
        string='Is fiscal only?', readonly=True)
    procedure_code = fields.Char(
        string='Procedure Code', size=2)
    transaction_code = fields.Char(string='Transaction code', size=2)
    partner_vat = fields.Char(string='Partner VAT', size=32)
    partner_id = fields.Many2one('res.partner', string='Partner Name')

    @api.one
    @api.constrains('weight', 'quantity')
    def _check_intrastat_line(self):
        if self.weight and not self.weight.isdigit():
            raise ValidationError(_('Weight must be an integer.'))
        if self.quantity and not self.quantity.isdigit():
            raise ValidationError(_('Quantity must be an integer.'))

    # TODO
# constrains on 'procedure_code', 'transaction_code'

    @api.onchange('partner_id')
    def partner_on_change(self):
        if self.partner_id and self.partner_id.vat:
            self.partner_vat = self.partner_id.vat

    @api.onchange('intrastat_code_id')
    def intrastat_code_on_change(self):
        if self.intrastat_code_id:
            self.intrastat_code = self.intrastat_code_id.intrastat_code
            self.intrastat_uom_id =\
                self.intrastat_code_id.intrastat_uom_id.id or False
        else:
            self.intrastat_code = False
            self.intrastat_uom_id = False

    @api.onchange('intrastat_type_id')
    def intrastat_type_on_change(self):
        if self.parent_id.obligation_level == 'simplified':
            self.is_fiscal_only = True
        if self.intrastat_type_id:
            self.procedure_code = self.intrastat_type_id.procedure_code
            self.transaction_code = self.intrastat_type_id.transaction_code
            self.is_vat_required = self.intrastat_type_id.is_vat_required
            if self.parent_id.obligation_level == 'detailed':
                self.is_fiscal_only = self.intrastat_type_id.is_fiscal_only
        if self.is_fiscal_only:
            self.quantity = False
            self.source_uom_id = False
            self.intrastat_uom_id = False
            self.partner_country_id = False
            self.intrastat_code = False
            self.intrastat_code_id = False
            self.weight = False
            self.product_country_origin_id = False
            self.transport = False
            self.department = False

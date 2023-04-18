# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat product module for OpenERP
#    Copyright (C) 2009-2014 Akretion (http://www.akretion.com)
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
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
from lxml import etree

logger = logging.getLogger(__name__)


class report_intrastat_product(orm.Model):
    _name = "report.intrastat.product"
    _description = "Intrastat Product"
    _rec_name = "start_date"
    _inherit = ['mail.thread']
    _order = "start_date desc, type"
    _track = {
        'state': {
            'l10n_fr_intrastat_product.declaration_done': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'done',
            }
        }


    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({
            'start_date': datetime.strftime(datetime.today() + relativedelta(day=1, months=-1), '%Y-%m-%d'),
            'intrastat_line_ids': False,
            'state': 'draft',
        })
        return super(report_intrastat_product, self).copy(cr, uid, id, default=default, context=context)


    def _compute_numbers(self, cr, uid, ids, name, arg, context=None):
        return self.pool.get('report.intrastat.common')._compute_numbers(cr, uid, ids, self, context=context)

    def _compute_total_fiscal_amount(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for intrastat in self.browse(cr, uid, ids, context=context):
            total_fiscal_amount = 0.0
            for line in intrastat.intrastat_line_ids:
                total_fiscal_amount += line.amount_company_currency * line.intrastat_type_id.fiscal_value_multiplier
            result[intrastat.id] = total_fiscal_amount
        return result


    def _compute_dates(self, cr, uid, ids, name, arg, context=None):
        return self.pool.get('report.intrastat.common')._compute_dates(cr, uid, ids, self, context=context)

    def _get_intrastat_from_product_line(self, cr, uid, ids, context=None):
        return self.pool.get('report.intrastat.product').search(cr, uid, [('intrastat_line_ids', 'in', ids)], context=context)

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True,
            states={'done': [('readonly', True)]}, help="Related company."),
        'start_date': fields.date('Start date', required=True,
            states={'done': [('readonly', True)]},
            help="Start date of the declaration. Must be the first day of a month."),
        'end_date': fields.function(_compute_dates, type='date',
            string='End date', multi='intrastat-product-dates', readonly=True,
            store={
                'report.intrastat.product': (lambda self, cr, uid, ids, c={}: ids, ['start_date'], 10),
                },
            help="End date for the declaration. Is the last day of the month of the start date."),
        'year_month': fields.function(_compute_dates, type='char',
             string='Month', multi='intrastat-product-dates', readonly=True,
             track_visibility='always', store={
                'report.intrastat.product': (lambda self, cr, uid, ids, c={}: ids, ['start_date'], 10)
                },
            help="Year and month of the declaration."),
        'type': fields.selection([
                ('import', 'Import'),
                ('export', 'Export')
            ], 'Type', required=True, states={'done': [('readonly', True)]},
            track_visibility='always', help="Select the type of DEB."),
        'obligation_level': fields.selection([
                ('detailed', 'Detailed'),
                ('simplified', 'Simplified')
            ], 'Obligation level', required=True, track_visibility='always',
            states={'done': [('readonly', True)]},
            help="Your obligation level for a certain type of DEB (Import or Export) depends on the total value that you export or import per year. Note that the obligation level 'Simplified' doesn't exist for an Import DEB."),
        'intrastat_line_ids': fields.one2many('report.intrastat.product.line',
            'parent_id', 'Report intrastat product lines',
            states={'done': [('readonly', True)]}),
        'num_lines': fields.function(_compute_numbers, type='integer',
            multi='numbers', string='Number of lines', store={
                'report.intrastat.product.line': (_get_intrastat_from_product_line, ['parent_id'], 20),
            },
            track_visibility='always', help="Number of lines in this declaration."),
        'total_amount': fields.function(_compute_numbers,
            digits_compute=dp.get_precision('Account'), multi='numbers',
            string='Total amount', store={
                'report.intrastat.product.line': (_get_intrastat_from_product_line, ['amount_company_currency', 'parent_id'], 20),
            },
            help="Total amount in company currency of the declaration."),
        'total_fiscal_amount': fields.function(_compute_total_fiscal_amount,
            digits_compute=dp.get_precision('Account'),
            string='Total fiscal amount', track_visibility='always', store={
                'report.intrastat.product.line': (_get_intrastat_from_product_line, ['amount_company_currency', 'parent_id'], 20),
            },
            help="Total fiscal amount in company currency of the declaration. This is the total amount that is displayed on the Prodouane website."),
        'currency_id': fields.related('company_id', 'currency_id', readonly=True,
            type='many2one', relation='res.currency', string='Currency'),
        'state': fields.selection([
                ('draft', 'Draft'),
                ('done', 'Done'),
            ], 'State', readonly=True, track_visibility='onchange',
            help="State of the declaration. When the state is set to 'Done', the parameters become read-only."),
        # No more need for date_done, because chatter does the job
    }

    _defaults = {
        # By default, we propose 'current month -1', because you prepare in
        # February the DEB of January
        'start_date': lambda *a: datetime.strftime(datetime.today() + relativedelta(day=1, months=-1), '%Y-%m-%d'),
        'state': 'draft',
        'company_id': lambda self, cr, uid, context:
            self.pool['res.company']._company_default_get(cr, uid, 'report.intrastat.product', context=context),
    }


    def type_on_change(
            self, cr, uid, ids, company_id=False, type=False, context=None):
        result = {}
        result['value'] = {}
        if type and company_id:
            company = self.pool['res.company'].read(
                cr, uid, company_id,
                ['export_obligation_level', 'import_obligation_level'],
                context=context)
            if type == 'import':
                if company['import_obligation_level']:
                    if company['import_obligation_level'] == 'detailed':
                        result['value'].update({'obligation_level': company['import_obligation_level']})
                    elif company['import_obligation_level'] == 'none':
                        result['warning'] = {
                            'title': _("Warning on the Obligation Level"),
                            'message': _("You are tying to make an Intrastat Product of type 'Import', but the Import Obligation Level set for your company is 'None'. If this parameter on your company is correct, you should NOT create an Import Intrastat Product."),
                        }
            if type == 'export':
                if company['export_obligation_level']:
                    result['value'].update({'obligation_level': company['export_obligation_level']})
        return result

    def _check_start_date(self, cr, uid, ids):
        return self.pool.get('report.intrastat.common')._check_start_date(cr, uid, ids, self)

    def _check_obligation_level(self, cr, uid, ids):
        for intrastat_to_check in self.read(cr, uid, ids, ['type', 'obligation_level']):
            if intrastat_to_check['type'] == 'import' and intrastat_to_check['obligation_level'] == 'simplified':
                return False
        return True

    _constraints = [
        (_check_start_date, "Start date must be the first day of a month", ['start_date']),
        (_check_obligation_level, "Obligation level can't be 'Simplified' for Import", ['obligation_level']),
    ]

    _sql_constraints = [
        ('date_uniq', 'unique(start_date, company_id, type)', 'A DEB of the same type already exists for this month !'),
    ]

    def create_intrastat_product_lines(
            self, cr, uid, ids, intrastat, invoice, parent_values,
            context=None):
        """This function is called for each invoice"""
        assert len(ids) == 1, "Only one ID accepted"
        if context is None:
            context = {}
        line_obj = self.pool['report.intrastat.product.line']

        data_obj = self.pool['ir.model.data']
        uom_categ_model, weight_uom_categ_id = data_obj.get_object_reference(
            cr, uid, 'product', 'product_uom_categ_kgm')
        assert uom_categ_model == 'product.uom.categ', 'Wrong model uom categ'

        uom_model, kg_uom_id = data_obj.get_object_reference(
            cr, uid, 'product', 'product_uom_kgm')
        assert uom_model == 'product.uom', 'Wrong model uom'

        uom_categ_model, pce_uom_categ_id = data_obj.get_object_reference(
            cr, uid, 'product', 'product_uom_categ_unit')
        assert uom_categ_model == 'product.uom.categ', 'Wrong model uom categ'

        uom_model, pce_uom_id = data_obj.get_object_reference(
            cr, uid, 'product', 'product_uom_unit')
        assert uom_model == 'product.uom', 'Wrong model uom'

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
            if line.product_id.type not in ('product', 'consu') and not line.product_id.is_accessory_cost:
                continue

            skip_this_line = False
            for line_tax in line.invoice_line_tax_id:
                if line_tax.exclude_from_intrastat_if_present:
                    skip_this_line = True
            if skip_this_line:
                continue
            if line.product_id.is_accessory_cost and line.product_id.type == 'service':
                total_invoice_cur_accessory_cost += line.price_subtotal
                continue
            # END OF "continue" instructions
            ## AFTER THIS POINT, we are sure to have real products that have to be declared to DEB
            amount_product_value_inv_cur_to_write = line.price_subtotal
            total_invoice_cur_product_value += line.price_subtotal
            invoice_currency_id_to_write = invoice.currency_id.id

            if not parent_values['is_fiscal_only']:

                if not source_uom:
                    raise orm.except_orm(_('Error :'), _("Missing unit of measure on the line with %d product(s) '%s' on invoice '%s'.") % (line_qty, line.product_id.name, invoice.number))
                else:
                    source_uom_id_to_write = source_uom.id

                if source_uom.id == kg_uom_id:
                    weight_to_write = line_qty
                elif source_uom.category_id.id == weight_uom_categ_id:
                    dest_uom_kg = self.pool.get('product.uom').browse(cr, uid,
                        kg_uom_id, context=context)
                    weight_to_write = self.pool.get('product.uom')._compute_qty_obj(cr, uid,
                        source_uom, line_qty, dest_uom_kg, context=context)
                elif source_uom.category_id.id == pce_uom_categ_id:
                    if not line.product_id.weight_net:
                        raise orm.except_orm(_('Error :'), _("Missing net weight on product '%s'.") % (line.product_id.name))
                    if source_uom.id == pce_uom_id:
                        weight_to_write = line.product_id.weight_net * line_qty
                    else:
                        dest_uom_pce = self.pool.get('product.uom').browse(cr, uid,
                            pce_uom_id, context=context)
                        # Here, I suppose that, on the product, the weight is per PCE and not per uom_id
                        weight_to_write = line.product_id.weight_net * self.pool.get('product.uom')._compute_qty_obj(cr, uid, source_uom, line_qty, dest_uom_pce, context=context)

                else:
                    raise orm.except_orm(_('Error :'), _("Conversion from unit of measure '%s' to 'Kg' is not implemented yet.") % (source_uom.name))

                product_intrastat_code = line.product_id.intrastat_id
                if not product_intrastat_code:
                    # If the H.S. code is not set on the product, we check if it's set
                    # on it's related category
                    product_intrastat_code = line.product_id.categ_id.intrastat_id
                    if not product_intrastat_code:
                        raise orm.except_orm(_('Error :'), _("Missing H.S. code on product '%s' or on it's related category '%s'.") % (line.product_id.name, line.product_id.categ_id.complete_name))
                intrastat_code_id_to_write = product_intrastat_code.id

                if not product_intrastat_code.intrastat_code:
                    raise orm.except_orm(_('Error :'), _("Missing intrastat code on H.S. code '%s' (%s).") % (product_intrastat_code.name, product_intrastat_code.description))
                else:
                    intrastat_code_to_write = product_intrastat_code.intrastat_code

                if not product_intrastat_code.intrastat_uom_id:
                    intrastat_uom_id_to_write = False
                    quantity_to_write = False
                else:
                    intrastat_uom_id_to_write = product_intrastat_code.intrastat_uom_id.id
                    if intrastat_uom_id_to_write == source_uom_id_to_write:
                        quantity_to_write = line_qty
                    elif source_uom.category_id == product_intrastat_code.intrastat_uom_id.category_id:
                        quantity_to_write = self.pool.get('product.uom')._compute_qty_obj(cr,
                            uid, source_uom, line_qty,
                            product_intrastat_code.intrastat_uom_id, context=context)
                    else:
                        raise orm.except_orm(_('Error :'), _("On invoice '%s', the line with product '%s' has a unit of measure (%s) which can't be converted to UoM of it's intrastat code (%s).") % (invoice.number, line.product_id.name, source_uom_id_to_write, intrastat_uom_id_to_write))

                # The origin country should only be declated on Import
                if intrastat.type == 'export':
                    product_country_origin_id_to_write = False
                elif line.product_id.country_id:
                # If we have the country of origin on the product -> take it
                    product_country_origin_id_to_write = line.product_id.country_id.id
                else:
                    # If we don't, look on the product supplier info
                    origin_partner_id = parent_values.get('origin_partner_id', False)
                    if origin_partner_id:
                        supplieri_obj = self.pool.get('product.supplierinfo')
                        supplier_ids = supplieri_obj.search(cr, uid, [
                            ('name', '=', origin_partner_id),
                            ('product_id', '=', line.product_id.id),
                            ('origin_country_id', '!=', False)
                            ], context=context)
                        if not supplier_ids:
                            raise orm.except_orm(_('Error :'),
                                _("Missing country of origin on product '%s' or on it's supplier information for partner '%s'.")
                                % (line.product_id.name, parent_values.get('origin_partner_name', 'none')))
                        else:
                            product_country_origin_id_to_write = supplieri_obj.read(cr, uid,
                                supplier_ids[0], ['origin_country_id'],
                                context=context)['origin_country_id'][0]
                    else:
                        raise orm.except_orm(_('Error :'),
                            _("Missing country of origin on product '%s' (it's not possible to get the country of origin from the 'supplier information' in this case because we don't know the supplier of this product for the invoice '%s').")
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
                if line_to_create.get('intrastat_code_id', False) == intrastat_code_id_to_write \
                    and line_to_create.get('source_uom_id', False) == source_uom_id_to_write \
                    and line_to_create.get('intrastat_type_id', False) == parent_values['intrastat_type_id_to_write'] \
                    and line_to_create.get('product_country_origin_id', False) == product_country_origin_id_to_write:
                    create_new_line = False
                    line_to_create['quantity'] += quantity_to_write
                    line_to_create['weight'] += weight_to_write
                    line_to_create['amount_product_value_inv_cur'] += amount_product_value_inv_cur_to_write
                    break
            if create_new_line:
                lines_to_create.append({
                    'parent_id': ids[0],
                    'invoice_id': invoice.id,
                    'quantity': quantity_to_write,
                    'source_uom_id': source_uom_id_to_write,
                    'intrastat_uom_id': intrastat_uom_id_to_write,
                    'partner_country_id': parent_values['partner_country_id_to_write'],
                    'intrastat_code': intrastat_code_to_write,
                    'intrastat_code_id': intrastat_code_id_to_write,
                    'weight': weight_to_write,
                    'product_country_origin_id': product_country_origin_id_to_write,
                    'transport': parent_values['transport_to_write'],
                    'department': parent_values['department_to_write'],
                    'intrastat_type_id': parent_values['intrastat_type_id_to_write'],
                    'procedure_code': parent_values['procedure_code_to_write'],
                    'transaction_code': parent_values['transaction_code_to_write'],
                    'partner_id': parent_values['partner_id_to_write'],
                    'invoice_currency_id': invoice_currency_id_to_write,
                    'amount_product_value_inv_cur': amount_product_value_inv_cur_to_write,
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
                # If I have invoice.intrastat_country_id and the invoice partner
                # is outside the EU, then I look for the fiscal rep of the partner
                if invoice.intrastat_country_id and not invoice.partner_id.country_id.intrastat:
                    if not invoice.partner_id.intrastat_fiscal_representative:
                        raise orm.except_orm(_('Error :'), _("Missing fiscal representative for partner '%s'. It is required for invoice '%s' which has an invoice partner outside the EU but the goods were delivered to or received from inside the EU.") % (invoice.partner_id.name, invoice.number))
                    else:
                        parent_values['partner_vat_to_write'] = invoice.partner_id.intrastat_fiscal_representative.vat
                # Otherwise, I just read the vat number on the partner of the invoice
                else:

                    if not invoice.partner_id.vat:
                        raise orm.except_orm(_('Error :'), _("Missing VAT number on partner '%s'.") % invoice.partner_id.name)
                    else:
                        parent_values['partner_vat_to_write'] = invoice.partner_id.vat
            else:
                parent_values['partner_vat_to_write'] = False

        for line_to_create in lines_to_create:
            line_to_create['partner_vat'] = parent_values['partner_vat_to_write']

            if not total_invoice_cur_accessory_cost:
                line_to_create['amount_accessory_cost_inv_cur'] = 0
            else:
                if total_invoice_cur_product_value:
                    # The accessory costs are added at the pro-rata of value
                    line_to_create['amount_accessory_cost_inv_cur'] = total_invoice_cur_accessory_cost * line_to_create['amount_product_value_inv_cur'] / total_invoice_cur_product_value
                else:
                    # The accessory costs are added at the pro-rata of the number of lines
                    line_to_create['amount_accessory_cost_inv_cur'] = total_invoice_cur_accessory_cost / len(lines_to_create)

            line_to_create['amount_invoice_currency'] = line_to_create['amount_product_value_inv_cur'] + line_to_create['amount_accessory_cost_inv_cur']


            # We do currency conversion NOW
            if invoice.currency_id.name != 'EUR':
                # for currency conversion
                ctx_currency = context.copy()
                ctx_currency['date'] = invoice.date_invoice
                line_to_create['amount_company_currency'] = self.pool.get('res.currency').compute(cr, uid, invoice.currency_id.id, intrastat.company_id.currency_id.id, line_to_create['amount_invoice_currency'], context=ctx_currency)
            else:
                line_to_create['amount_company_currency'] = line_to_create['amount_invoice_currency']
            # We round
            line_to_create['amount_company_currency'] = int(round(line_to_create['amount_company_currency']))
            if line_to_create['amount_company_currency'] == 0:
                # p20 of the BOD : lines with value rounded to 0 mustn't be declared
                continue
            for value in ['quantity', 'weight']:  # These 2 fields are char
                if line_to_create[value]:
                    line_to_create[value] = str(int(round(line_to_create[value], 0)))
            line_obj.create(cr, uid, line_to_create, context=context)

        return True


    def compute_invoice_values(self, cr, uid, intrastat, invoice, parent_values, context=None):

        intrastat_type = self.pool.get('report.intrastat.type').read(cr, uid, parent_values['intrastat_type_id_to_write'], context=context)
        parent_values['procedure_code_to_write'] = intrastat_type['procedure_code']
        parent_values['transaction_code_to_write'] = intrastat_type['transaction_code']
        parent_values['is_fiscal_only'] = intrastat_type['is_fiscal_only']
        parent_values['is_vat_required'] = intrastat_type['is_vat_required']

        if intrastat.obligation_level == 'simplified':
            # force to is_fiscal_only
            parent_values['is_fiscal_only'] = True

        if not parent_values['is_fiscal_only']:
            if not invoice.intrastat_transport:
                if not intrastat.company_id.default_intrastat_transport:
                    raise orm.except_orm(_('Error :'), _("The mode of transport is not set on invoice '%s' nor the default mode of transport on the company '%s'.") % (invoice.number, intrastat.company_id.name))
                else:
                    parent_values['transport_to_write'] = intrastat.company_id.default_intrastat_transport
            else:
                parent_values['transport_to_write'] = invoice.intrastat_transport

            if not invoice.intrastat_department:
                if not intrastat.company_id.default_intrastat_department:
                    raise orm.except_orm(_('Error :'), _("The intrastat department hasn't been set on invoice '%s' and the default intrastat department is missing on the company '%s'.") % (invoice.number, intrastat.company_id.name))
                else:
                    parent_values['department_to_write'] = intrastat.company_id.default_intrastat_department
            else:
                parent_values['department_to_write'] = invoice.intrastat_department
        else:
            parent_values['department_to_write'] = False
            parent_values['transport_to_write'] = False
            parent_values['transaction_code_to_write'] = False
            parent_values['partner_country_id_to_write'] = False
        #print "parent_values =", parent_values
        return parent_values


    def generate_product_lines_from_invoice(self, cr, uid, ids, context=None):
        '''Function called by the button on form view'''
        #print "generate lines, ids=", ids
        assert len(ids) == 1, "Only one ID accepted"
        intrastat = self.browse(cr, uid, ids[0], context=context)
        self.pool.get('report.intrastat.common')._check_generate_lines(cr, uid, intrastat, context=context)
        line_obj = self.pool.get('report.intrastat.product.line')
        line_remove_ids = line_obj.search(cr, uid, [('parent_id', '=', ids[0]), ('invoice_id', '!=', False)], context=context)
        if line_remove_ids:
            line_obj.unlink(cr, uid, line_remove_ids, context=context)

        invoice_obj = self.pool.get('account.invoice')
        invoice_type = False
        if intrastat.type == 'import':
            # Les régularisations commerciales à l'HA ne sont PAS
            # déclarées dans la DEB, cf page 50 du BOD 6883 du 06 janvier 2011
            invoice_type = ('in_invoice', 'POUET')  # I need 'POUET' to make it a tuple
        if intrastat.type == 'export':
            invoice_type = ('out_invoice', 'out_refund')
        invoice_ids = invoice_obj.search(cr, uid, [
            ('type', 'in', invoice_type),
            ('date_invoice', '<=', intrastat.end_date),
            ('date_invoice', '>=', intrastat.start_date),
            ('state', 'in', ('open', 'paid')),
            ('company_id', '=', intrastat.company_id.id)
        ], order='date_invoice', context=context)
        #print "invoice_ids=", invoice_ids
        for invoice in invoice_obj.browse(cr, uid, invoice_ids, context=context):
            #print "INVOICE num =", invoice.number
            parent_values = {}

            # We should always have a country on partner_id
            if not invoice.partner_id.country_id:
                raise orm.except_orm(_('Error :'), _("Missing country on partner '%s'.") % invoice.partner_id.name)

            # If I have no invoice.intrastat_country_id, which is the case the first month
            # of the deployment of the module, then I use the country on invoice partner
            if not invoice.intrastat_country_id:
                if not invoice.partner_id.country_id.intrastat:
                    continue
                elif invoice.partner_id.country_id.id == intrastat.company_id.country_id.id:
                    continue
                else:
                    parent_values['partner_country_id_to_write'] = invoice.partner_id.country_id.id

            # If I have invoice.intrastat_country_id, which should be the case after the
            # first month of use of the module, then I use invoice.intrastat_country_id
            else:
                if not invoice.intrastat_country_id.intrastat:
                    continue
                elif invoice.intrastat_country_id.id == intrastat.company_id.country_id.id:
                    continue
                else:
                    parent_values['partner_country_id_to_write'] = invoice.intrastat_country_id.id
            if not invoice.intrastat_type_id:
                if invoice.type == 'out_invoice':
                    if intrastat.company_id.default_intrastat_type_out_invoice:
                        parent_values['intrastat_type_id_to_write'] = intrastat.company_id.default_intrastat_type_out_invoice.id
                    else:
                        raise orm.except_orm(_('Error :'), _("The intrastat type hasn't been set on invoice '%s' and the 'default intrastat type for customer invoice' is missing for the company '%s'.") % (invoice.number, intrastat.company_id.name))
                elif invoice.type == 'out_refund':
                    if intrastat.company_id.default_intrastat_type_out_refund:
                        parent_values['intrastat_type_id_to_write'] = intrastat.company_id.default_intrastat_type_out_refund.id
                    else:
                        raise orm.except_orm(_('Error :'), _("The intrastat type hasn't been set on refund '%s' and the 'default intrastat type for customer refund' is missing for the company '%s'.") % (invoice.number, intrastat.company_id.name))
                elif invoice.type == 'in_invoice':
                    if intrastat.company_id.default_intrastat_type_in_invoice:
                        parent_values['intrastat_type_id_to_write'] = intrastat.company_id.default_intrastat_type_in_invoice.id
                    else:
                        raise orm.except_orm(_('Error :'), _("The intrastat type hasn't been set on invoice '%s' and the 'Default intrastat type for supplier invoice' is missing for the company '%s'.") % (invoice.number, intrastat.company_id.name))
                else:
                    raise orm.except_orm(_('Error :'), "Hara kiri... we can't have a supplier refund")

            else:
                parent_values['intrastat_type_id_to_write'] = invoice.intrastat_type_id.id

            if invoice.intrastat_country_id and not invoice.partner_id.country_id.intrastat and invoice.partner_id.intrastat_fiscal_representative:
                # fiscal rep
                parent_values['partner_id_to_write'] = invoice.partner_id.intrastat_fiscal_representative.id
            else:
                parent_values['partner_id_to_write'] = invoice.partner_id.id

            # Get partner on which we will check the 'country of origin' on product_supplierinfo
            parent_values['origin_partner_id'] = invoice.partner_id.id
            parent_values['origin_partner_name'] = invoice.partner_id.name

            parent_values = self.compute_invoice_values(cr, uid, intrastat, invoice, parent_values, context=context)

            self.create_intrastat_product_lines(cr, uid, ids, intrastat, invoice, parent_values, context=context)

        return True


    def done(self, cr, uid, ids, context=None):
        assert len(ids) == 1, "Only one ID accepted"
        self.write(cr, uid, ids[0], {'state': 'done'}, context=context)
        return True

    def back2draft(self, cr, uid, ids, context=None):
        assert len(ids) == 1, "Only one ID accepted"
        self.write(cr, uid, ids[0], {'state': 'draft'}, context=context)
        return True


    def generate_xml(self, cr, uid, ids, context=None):
        '''Generate the INSTAT XML file export.'''
        intrastat = self.browse(cr, uid, ids[0], context=context)
        start_date_str = intrastat.start_date
        end_date_str = intrastat.end_date
        start_date_datetime = datetime.strptime(start_date_str, '%Y-%m-%d')

        self.pool.get('report.intrastat.common')._check_generate_xml(cr, uid, intrastat, context=context)

        my_company_vat = intrastat.company_id.partner_id.vat.replace(' ', '')

        if not intrastat.company_id.siret:
            raise orm.except_orm(
                _('Error :'),
                _("The SIRET is not set on company '%s'.")
                    % intrastat.company_id.name)
        my_company_id = my_company_vat + intrastat.company_id.siret[9:]

        my_company_currency = intrastat.company_id.currency_id.name

        root = etree.Element('INSTAT')
        envelope = etree.SubElement(root, 'Envelope')
        envelope_id = etree.SubElement(envelope, 'envelopeId')
        try: envelope_id.text = intrastat.company_id.customs_accreditation
        except: raise orm.except_orm(_('Error :'), _("The customs accreditation identifier is not set for the company '%s'.") % intrastat.company_id.name)
        create_date_time = etree.SubElement(envelope, 'DateTime')
        create_date = etree.SubElement(create_date_time, 'date')
        create_date.text = datetime.strftime(datetime.today(), '%Y-%m-%d')
        create_time = etree.SubElement(create_date_time, 'time')
        create_time.text = datetime.strftime(datetime.today(), '%H:%M:%S')
        party = etree.SubElement(envelope, 'Party', partyType="PSI", partyRole="PSI")
        party_id = etree.SubElement(party, 'partyId')
        party_id.text = my_company_id
        party_name = etree.SubElement(party, 'partyName')
        party_name.text = intrastat.company_id.name
        software_used = etree.SubElement(envelope, 'softwareUsed')
        software_used.text = 'OpenERP'
        declaration = etree.SubElement(envelope, 'Declaration')
        declaration_id = etree.SubElement(declaration, 'declarationId')
        declaration_id.text = datetime.strftime(start_date_datetime, '%Y%m')  # 6 digits
        reference_period = etree.SubElement(declaration, 'referencePeriod')
        reference_period.text = datetime.strftime(start_date_datetime, '%Y-%m')
        psi_id = etree.SubElement(declaration, 'PSIId')
        psi_id.text = my_company_id
        function = etree.SubElement(declaration, 'Function')
        function_code = etree.SubElement(function, 'functionCode')
        function_code.text = 'O'
        declaration_type_code = etree.SubElement(declaration, 'declarationTypeCode')
        if intrastat.obligation_level == 'detailed':
            declaration_type_code.text = '1'
        elif intrastat.obligation_level == 'simplified':
            declaration_type_code.text = '4'
        else:
            raise orm.except_orm(_('Error :'), "The obligation level for DEB should be 'simplified' or 'detailed'.")
        flow_code = etree.SubElement(declaration, 'flowCode')

        if intrastat.type == 'export':
            flow_code.text = 'D'
        elif intrastat.type == 'import':
            flow_code.text = 'A'
        else:
            raise orm.except_orm(_('Error :'), "The DEB must be of type 'Import' or 'Export'")
        currency_code = etree.SubElement(declaration, 'currencyCode')
        if my_company_currency == 'EUR': # already tested in generate_lines function !
            currency_code.text = my_company_currency
        else:
            raise orm.except_orm(_('Error :'), "Company currency must be 'EUR' but is currently '%s'." % my_company_currency)

        # THEN, the fields which vary from a line to the next
        line = 0
        for pline in intrastat.intrastat_line_ids:
            line += 1  # increment line number
            #print "line =", line
            try: intrastat_type = self.pool.get('report.intrastat.type').read(cr, uid, pline.intrastat_type_id.id, ['is_fiscal_only'], context=context)
            except: raise orm.except_orm(_('Error :'), "Missing Intrastat type id on line %d." %line)
            item = etree.SubElement(declaration, 'Item')
            item_number = etree.SubElement(item, 'itemNumber')
            item_number.text = str(line)
            # START of elements which are only required in "detailed" level
            if intrastat.obligation_level == 'detailed' and not intrastat_type['is_fiscal_only']:
                cn8 = etree.SubElement(item, 'CN8')
                cn8_code = etree.SubElement(cn8, 'CN8Code')
                try: cn8_code.text = pline.intrastat_code
                except: raise orm.except_orm(_('Error :'), _('Missing Intrastat code on line %d.') % line)
                # We fill SUCode only if the H.S. code requires it
                if pline.intrastat_uom_id:
                    su_code = etree.SubElement(cn8, 'SUCode')
                    try: su_code.text = pline.intrastat_uom_id.intrastat_label
                    except: raise orm.except_orm(_('Error :'), _('Missing Intrastat UoM on line %d.') % line)
                    destination_country = etree.SubElement(item, 'MSConsDestCode')
                    if intrastat.type == 'import': country_origin = etree.SubElement(item, 'countryOfOriginCode')
                    weight = etree.SubElement(item, 'netMass')
                    quantity_in_SU = etree.SubElement(item, 'quantityInSU')

                    try: quantity_in_SU.text = pline.quantity
                    except: raise orm.except_orm(_('Error :'), _('Missing quantity on line %d.') % line)
                else:
                    destination_country = etree.SubElement(item, 'MSConsDestCode')
                    if intrastat.type == 'import': country_origin = etree.SubElement(item, 'countryOfOriginCode')
                    weight = etree.SubElement(item, 'netMass')
                try: destination_country.text = pline.partner_country_code
                except: raise orm.except_orm(_('Error :'), _('Missing partner country on line %d.') % line)
                if intrastat.type == 'import':
                    try: country_origin.text = pline.product_country_origin_code
                    except: raise orm.except_orm(_('Error :'), _('Missing product country of origin on line %d.') % line)
                try: weight.text = pline.weight
                except: raise orm.except_orm(_('Error :'), _('Missing weight on line %d.') % line)

            # START of elements that are part of all DEBs
            invoiced_amount = etree.SubElement(item, 'invoicedAmount')
            try:
                invoiced_amount.text = str(pline.amount_company_currency)
            except: raise orm.except_orm(_('Error :'), _('Missing fiscal value on line %d.') % line)
            # Partner VAT is only declared for export when code régime != 29
            if intrastat.type == 'export' and pline.intrastat_type_id.is_vat_required:
                partner_id = etree.SubElement(item, 'partnerId')
                try: partner_id.text = pline.partner_vat.replace(' ', '')
                except: raise orm.except_orm(_('Error :'), _("Missing VAT number for partner '%s'.") % pline.partner_id.name)
            # Code régime is on all DEBs
            statistical_procedure_code = etree.SubElement(item, 'statisticalProcedureCode')
            statistical_procedure_code.text = pline.procedure_code

            # START of elements which are only required in "detailed" level
            if intrastat.obligation_level == 'detailed' and not intrastat_type['is_fiscal_only']:
                transaction_nature = etree.SubElement(item, 'NatureOfTransaction')
                transaction_nature_a = etree.SubElement(transaction_nature, 'natureOfTransactionACode')
                transaction_nature_a.text = pline.transaction_code[0] # str(integer)[0] always have a value, so it should never crash here -> no try/except
                transaction_nature_b = etree.SubElement(transaction_nature, 'natureOfTransactionBCode')
                try: transaction_nature_b.text = pline.transaction_code[1]
                except: raise orm.except_orm(_('Error :'), _('Transaction code on line %d should have 2 digits.') % line)
                mode_of_transport_code = etree.SubElement(item, 'modeOfTransportCode')
                # I can't do a try/except as usual, because field.text = str(integer)
                # will always work, even if integer is False
                if not pline.transport:
                    raise orm.except_orm(_('Error :'), _('Mode of transport is not set on line %d.') % line)
                else:
                    mode_of_transport_code.text = str(pline.transport)
                region_code = etree.SubElement(item, 'regionCode')
                try: region_code.text = pline.department
                except: raise orm.except_orm(_('Error :'), _('Department code is not set on line %d.') % line)

        xml_string = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
        # We now validate the XML file against the official XML Schema Definition
        # Because we may catch some problems with the content of the XML file this way
        self.pool.get('report.intrastat.common')._check_xml_schema(cr, uid, root, xml_string, 'l10n_fr_intrastat_product/data/deb.xsd', context=context)
        # Attach the XML file to the current object
        attach_id = self.pool.get('report.intrastat.common')._attach_xml_file(cr, uid, ids, self, xml_string, start_date_datetime, 'deb', context=context)
        return self.pool.get('report.intrastat.common')._open_attach_view(cr, uid, attach_id, title="DEB XML file", context=context)


    def _scheduler_reminder(self, cr, uid, context=None):
        if context is None:
            context = {}
        previous_month = datetime.strftime(datetime.today() + relativedelta(day=1, months=-1), '%Y-%m')
        # I can't search on [('country_id', '=', ..)]
        # because it is a fields.function not stored and without fnct_search
        company_ids = self.pool['res.company'].search(
            cr, uid, [], context=context)
        logger.info('Starting the Intrastat Product reminder')
        for company in self.pool['res.company'].browse(cr, uid, company_ids, context=None):
            if company.country_id.code != 'FR':
                continue
            for type in ['import', 'export']:
                if type == 'import' and company.import_obligation_level == 'none':
                    continue
                # Check if a declaration already exists for month N-1
                intrastat_ids = self.search(cr, uid, [('year_month', '=', previous_month), ('type', '=', type), ('company_id', '=', company.id)], context=context)
                if intrastat_ids:
                    # if it already exists, we don't do anything
                    logger.info('An %s Intrastat Product for month %s already exists for company %s' % (type, previous_month, company.name))
                    continue
                else:
                    # If not, we create one for month N-1
                    obligation_level = eval('company.%s_obligation_level' % type)
                    if not obligation_level:
                        logger.warning("Missing obligation level for %s on company '%s'." % (type, company.name))
                        continue
                    intrastat_id = self.create(cr, uid, {
                        'company_id': company.id,
                        'type': type,
                        'obligation_level': obligation_level,
                        }, context=context)
                    logger.info('An %s Intrastat Product for month %s has been created by OpenERP for company %s' % (type, previous_month, company.name))
                    try:
                        self.generate_product_lines_from_invoice(cr, uid, [intrastat_id], context=context)
                    except orm.except_orm as e:
                        context['exception'] = True
                        context['error_msg'] = e[1]

                    # send the reminder e-mail
                    # TODO : how could we translate ${object.type} in the mail tpl ?
                    self.pool['report.intrastat.common'].send_reminder_email(cr, uid, company, 'l10n_fr_intrastat_product', 'intrastat_product_reminder_email_template', intrastat_id, context=context)
        return True


class report_intrastat_product_line(orm.Model):
    _name = "report.intrastat.product.line"
    _description = "Intrastat Product Lines"
    _order = 'id'

    _columns = {
        'parent_id': fields.many2one('report.intrastat.product', 'Intrastat product ref', ondelete='cascade', readonly=True),
        'company_id': fields.related('parent_id', 'company_id', type='many2one', relation='res.company', string="Company", readonly=True),
        'type': fields.related('parent_id', 'type', type='char', string="Type", readonly=True),
        'company_currency_id': fields.related('company_id', 'currency_id', type='many2one', relation='res.currency', string="Company currency", readonly=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice ref', readonly=True),
        'quantity': fields.char('Quantity', size=10),
        'source_uom_id': fields.many2one('product.uom', 'Source UoM', readonly=True),
        'intrastat_uom_id': fields.many2one('product.uom', 'Intrastat UoM'),
        'partner_country_id': fields.many2one('res.country', 'Partner country'),
        'partner_country_code': fields.related('partner_country_id', 'code', type='string', relation='res.country', string='Partner country', readonly=True),
        'intrastat_code': fields.char('Intrastat code', size=9),
        'intrastat_code_id': fields.many2one('report.intrastat.code', 'Intrastat code (not used in XML)'),
        # Weight should be an integer... but I want to be able to display nothing in
        # tree view when the value is False (if weight is an integer, a False value would
        # be displayed as 0), that's why weight is a char !
        'weight': fields.char('Weight', size=10),
        'amount_company_currency': fields.integer('Fiscal value in company currency',
            required=True,
            help="Amount in company currency to write in the declaration. Amount in company currency = amount in invoice currency converted to company currency with the rate of the invoice date and rounded at 0 digits"),
        'amount_invoice_currency': fields.float('Fiscal value in invoice currency',
            digits_compute=dp.get_precision('Account'), readonly=True,
            help="Amount in invoice currency = amount of product value in invoice currency + amount of accessory cost in invoice currency (not rounded)"),
        'amount_accessory_cost_inv_cur': fields.float(
            'Amount of accessory costs in invoice currency',
            digits_compute=dp.get_precision('Account'), readonly=True,
            help="Amount of accessory costs in invoice currency = total amount of accessory costs of the invoice broken down into each product line at the pro-rata of the value"),
        'amount_product_value_inv_cur': fields.float(
            'Amount of product value in invoice currency',
            digits_compute=dp.get_precision('Account'), readonly=True,
            help="Amount of product value in invoice currency ; it is the amount of the invoice line or group of invoice lines."),
        'invoice_currency_id': fields.many2one('res.currency', "Invoice currency", readonly=True),
        'product_country_origin_id': fields.many2one('res.country', 'Product country of origin'),
        'product_country_origin_code': fields.related('product_country_origin_id', 'code', type='string', relation='res.country', string='Product country of origin', readonly=True),
        'transport': fields.selection([
            (1, '1. Transport maritime'),
            (2, '2. Transport par chemin de fer'),
            (3, '3. Transport par route'),
            (4, '4. Transport par air'),
            (5, '5. Envois postaux'),
            (7, '7. Installations de transport fixes'),
            (8, '8. Transport par navigation intérieure'),
            (9, '9. Propulsion propre')
            ], 'Type of transport'),
        'department': fields.char('Department', size=2),
        'intrastat_type_id': fields.many2one('report.intrastat.type', 'Intrastat type'),
        'is_vat_required': fields.related('intrastat_type_id', 'is_vat_required', type='boolean', relation='report.intrastat.type', string='Is Partner VAT required ?', readonly=True),
        # Is fiscal_only is not fields.related because, if obligation_level = simplified, is_fiscal_only is always true
        'is_fiscal_only': fields.boolean('Is fiscal only?', readonly=True),
        'procedure_code': fields.char('Procedure code', size=2),
        'transaction_code': fields.char('Transaction code', size=2),
        'partner_vat': fields.char('Partner VAT', size=32),
        'partner_id': fields.many2one('res.partner', 'Partner name'),
    }

    def _integer_check(self, cr, uid, ids):
        for values in self.read(cr, uid, ids, ['weight', 'quantity']):
            if values['weight'] and not values['weight'].isdigit():
                raise orm.except_orm(_('Error :'), _('Weight must be an integer.'))
            if values['quantity'] and not values['quantity'].isdigit():
                raise orm.except_orm(_('Error :'), _('Quantity must be an integer.'))
        return True

    def _code_check(self, cr, uid, ids):
        for lines in self.read(cr, uid, ids, ['procedure_code', 'transaction_code']):
            self.pool.get('report.intrastat.type').real_code_check(lines)
        return True

    _constraints = [
        (_code_check, "Error msg in raise", ['procedure_code', 'transaction_code']),
        (_integer_check, "Error msg in raise", ['weight', 'quantity']),
    ]

    def partner_on_change(self, cr, uid, ids, partner_id=False, context=None):
        return self.pool['report.intrastat.common'].partner_on_change(
            cr, uid, ids, partner_id, context=context)

    def intrastat_code_on_change(
            self, cr, uid, ids, intrastat_code_id=False, context=None):
        result = {}
        result['value'] = {}
        if intrastat_code_id:
            intrastat_code = self.pool['report.intrastat.code'].browse(
                cr, uid, intrastat_code_id, context=context)
            if intrastat_code.intrastat_uom_id:
                result['value'].update({
                    'intrastat_code': intrastat_code.intrastat_code,
                    'intrastat_uom_id': intrastat_code.intrastat_uom_id.id,
                    })
            else:
                result['value'].update({
                    'intrastat_code': intrastat_code.intrastat_code,
                    'intrastat_uom_id': False,
                    })
        return result

    def intrastat_type_on_change(
            self, cr, uid, ids, intrastat_type_id=False, type=False,
            obligation_level=False, context=None):
        result = {}
        result['value'] = {}
        if obligation_level == 'simplified':
            result['value'].update({'is_fiscal_only': True})
        if intrastat_type_id:
            intrastat_type = self.pool['report.intrastat.type'].read(
                cr, uid, intrastat_type_id, [
                    'procedure_code', 'transaction_code',
                    'is_fiscal_only', 'is_vat_required',
                    ], context=context)
            result['value'].update({'procedure_code': intrastat_type['procedure_code'], 'transaction_code': intrastat_type['transaction_code'], 'is_vat_required': intrastat_type['is_vat_required']})
            if obligation_level == 'detailed':
                result['value'].update({'is_fiscal_only': intrastat_type['is_fiscal_only']})

        if result['value'].get('is_fiscal_only', False):
            result['value'].update({
                'quantity': False,
                'source_uom_id': False,
                'intrastat_uom_id': False,
                'partner_country_id': False,
                'intrastat_code': False,
                'intrastat_code_id': False,
                'weight': False,
                'product_country_origin_id': False,
                'transport': False,
                'department': False
            })
        return result

# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat product module for OpenERP
#    Copyright (C) 2009-2012 Akretion (http://www.akretion.com). All Rights Reserved.
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

from osv import osv, fields
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tools.translate import _
import decimal_precision as dp

class report_intrastat_product(osv.osv):
    _name = "report.intrastat.product"
    _description = "Intrastat report for products"
    _rec_name = "start_date"
    _order = "start_date desc, type"


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


    def _compute_end_date(self, cr, uid, ids, name, arg, context=None):
        return self.pool.get('report.intrastat.common')._compute_end_date(cr, uid, ids, self, context=context)

    def _get_intrastat_from_product_line(self, cr, uid, ids, context=None):
        return self.pool.get('report.intrastat.product').search(cr, uid, [('intrastat_line_ids', 'in', ids)], context=context)

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True,
            states={'done':[('readonly',True)]}, help="Related company."),
        'start_date': fields.date('Start date', required=True,
            states={'done':[('readonly',True)]},
            help="Start date of the declaration. Must be the first day of a month."),
        'end_date': fields.function(_compute_end_date, method=True, type='date',
            string='End date', store={
                'report.intrastat.product': (lambda self, cr, uid, ids, c={}: ids, ['start_date'], 10),
                },
            help="End date for the declaration. Is the last day of the month of the start date."),
        'type': fields.selection([
                ('import', 'Import'),
                ('export', 'Export')
            ], 'Type', required=True, states={'done':[('readonly',True)]},
            help="Select the type of DEB."),
        'obligation_level' : fields.selection([
                ('detailed', 'Detailed'),
                ('simplified', 'Simplified')
            ], 'Obligation level', required=True,
            states={'done':[('readonly',True)]},
            help="Your obligation level for a certain type of DEB (Import or Export) depends on the total value that you export or import per year. Note that the obligation level 'Simplified' doesn't exist for an Import DEB."),
        'intrastat_line_ids': fields.one2many('report.intrastat.product.line',
            'parent_id', 'Report intrastat product lines',
            states={'done':[('readonly',True)]}),
        'num_lines': fields.function(_compute_numbers, method=True, type='integer',
            multi='numbers', string='Number of lines', store={
                'report.intrastat.product.line': (_get_intrastat_from_product_line, ['parent_id'], 20),
            },
            help="Number of lines in this declaration."),
        'total_amount': fields.function(_compute_numbers, method=True,
            digits_compute=dp.get_precision('Account'), multi='numbers',
            string='Total amount', store={
                'report.intrastat.product.line': (_get_intrastat_from_product_line, ['amount_company_currency', 'parent_id'], 20),
            },
            help="Total amount in company currency of the declaration."),
        'total_fiscal_amount': fields.function(_compute_total_fiscal_amount,
            method=True, digits_compute=dp.get_precision('Account'),
            string='Total fiscal amount', store={
                'report.intrastat.product.line': (_get_intrastat_from_product_line, ['amount_company_currency', 'parent_id'], 20),
            },
            help="Total fiscal amount in company currency of the declaration. This is the total amount that is displayed on the Prodouane website."),
        'currency_id': fields.related('company_id', 'currency_id', readonly=True,
            type='many2one', relation='res.currency', string='Currency'),
        'state' : fields.selection([
                ('draft','Draft'),
                ('done','Done'),
            ], 'State', select=True, readonly=True,
            help="State of the declaration. When the state is set to 'Done', the parameters become read-only."),
        'date_done' : fields.datetime('Date done', readonly=True,
            help="Last date when the intrastat declaration was converted to 'Done' state."),
        'notes' : fields.text('Notes',
            help="You can add some comments here if you want."),
    }

    _defaults = {
        # By default, we propose 'current month -1', because you prepare in
        # February the DEB of January
        'start_date': lambda *a: datetime.strftime(datetime.today() + relativedelta(day=1, months=-1), '%Y-%m-%d'),
        'state': 'draft',
        'company_id': lambda self, cr, uid, context: \
        self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id,
    }


    def type_on_change(self, cr, uid, ids, company_id=False, type=False):
        result = {}
        result['value'] = {}
        if type and company_id:
            if type == 'import': # The only level possible for DEB import is detailed
                result['value'].update({'obligation_level': 'detailed'})
            if type == 'export':
                company = self.pool.get('res.company').read(cr, uid, company_id, ['export_obligation_level'])
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

    def _get_id_from_xmlid(self, cr, uid, module, xml_id, model_name, context=None):
        irdata_obj = self.pool.get('ir.model.data')
        res = irdata_obj.get_object_reference(cr, uid, module, xml_id)
        if res[0] == model_name:
            res_id = res[1]
        else:
            raise osv.except_osv(_('Error :'), 'Hara kiri %s in _get_id_from_xmlid' % xml_id)
        return res_id

    def create_intrastat_product_lines(self, cr, uid, ids, intrastat, parent_obj, parent_values, context=None):
        """This function is called for each invoice and for each picking"""
        #print "create_intrastat_product_line ids=", ids

        if len(ids) != 1: raise osv.except_osv(_('Error :'), 'Hara kiri in build_intrastat_product_line')
        line_obj = self.pool.get('report.intrastat.product.line')

        weight_uom_categ_id = self._get_id_from_xmlid(cr, uid, 'product', 'product_uom_categ_kgm', 'product.uom.categ', context=context)

        kg_uom_id = self._get_id_from_xmlid(cr, uid, 'product', 'product_uom_kgm', 'product.uom', context=context)

        pce_uom_categ_id = self._get_id_from_xmlid(cr, uid, 'product', 'product_uom_categ_unit', 'product.uom.categ', context=context)

        pce_uom_id = self._get_id_from_xmlid(cr, uid, 'product', 'product_uom_unit', 'product.uom', context=context)

        if parent_obj._name == 'account.invoice':
            src = 'invoice'
            browse_on = parent_obj.invoice_line
            parent_name = parent_obj.number
            product_line_ref_field = 'invoice_id'
            currency_obj = parent_obj.currency_id
        elif parent_obj._name == 'stock.picking':
            src = 'picking'
            browse_on = parent_obj.move_lines
            parent_name = parent_obj.name
            product_line_ref_field = 'picking_id'
            currency_obj = intrastat.company_id.statistical_pricelist_id.currency_id
        else: raise osv.except_osv(_('Error :'), 'The function build_intrastat_product_lines() should have parent_obj as invoice or picking')

        lines_to_create = []
        total_invoice_cur_accessory_cost = 0.0
        total_invoice_cur_product_value = 0.0
        for line in browse_on:
            if src == 'invoice':
                line_qty = line.quantity
                source_uom = line.uos_id
            elif src == 'picking':
                line_qty = line.product_qty
                source_uom = line.product_uom

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

            if src == 'picking':
                if line.state <> 'done':
                    continue
                if parent_obj.type == 'in' and line.location_dest_id.usage <> 'internal':
                    continue
                if parent_obj.type == 'out' and line.location_dest_id.usage == 'internal':
                    continue

            if src == 'invoice':
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
                invoice_currency_id_to_write = currency_obj.id

            elif src == 'picking':
                invoice_currency_id_to_write = currency_obj.id
                unit_stat_price = self.pool.get('product.pricelist').price_get(cr, uid, [intrastat.company_id.statistical_pricelist_id.id], line.product_id.id, 1.0)[intrastat.company_id.statistical_pricelist_id.id]
                if not unit_stat_price:
                    raise osv.except_osv(_('Error :'), _("The Pricelist for statistical value '%s' that is set for the company '%s' gives a price of 0 for the product '%s'.") %(intrastat.company_id.statistical_pricelist_id.name, intrastat.company_id.name, line.product_id.name))
                else:
                    amount_product_value_inv_cur_to_write = unit_stat_price * line_qty

            if not parent_values['is_fiscal_only']:

                if not source_uom:
                    raise osv.except_osv(_('Error :'), _("Missing unit of measure on the line with %d product(s) '%s' on %s '%s'.") %(line_qty, line.product_id.name, src, parent_name))
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
                        raise osv.except_osv(_('Error :'), _("Missing net weight on product '%s'.") %(line.product_id.name))
                    if source_uom.id == pce_uom_id:
                        weight_to_write = line.product_id.weight_net * line_qty
                    else:
                        dest_uom_pce = self.pool.get('product.uom').browse(cr, uid,
                            pce_uom_id, context=context)
                        # Here, I suppose that, on the product, the weight is per PCE and not per uom_id
                        weight_to_write = line.product_id.weight_net * self.pool.get('product.uom')._compute_qty_obj(cr, uid, source_uom, line_qty, dest_uom_pce, context=context)

                else:
                    raise osv.except_osv(_('Error :'), _("Conversion from unit of measure '%s' to 'Kg' is not implemented yet.") %(source_uom.name))

                product_intrastat_code = line.product_id.intrastat_id
                if not product_intrastat_code:
                    # If the H.S. code is not set on the product, we check if it's set
                    # on it's related category
                    product_intrastat_code = line.product_id.categ_id.intrastat_id
                    if not product_intrastat_code:
                        raise osv.except_osv(_('Error :'), _("Missing H.S. code on product '%s' or on it's related category '%s'.") %(line.product_id.name, line.product_id.categ_id.complete_name))
                intrastat_code_id_to_write = product_intrastat_code.id

                if not product_intrastat_code.intrastat_code:
                    raise osv.except_osv(_('Error :'), _("Missing intrastat code on H.S. code '%s' (%s).") %(product_intrastat_code.name, product_intrastat_code.description))
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
                        raise osv.except_osv(_('Error :'), _("On %s '%s', the line with product '%s' has a unit of measure (%s) which can't be converted to UoM of it's intrastat code (%s).") %(src, parent_name, line.product_id.name, source_uom_id_to_write, intrastat_uom_id_to_write))

                # The origin country should only be declated on Import
                if intrastat.type == 'export':
                    product_country_origin_id_to_write = False
                elif line.product_id.country_id:
                # If we have the country of origin on the product -> take it
                    product_country_origin_id_to_write = line.product_id.country_id.id
                else:
                    # If we don't, look on the product supplier info
                    # We only have parent_values['origin_partner_id'] when src = invoice
                    origin_partner_id = parent_values.get('origin_partner_id', False)
                    if origin_partner_id:
                        supplieri_obj = self.pool.get('product.supplierinfo')
                        supplier_ids = supplieri_obj.search(cr, uid, [
                            ('name', '=', origin_partner_id),
                            ('product_id', '=', line.product_id.id),
                            ('origin_country_id', '!=', 'null')
                            ], context=context)
                        if not supplier_ids:
                            raise osv.except_osv(_('Error :'),
                                _("Missing country of origin on product '%s' or on it's supplier information for partner '%s'.")
                                %(line.product_id.name, parent_values.get('origin_partner_name', 'none')))
                        else:
                            product_country_origin_id_to_write = supplieri_obj.read(cr, uid,
                                supplier_ids[0], ['origin_country_id'],
                                context=context)['origin_country_id'][0]
                    else:
                        raise osv.except_osv(_('Error :'),
                            _("Missing country of origin on product '%s' (it's not possible to get the country of origin from the 'supplier information' in this case because we don't know the supplier of this product for the %s '%s').")
                            %(line.product_id.name, src, parent_name))

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
#                    line_to_create['amount_company_currency'] += amount_company_currency_to_write
                    line_to_create['weight'] += weight_to_write
#                    line_to_create['amount_invoice_currency'] += amount_invoice_currency_to_write
                    line_to_create['amount_product_value_inv_cur'] += amount_product_value_inv_cur_to_write
                    break
            if create_new_line == True:
                lines_to_create.append({
                    'parent_id': ids[0],
                    product_line_ref_field: parent_obj.id,
                    'quantity': quantity_to_write,
                    'source_uom_id': source_uom_id_to_write,
                    'intrastat_uom_id': intrastat_uom_id_to_write,
                    'partner_country_id': parent_values['partner_country_id_to_write'],
                    'intrastat_code': intrastat_code_to_write,
                    'intrastat_code_id': intrastat_code_id_to_write,
                    'weight': weight_to_write,
#                    'amount_company_currency': amount_company_currency_to_write,
                    'product_country_origin_id': product_country_origin_id_to_write,
                    'transport': parent_values['transport_to_write'],
                    'department': parent_values['department_to_write'],
                    'intrastat_type_id': parent_values['intrastat_type_id_to_write'],
                    'procedure_code': parent_values['procedure_code_to_write'],
                    'transaction_code': parent_values['transaction_code_to_write'],
                    'partner_id': parent_values['partner_id_to_write'],
                    'invoice_currency_id': invoice_currency_id_to_write,
#                    'amount_invoice_currency': amount_invoice_currency_to_write,
                    'amount_product_value_inv_cur': amount_product_value_inv_cur_to_write,
                    'is_fiscal_only': parent_values['is_fiscal_only'],
                })
        # End of the loop on invoice/picking lines

        # Why do I manage the Partner VAT number only here and not earlier
        # in the code ?
        # Because, if I sell to a physical person in the EU with VAT, then
        # the corresponding partner will not have a VAT number, and the entry
        # will be skipped because line_tax.exclude_from_intrastat_if_present
        # is always True
        # So we should not block with a raise before the end of the loop on the
        # invoice/picking lines
        if lines_to_create:
            if parent_values['is_vat_required']:
                if src <> 'invoice':
                    raise osv.except_osv(_('Error :'), "We can't have such an intrastat type in a repair picking.")
                # If I have invoice.intrastat_country_id and the invoice address
                # is outside the EU, then I look for the fiscal rep of the partner
                if parent_obj.intrastat_country_id and not parent_obj.address_invoice_id.country_id.intrastat:
                    if not parent_obj.partner_id.intrastat_fiscal_representative:
                        raise osv.except_osv(_('Error :'), _("Missing fiscal representative for partner '%s'. It is required for invoice '%s' which has an invoice address outside the EU but the goods were delivered to or received from inside the EU.") % (parent_obj.partner_id.name, parent_obj.number))
                    else:
                        parent_values['partner_vat_to_write'] = parent_obj.partner_id.intrastat_fiscal_representative.vat
                # Otherwise, I just read the vat number on the partner of the invoice
                else:

                    if not parent_obj.partner_id.vat:
                        raise osv.except_osv(_('Error :'), _("Missing VAT number on partner '%s'.") %parent_obj.partner_id.name)
                    else:
                        parent_values['partner_vat_to_write'] = parent_obj.partner_id.vat
            else:
                parent_values['partner_vat_to_write'] = False

        for line_to_create in lines_to_create:
            line_to_create['partner_vat'] = parent_values['partner_vat_to_write']

            if src == 'picking':
                context['date'] = parent_obj.date_done # for currency conversion
                line_to_create['amount_accessory_cost_inv_cur'] = 0
            elif src == 'invoice':
                context['date'] = parent_obj.date_invoice # for currency conversion
                if not total_invoice_cur_accessory_cost:
                    line_to_create['amount_accessory_cost_inv_cur'] = 0
                else:
                    # The accessory costs are added at the pro-rata of value
                    line_to_create['amount_accessory_cost_inv_cur'] = total_invoice_cur_accessory_cost * line_to_create['amount_product_value_inv_cur'] / total_invoice_cur_product_value

            line_to_create['amount_invoice_currency'] = line_to_create['amount_product_value_inv_cur'] + line_to_create['amount_accessory_cost_inv_cur']


            # We do currency conversion NOW
            if currency_obj.name != 'EUR':
                line_to_create['amount_company_currency'] = self.pool.get('res.currency').compute(cr, uid, currency_obj.id, intrastat.company_id.currency_id.id, line_to_create['amount_invoice_currency'], context=context)
            else:
                line_to_create['amount_company_currency'] = line_to_create['amount_invoice_currency']
            # We round
            line_to_create['amount_company_currency'] = int(round(line_to_create['amount_company_currency']))
            if line_to_create['amount_company_currency'] == 0:
                # p20 of the BOD : lines with value rounded to 0 mustn't be declared
                continue
            for value in ['quantity', 'weight']: # These 2 fields are char
                if line_to_create[value]:
                    line_to_create[value] = str(int(round(line_to_create[value], 0)))
            line_obj.create(cr, uid, line_to_create, context=context)

        return True


    def common_compute_invoice_picking(self, cr, uid, intrastat, parent_obj, parent_values, context=None):

        intrastat_type = self.pool.get('report.intrastat.type').read(cr, uid, parent_values['intrastat_type_id_to_write'], context=context)
        parent_values['procedure_code_to_write'] = intrastat_type['procedure_code']
        parent_values['transaction_code_to_write'] = intrastat_type['transaction_code']
        parent_values['is_fiscal_only'] = intrastat_type['is_fiscal_only']
        parent_values['is_vat_required'] = intrastat_type['is_vat_required']


        if intrastat.obligation_level == 'simplified': # Then force to is_fiscal_only
            parent_values['is_fiscal_only'] = True

        if parent_obj._name == 'account.invoice':
            src = 'invoice'
            parent_name = parent_obj.number
        elif parent_obj._name == 'stock.picking':
            src = 'picking'
            parent_name = parent_obj.name
        else: raise osv.except_osv(_('Error :'), 'The function build_intrastat_product_lines() should have parent_obj as invoice or picking')

        if not parent_values['is_fiscal_only']:
            if not parent_obj.intrastat_transport:
# PAS de try / except, car ça marche quand le truc vaut FALSE !!!
                if not intrastat.company_id.default_intrastat_transport:
                    raise osv.except_osv(_('Error :'), _("The mode of transport is not set on %s '%s' nor the default mode of transport on the company '%s'.") %(src, parent_name, intrastat.company_id.name))
                else:
                    parent_values['transport_to_write'] = intrastat.company_id.default_intrastat_transport
            else:
                parent_values['transport_to_write'] = parent_obj.intrastat_transport

            if not parent_obj.intrastat_department:
                if not intrastat.company_id.default_intrastat_department:
                    raise osv.except_osv(_('Error :'), _("The intrastat department hasn't been set on %s '%s' and the default intrastat department is missing on the company '%s'.") %(src, parent_name, intrastat.company_id.name))
                else:
                    parent_values['department_to_write'] = intrastat.company_id.default_intrastat_department
            else:
                parent_values['department_to_write'] = parent_obj.intrastat_department
        else:
            parent_values['department_to_write'] = False
            parent_values['transport_to_write'] = False
            parent_values['transaction_code_to_write'] = False
            parent_values['partner_country_id_to_write'] = False
        #print "parent_values =", parent_values
        return parent_values


    def remove_intrastat_product_lines(self, cr, uid, ids, field, context=None):
        '''Get current lines that were generated from invoices/picking and delete them'''
        if len(ids) != 1: raise osv.except_osv(_('Error :'), 'Hara kiri in remove_intrastat_product_lines')
        line_obj = self.pool.get('report.intrastat.product.line')
        line_remove_ids = line_obj.search(cr, uid, [('parent_id', '=', ids[0]), (field, '!=', False)], context=context)
        #print "line_remove_ids = ", line_remove_ids
        if line_remove_ids:
            line_obj.unlink(cr, uid, line_remove_ids, context=context)


    def generate_product_lines_from_invoice(self, cr, uid, ids, context=None):
        #print "generate lines, ids=", ids
        intrastat = self.browse(cr, uid, ids[0], context=context)
        self.pool.get('report.intrastat.common')._check_generate_lines(cr, uid, intrastat, context=context)
        self.remove_intrastat_product_lines(cr, uid, ids, 'invoice_id', context=context)

        invoice_obj = self.pool.get('account.invoice')
        invoice_type = False
        if intrastat.type == 'import':
            # Les régularisations commerciales à l'HA ne sont PAS
            # déclarées dans la DEB, cf page 50 du BOD 6883 du 06 janvier 2011
            invoice_type = ('in_invoice', 'POUET') # I need 'POUET' to make it a tuple
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

            # We should always have a country on address_invoice_id
            if not invoice.address_invoice_id.country_id:
                raise osv.except_osv(_('Error :'), _("Missing country on partner address '%s' of partner '%s'.") %(invoice.address_invoice_id.name, invoice.address_invoice_id.partner_id.name))

            # If I have no invoice.intrastat_country_id, which is the case the first month
            # of the deployment of the module, then I use the country on invoice address
            if not invoice.intrastat_country_id:
                if not invoice.address_invoice_id.country_id.intrastat:
                    continue
                elif invoice.address_invoice_id.country_id.id == intrastat.company_id.country_id.id:
                    continue
                else:
                    parent_values['partner_country_id_to_write'] = invoice.address_invoice_id.country_id.id

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
                        raise osv.except_osv(_('Error :'), _("The intrastat type hasn't been set on invoice '%s' and the 'default intrastat type for customer invoice' is missing for the company '%s'.") %(invoice.number, intrastat.company_id.name))
                elif invoice.type == 'out_refund':
                    if intrastat.company_id.default_intrastat_type_out_refund:
                        parent_values['intrastat_type_id_to_write'] = intrastat.company_id.default_intrastat_type_out_refund.id
                    else:
                        raise osv.except_osv(_('Error :'), _("The intrastat type hasn't been set on refund '%s' and the 'default intrastat type for customer refund' is missing for the company '%s'.") %(invoice.number, intrastat.company_id.name))
                elif invoice.type == 'in_invoice':
                    if intrastat.company_id.default_intrastat_type_in_invoice:
                        parent_values['intrastat_type_id_to_write'] = intrastat.company_id.default_intrastat_type_in_invoice.id
                    else:
                        raise osv.except_osv(_('Error :'), _("The intrastat type hasn't been set on invoice '%s' and the 'Default intrastat type for supplier invoice' is missing for the company '%s'.") %(invoice.number, intrastat.company_id.name))
                else: raise osv.except_osv(_('Error :'), "Hara kiri... we can't have a supplier refund")

            else:
                parent_values['intrastat_type_id_to_write'] = invoice.intrastat_type_id.id

            if invoice.intrastat_country_id and not invoice.address_invoice_id.country_id.intrastat and invoice.partner_id.intrastat_fiscal_representative:
                # fiscal rep
                parent_values['partner_id_to_write'] = invoice.partner_id.intrastat_fiscal_representative.id
            else:
                parent_values['partner_id_to_write'] = invoice.partner_id.id

            # Get partner on which we will check the 'country of origin' on product_supplierinfo
            parent_values['origin_partner_id'] = invoice.partner_id.id
            parent_values['origin_partner_name'] = invoice.partner_id.name

            parent_values = self.common_compute_invoice_picking(cr, uid, intrastat, invoice, parent_values, context=context)

            self.create_intrastat_product_lines(cr, uid, ids, intrastat, invoice, parent_values, context=context)

        return True



    def generate_product_lines_from_picking(self, cr, uid, ids, context=None):
        '''Function used to have the DEB lines corresponding to repairs'''
        #print "generate_product_lines_from_picking ids=", ids
        intrastat = self.browse(cr, uid, ids[0], context=context)
        self.pool.get('report.intrastat.common')._check_generate_lines(cr, uid, intrastat, context=context)
        # not needed when type = export and oblig_level = simplified, cf p26 du BOD
        if intrastat.type == 'export' and intrastat.obligation_level == 'simplified':
            raise osv.except_osv(_('Error :'), _("You don't need to get lines from picking for an export DEB in 'Simplified' obligation level."))

        # Remove existing lines
        self.remove_intrastat_product_lines(cr, uid, ids, 'picking_id', context=context)

        # Check pricelist for stat value
        if not intrastat.company_id.statistical_pricelist_id:
            raise osv.except_osv(_('Error :'), _("You must select a 'Pricelist for statistical value' for the company %s.") %intrastat.company_id.name)

        pick_obj = self.pool.get('stock.picking')
        pick_type = False
        exclude_field = False
        if intrastat.type == 'import':
            pick_type = 'in'
            exclude_field = 'purchase_id'
        if intrastat.type == 'export':
            pick_type = 'out'
            exclude_field = 'sale_id'
        picking_ids = pick_obj.search(cr, uid, [
            ('type', '=', pick_type),
            ('date_done', '<=', intrastat.end_date),
            ('date_done', '>=', intrastat.start_date),
            ('invoice_state', '=', 'none'),
            ('company_id', '=', intrastat.company_id.id),
            (exclude_field, '=', False),
            ('state', 'not in', ('draft', 'waiting', 'confirmed', 'assigned', 'cancel'))
        ], order='date_done', context=context)
        #print "picking_ids =", picking_ids
        for picking in pick_obj.browse(cr, uid, picking_ids, context=context):
            parent_values = {}
            #print "PICKING =", picking.name
            if not picking.address_id:
                continue

            if not picking.address_id.country_id:
                raise osv.except_osv(_('Error :'), _("Missing country on partner address '%s' used on picking '%s'.") %(picking.address_id.name, picking.name))
            elif not picking.address_id.country_id.intrastat:
                continue
            else:
                parent_values['partner_country_id_to_write'] = picking.address_id.country_id.id


            if not picking.address_id.partner_id:
                raise osv.except_osv(_('Error :'), _("Partner address '%s' used on picking '%s' is not linked to a partner !") %(move_line.address_id.name, picking.name))
            else:
                parent_values['partner_id_to_write'] = picking.address_id.partner_id.id

            # TODO : check = 29 /19 ???
            if not picking.intrastat_type_id:
                if picking.type == 'out':
                    if intrastat.company_id.default_intrastat_type_out_picking:
                        parent_values['intrastat_type_id_to_write'] = intrastat.company_id.default_intrastat_type_out_picking.id
                    else:
                        raise osv.except_osv(_('Error :'), _("The intrastat type hasn't been set on picking '%s' and the 'default intrastat type for outgoing products' is missing for the company '%s'.") %(picking.name, intrastat.company_id.name))
                elif picking.type == 'in':
                    if intrastat.company_id.default_intrastat_type_in_picking:
                        parent_values['intrastat_type_id_to_write'] = intrastat.company_id.default_intrastat_type_in_picking.id
                    else:
                        raise osv.except_osv(_('Error :'), _("The intrastat type hasn't been set on picking '%s' and the 'default intrastat type for incoming products' is missing for the company '%s'.") %(picking.name, intrastat.company_id.name))
                else: raise osv.except_osv(_('Error :'), "Hara kiri... we can't arrive here")
            else:
                parent_values['intrastat_type_id_to_write'] = picking.intrastat_type_id.id


            parent_values = self.common_compute_invoice_picking(cr, uid, intrastat, picking, parent_values, context=context)

            self.create_intrastat_product_lines(cr, uid, ids, intrastat, picking, parent_values, context=context)

        return True




    def done(self, cr, uid, ids, context=None):
        if len(ids) != 1: raise osv.except_osv(_('Error :'), 'Hara kiri in done')
        self.write(cr, uid, ids[0], {'state': 'done', 'date_done': datetime.strftime(datetime.today(), '%Y-%m-%d %H:%M:%S')}, context=context)
        return True

    def back2draft(self, cr, uid, ids, context=None):
        if len(ids) != 1: raise osv.except_osv(_('Error :'), 'Hara kiri in back2draft')
        self.write(cr, uid, ids[0], {'state': 'draft'}, context=context)
        return True


    def generate_xml(self, cr, uid, ids, context=None):
        '''Generate the INSTAT XML file export.'''
        #print "generate_xml ids=", ids
        from lxml import etree
        import deb_xsd
        intrastat = self.browse(cr, uid, ids[0], context=context)
        start_date_str = intrastat.start_date
        end_date_str = intrastat.end_date
        start_date_datetime = datetime.strptime(start_date_str, '%Y-%m-%d')

        self.pool.get('report.intrastat.common')._check_generate_xml(cr, uid, intrastat, context=context)

        my_company_vat = intrastat.company_id.partner_id.vat.replace(' ', '')

        if not intrastat.company_id.siret_complement:
            raise osv.except_osv(_('Error :'), _("The SIRET complement is not set on company '%s'.") %intrastat.company_id.name)
        my_company_id = my_company_vat + intrastat.company_id.siret_complement

        my_company_currency = intrastat.company_id.currency_id.name

        root = etree.Element('INSTAT')
        envelope = etree.SubElement(root, 'Envelope')
        envelope_id = etree.SubElement(envelope, 'envelopeId')
        try: envelope_id.text = intrastat.company_id.customs_accreditation
        except: raise osv.except_osv(_('Error :'), _("The customs accreditation identifier is not set for the company '%s'.") %intrastat.company_id.name)
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
            raise osv.except_osv(_('Error :'), "The obligation level for DEB should be 'simplified' or 'detailed'.")
        flow_code = etree.SubElement(declaration, 'flowCode')

        if intrastat.type == 'export':
            flow_code.text = 'D'
        elif intrastat.type == 'import':
            flow_code.text = 'A'
        else:
            raise osv.except_osv(_('Error :'), "The DEB must be of type 'Import' or 'Export'")
        currency_code = etree.SubElement(declaration, 'currencyCode')
        if my_company_currency == 'EUR': # already tested in generate_lines function !
            currency_code.text = my_company_currency
        else:
            raise osv.except_osv(_('Error :'), "Company currency must be 'EUR' but is currently '%s'." %my_company_currency)

        # THEN, the fields which vary from a line to the next
        line = 0
        for pline in intrastat.intrastat_line_ids:
            line += 1 #increment line number
            #print "line =", line
            try: intrastat_type = self.pool.get('report.intrastat.type').read(cr, uid, pline.intrastat_type_id.id, ['is_fiscal_only'], context=context)
            except: raise osv.except_osv(_('Error :'), "Missing Intrastat type id on line %d." %line)
            item = etree.SubElement(declaration, 'Item')
            item_number = etree.SubElement(item, 'itemNumber')
            item_number.text = str(line)
            # START of elements which are only required in "detailed" level
            if intrastat.obligation_level == 'detailed' and not intrastat_type['is_fiscal_only']:
                cn8 = etree.SubElement(item, 'CN8')
                cn8_code = etree.SubElement(cn8, 'CN8Code')
                try: cn8_code.text = pline.intrastat_code
                except: raise osv.except_osv(_('Error :'), _('Missing Intrastat code on line %d.') %line)
                # We fill SUCode only if the H.S. code requires it
                if pline.intrastat_uom_id:
                    su_code = etree.SubElement(cn8, 'SUCode')
                    try: su_code.text = pline.intrastat_uom_id.intrastat_label
                    except: raise osv.except_osv(_('Error :'), _('Missing Intrastat UoM on line %d.') %line)
                    destination_country = etree.SubElement(item, 'MSConsDestCode')
                    if intrastat.type == 'import': country_origin = etree.SubElement(item, 'countryOfOriginCode')
                    weight = etree.SubElement(item, 'netMass')
                    quantity_in_SU = etree.SubElement(item, 'quantityInSU')

                    try: quantity_in_SU.text = pline.quantity
                    except: raise osv.except_osv(_('Error :'), _('Missing quantity on line %d.') %line)
                else:
                    destination_country = etree.SubElement(item, 'MSConsDestCode')
                    if intrastat.type == 'import': country_origin = etree.SubElement(item, 'countryOfOriginCode')
                    weight = etree.SubElement(item, 'netMass')
                try: destination_country.text = pline.partner_country_code
                except: raise osv.except_osv(_('Error :'), _('Missing partner country on line %d.') %line)
                if intrastat.type == 'import':
                    try: country_origin.text = pline.product_country_origin_code
                    except: raise osv.except_osv(_('Error :'), _('Missing product country of origin on line %d.') %line)
                try: weight.text = pline.weight
                except: raise osv.except_osv(_('Error :'), _('Missing weight on line %d.') %line)

            # START of elements that are part of all DEBs
            invoiced_amount = etree.SubElement(item, 'invoicedAmount')
            try:
                invoiced_amount.text = str(pline.amount_company_currency)
            except: raise osv.except_osv(_('Error :'), _('Missing fiscal value on line %d.') %line)
            # Partner VAT is only declared for export when code régime <> 29
            if intrastat.type == 'export' and pline.intrastat_type_id.is_vat_required:
                partner_id = etree.SubElement(item, 'partnerId')
                try: partner_id.text = pline.partner_vat.replace(' ', '')
                except: raise osv.except_osv(_('Error :'), _("Missing VAT number for partner '%s'.") %pline.partner_id.name)
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
                except: raise osv.except_osv(_('Error :'), _('Transaction code on line %d should have 2 digits.') %line)
                mode_of_transport_code = etree.SubElement(item, 'modeOfTransportCode')
                # I can't do a try/except as usual, because field.text = str(integer)
                # will always work, even if integer is False
                if not pline.transport:
                    raise osv.except_osv(_('Error :'), _('Mode of transport is not set on line %d.') %line)
                else:
                    mode_of_transport_code.text = str(pline.transport)
                region_code = etree.SubElement(item, 'regionCode')
                try: region_code.text = pline.department
                except: raise osv.except_osv(_('Error :'), _('Department code is not set on line %d.') %line)

        xml_string = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
        # We now validate the XML file against the official XML Schema Definition
        # Because we may catch some problems with the content of the XML file this way
        self.pool.get('report.intrastat.common')._check_xml_schema(cr, uid, root, xml_string, deb_xsd.deb_xsd, context=context)
        # Attach the XML file to the current object
        attach_id = self.pool.get('report.intrastat.common')._attach_xml_file(cr, uid, ids, self, xml_string, start_date_datetime, 'deb', context=context)
        return self.pool.get('report.intrastat.common')._open_attach_view(cr, uid, attach_id, title="DEB XML file", context=context)

report_intrastat_product()


class report_intrastat_product_line(osv.osv):
    _name = "report.intrastat.product.line"
    _description = "Lines of intrastat product declaration (DEB)"
    _order = 'id'
    _columns = {
        'parent_id': fields.many2one('report.intrastat.product', 'Intrastat product ref', ondelete='cascade', select=True, readonly=True),
        'state' : fields.related('parent_id', 'state', type='string', relation='report.intrastat.product', string='State', readonly=True),
        'company_id': fields.related('parent_id', 'company_id', type='many2one', relation='res.company', string="Company", readonly=True),
        'company_currency_id': fields.related('company_id', 'currency_id', type='many2one', relation='res.currency', string="Company currency", readonly=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice ref', readonly=True),
        'picking_id': fields.many2one('stock.picking', 'Picking ref', readonly=True),
        'quantity': fields.char('Quantity', size=10, states={'done':[('readonly',True)]}),
        'source_uom_id': fields.many2one('product.uom', 'Source UoM', readonly=True),
        'intrastat_uom_id': fields.many2one('product.uom', 'Intrastat UoM', states={'done':[('readonly',True)]}),
        'partner_country_id': fields.many2one('res.country', 'Partner country', states={'done':[('readonly',True)]}),
        'partner_country_code' : fields.related('partner_country_id', 'code', type='string', relation='res.country', string='Partner country', readonly=True),
        'intrastat_code': fields.char('Intrastat code', size=9, states={'done':[('readonly',True)]}),
        'intrastat_code_id': fields.many2one('report.intrastat.code', 'Intrastat code (not used in XML)', states={'done':[('readonly',True)]}),
        # Weight should be an integer... but I want to be able to display nothing in
        # tree view when the value is False (if weight is an integer, a False value would
        # be displayed as 0), that's why weight is a char !
        'weight': fields.char('Weight', size=10, states={'done':[('readonly',True)]}),
        'amount_company_currency': fields.integer('Fiscal value in company currency',
            required=True, states={'done':[('readonly',True)]},
            help="Amount in company currency to write in the declaration. Amount in company currency = amount in invoice currency converted to company currency with the rate of the invoice date (for pickings : with the rate of the 'date done') and rounded at 0 digits"),
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
            help="Amount of product value in invoice currency. For invoices, it is the amount of the invoice line or group of invoice lines. For pickings, it is the value of the product given by the pricelist for statistical value of the company."),
        'invoice_currency_id': fields.many2one('res.currency', "Invoice currency", readonly=True),
        'product_country_origin_id' : fields.many2one('res.country', 'Product country of origin', states={'done':[('readonly',True)]}),
        'product_country_origin_code' : fields.related('product_country_origin_id', 'code', type='string', relation='res.country', string='Product country of origin', readonly=True),
        'transport' : fields.selection([
            (1, '1. Transport maritime'),
            (2, '2. Transport par chemin de fer'),
            (3, '3. Transport par route'),
            (4, '4. Transport par air'),
            (5, '5. Envois postaux'),
            (7, '7. Installations de transport fixes'),
            (8, '8. Transport par navigation intérieure'),
            (9, '9. Propulsion propre')
            ], 'Type of transport', states={'done':[('readonly',True)]}),
        'department' : fields.char('Department', size=2, states={'done':[('readonly',True)]}),
        'intrastat_type_id' : fields.many2one('report.intrastat.type', 'Intrastat type', states={'done':[('readonly',True)]}),
        'is_vat_required' : fields.related('intrastat_type_id', 'is_vat_required', type='boolean', relation='report.intrastat.type', string='Is Partner VAT required ?', readonly=True),
        # Is fiscal_only is not fields.related because, if obligation_level = simplified, is_fiscal_only is always true
        'is_fiscal_only' : fields.boolean('Is fiscal only?', readonly=True),
        'procedure_code': fields.char('Procedure code', size=2),
        'transaction_code': fields.char('Transaction code', size=2),
        'partner_vat': fields.char('Partner VAT', size=32, states={'done':[('readonly',True)]}),
        'partner_id': fields.many2one('res.partner', 'Partner name', states={'done':[('readonly',True)]}),
    }

    def _integer_check(self, cr, uid, ids):
        for values in self.read(cr, uid, ids, ['weight', 'quantity']):
            if values['weight'] and not values['weight'].isdigit():
                raise osv.except_osv(_('Error :'), _('Weight must be an integer.'))
            if values['quantity'] and not values['quantity'].isdigit():
                raise osv.except_osv(_('Error :'), _('Quantity must be an integer.'))
        return True

    def _code_check(self, cr, uid, ids):
        for lines in self.read(cr, uid, ids, ['procedure_code', 'transaction_code']):
            self.pool.get('report.intrastat.type').real_code_check(lines)
        return True

    _constraints = [
        (_code_check, "Error msg in raise", ['procedure_code', 'transaction_code']),
        (_integer_check, "Error msg in raise", ['weight', 'quantity']),
    ]


    def partner_on_change(self, cr, uid, ids, partner_id=False):
        return self.pool.get('report.intrastat.common').partner_on_change(cr, uid, ids, partner_id)

    def intrastat_code_on_change(self, cr, uid, ids, intrastat_code_id=False):
        result = {}
        result['value'] = {}
        if intrastat_code_id:
            intrastat_code = self.pool.get('report.intrastat.code').browse(cr, uid, intrastat_code_id)
            if intrastat_code.intrastat_uom_id:
                result['value'].update({'intrastat_code': intrastat_code.intrastat_code, 'intrastat_uom_id': intrastat_code.intrastat_uom_id.id})
            else:
                result['value'].update({'intrastat_code': intrastat_code.intrastat_code, 'intrastat_uom_id': False})
        return result

    def intrastat_type_on_change(self, cr, uid, ids, intrastat_type_id=False, type=False, obligation_level=False):
        result = {}
        result['value'] = {}
        if obligation_level=='simplified':
            result['value'].update({'is_fiscal_only': True})
        if intrastat_type_id:
            intrastat_type = self.pool.get('report.intrastat.type').read(cr, uid, intrastat_type_id, ['procedure_code', 'transaction_code', 'is_fiscal_only', 'is_vat_required'])
            result['value'].update({'procedure_code': intrastat_type['procedure_code'], 'transaction_code': intrastat_type['transaction_code'], 'is_vat_required': intrastat_type['is_vat_required']})
            if obligation_level=='detailed':
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
        #print "intrastat_type_on_change res=", result
        return result


report_intrastat_product_line()

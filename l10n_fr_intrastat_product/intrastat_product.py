# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat product module for OpenERP
#    Copyright (C) 2009-2011 Akretion (http://www.akretion.com). All Rights Reserved.
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

# TODO : We don't have the statistical value in the XML export !!!

#TODO : vérifier le multi-company

# TODO : display invoice type ?

from osv import osv, fields
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from tools.translate import _

class report_intrastat_type(osv.osv):
    _inherit = "report.intrastat.type"
    _columns = {
        'procedure_code': fields.integer('Procedure code', help="For the 'DEB' declaration to France's customs administration, you should enter the 'code régime' here."),
        'transaction_code': fields.integer('Transaction code', help="For the 'DEB' declaration to France's customs administration, you should enter the number 'nature de la transaction' here."),
    }

    def _code_check(self, cr, uid, ids):
    # Procedure_code and transaction codes are an integers, so they always have a value
        for intrastat_type in self.read(cr, uid, ids, ['type', 'procedure_code', 'transaction_code']):
            if intrastat_type['type'] == 'other':
                continue
            else:
                if not 10 <= intrastat_type['procedure_code'] <= 99:
                    raise osv.except_osv(_('Error :'), _('Procedure code must be between 10 and 99'))
                if not 10 <= intrastat_type['transaction_code'] <= 99:
                    raise osv.except_osv(_('Error :'), _('Transaction code must be between 10 and 99'))
        return True

    _constraints = [
        (_code_check, "Error msg in raise", ['procedure_code', 'transaction_code']),
    ]

report_intrastat_type()

class report_intrastat_product(osv.osv):
    _name = "report.intrastat.product"
    _description = "Intrastat report for products"
    _rec_name = "start_date"
    _order = "start_date, type"


    def _compute_numbers(self, cr, uid, ids, name, arg, context=None):
        print "PRODUCT _compute numbers start ids=", ids
        return self.pool.get('report.intrastat.common')._compute_numbers(cr, uid, ids, self, context=context)

    def _compute_end_date(self, cr, uid, ids, name, arg, context=None):
        print "PRODUCT _compute_end_date START ids=", ids
        return self.pool.get('report.intrastat.common')._compute_end_date(cr, uid, ids, self, context=context)

    def _get_intrastat_from_product_line(self, cr, uid, ids, context=None):
        print "invalidation function CALLED !!!"
        return self.pool.get('report.intrastat.product').search(cr, uid, [('intrastat_line_ids', 'in', ids)], context=context)

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True, states={'done':[('readonly',True)]}, help="Related company."),
        'start_date': fields.date('Start date', required=True, states={'done':[('readonly',True)]}, help="Start date of the declaration. Must be the first day of a month."),
        'end_date': fields.function(_compute_end_date, method=True, type='date', string='End date', store=True, help="End date for the declaration. Must be the last day of the month of the start date."),
        'type': fields.selection([('import', 'Import'), ('export', 'Export')], 'Type', required=True, states={'done':[('readonly',True)]}, help="Select the type of DEB."),
        'obligation_level' : fields.selection([('detailed', 'Detailed'), ('simplified', 'Simplified')], 'Obligation level', required=True, states={'done':[('readonly',True)]}, help="Your obligation level for a certain type of DEB (Import or Export) depends on the total value that you export or import per year. Note that the obligation level 'Simplified' doesn't exist for Import."),
        'intrastat_line_ids': fields.one2many('report.intrastat.product.line', 'parent_id', 'Report intrastat product lines', states={'done':[('readonly',True)]}),
        'num_lines': fields.function(_compute_numbers, method=True, type='integer', multi='numbers', string='Number of lines', store={
            'report.intrastat.product.line': (_get_intrastat_from_product_line, ['parent_id'], 20),
        }, help="Number of lines in this declaration."),
        'total_amount': fields.function(_compute_numbers, method=True, digits=(16,0), multi='numbers', string='Total amount', store={
            'report.intrastat.product.line': (_get_intrastat_from_product_line, ['amount_company_currency', 'parent_id'], 20),
            }, help="Total amount in company currency of the declaration."),
        'currency_id': fields.related('company_id', 'currency_id', readonly=True, type='many2one', relation='res.currency', string='Currency'),
        'state' : fields.selection([
            ('draft','Draft'),
            ('done','Done'),
        ], 'State', select=True, readonly=True, help="State of the declaration. When the state is set to 'Done', the parameters become read-only."),
        'date_done' : fields.date('Date done', readonly=True, help="Last date when the intrastat declaration was converted to 'Done' state."),
        'notes' : fields.text('Notes', help="You can add some comments here if you want."),
    }

    _defaults = {
        # By default, we propose 'current month -1', because you prepare in
        # February the DEB of January
        'start_date': lambda *a: datetime.strftime(datetime.today() + relativedelta(day=1, months=-1), '%Y-%m-%d'),
        'state': lambda *a: 'draft',
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
                print "company_id", company_id
                company = self.pool.get('res.company').read(cr, uid, company_id, ['export_obligation_level'])
                print "company =", company
                if company['export_obligation_level']:
                    result['value'].update({'obligation_level': company['export_obligation_level']})
        return result

    def _check_start_date(self, cr, uid, ids, context=None):
        return self.pool.get('report.intrastat.common')._check_start_date(cr, uid, ids, self, context=context)

    def _check_obligation_level(self, cr, uid, ids, context=None):
        for intrastat_to_check in self.read(cr, uid, ids, ['type', 'obligation_level'], context=context):
            if intrastat_to_check['type'] == 'import' and intrastat_to_check['obligation_level'] == 'simplified':
                return False
        return True

    _constraints = [
        (_check_start_date, "Start date must be the first day of a month", ['start_date']),
        (_check_obligation_level, "Obligation level can't be 'Simplified' for Import", ['obligation_level']),
    ]

    _sql_constraints = [
        ('date_uniq', 'unique(start_date, company_id, type)', 'You have already created a DEB of the same type for this month !'),
    ]

    def generate_product_lines(self, cr, uid, ids, context=None):
        print "generate lines, ids=", ids
        intrastat = self.browse(cr, uid, ids[0], context=context)
        self.pool.get('report.intrastat.common')._check_generate_lines(cr, uid, ids, intrastat, context=context)
        # Get current service lines and delete them
        line_remove = self.read(cr, uid, ids[0], ['intrastat_line_ids'], context=context)
        print "line_remove", line_remove
        if line_remove['intrastat_line_ids']:
            self.pool.get('report.intrastat.product.line').unlink(cr, uid, line_remove['intrastat_line_ids'], context=context)

# What about if we sell a product with 100% discount ?
# Here, we suppose that list_price on product template is in company_currency
        sql = '''
        SELECT
            min(inv_line.id) as id,
            company.id,
            inv.id as invoice_id,
            inv.currency_id as invoice_currency_id,
            company.currency_id as company_currency_id,
            hs.code8 as intrastat_code_8,
            inv_address.country_id as partner_country_id,
            pt.country_id as product_country_origin_id,
            sum(case when not intr.intrastat_only
                then inv_line.price_subtotal
                else 0
                end) as amount_invoice_currency,
            sum(case when not intr.intrastat_only and company.currency_id != inv.currency_id and res_currency_rate.rate is not null
                then round(inv_line.price_subtotal/res_currency_rate.rate, 2)
                when not intr.intrastat_only and company.currency_id = inv.currency_id
                then inv_line.price_subtotal
                else 0
                end) as amount_company_currency,

            sum(case when intr.intrastat_only and company.currency_id != inv.currency_id and res_currency_rate.rate is not null
                then round(inv_line.price_subtotal/res_currency_rate.rate, 2)
                    when intr.intrastat_only and company.currency_id = inv.currency_id
                        then inv_line.price_subtotal
                        else 0
                end) as stat_value_company_currency,

            sum(
                case when inv_uom.category_id != pt_uom.category_id then pt.weight_net * inv_line.quantity
                else
                    case when inv_uom.factor_inv_data > 0
                        then
                            pt.weight_net * inv_line.quantity * inv_uom.factor_inv_data
                        else
                            pt.weight_net * inv_line.quantity / inv_uom.factor
                    end
                end
                ) as weight,

            sum(
                case when inv_uom.category_id != pt_uom.category_id then inv_line.quantity
                else
                    case when inv_uom.factor_inv_data > 0
                        then
                            inv_line.quantity * inv_uom.factor_inv_data
                        else
                            inv_line.quantity / inv_uom.factor
                    end
                end
                ) as invoice_qty,
            inv_uom.id as invoice_uom_id,
            intrastat_uom.id as intrastat_uom_id,

            intr.procedure_code,
            intr.transaction_code,
            prt.vat as partner_vat,
            inv.partner_id as partner_id,
            intr.type as type,
            inv.intrastat_transport as transport,
            inv.intrastat_department as department

        FROM
            account_invoice inv
            left join account_invoice_line inv_line on inv_line.invoice_id=inv.id
            left join (product_template pt
                left join product_product pp on (pp.product_tmpl_id = pt.id)
                left join product_uom pt_uom on (pt.uom_id = pt_uom.id )
                left join (report_intrastat_code hs
                    left join product_uom intrastat_uom on ( intrastat_uom.id = hs.intrastat_uom_id )
                    ) on (hs.id = pt.intrastat_id))
                on (inv_line.product_id = pp.id)
                    left join product_uom inv_uom on inv_uom.id=inv_line.uos_id
                    left join (res_partner_address inv_address
                        left join res_country inv_country on (inv_country.id = inv_address.country_id))
                    on (inv_address.id = inv.address_invoice_id)
            left join report_intrastat_type intr on inv.intrastat_type_id = intr.id
            left join res_partner prt on inv.partner_id = prt.id
            left join res_currency_rate on (inv.currency_id = res_currency_rate.currency_id and inv.date_invoice = res_currency_rate.name)
            left join res_company company on inv.company_id=company.id

        WHERE
            inv.state in ('open', 'paid', 'legal_intrastat')
            and inv_line.product_id is not null
            and inv_line.price_subtotal != 0
            and inv_country.intrastat=true
            and pt.exclude_from_intrastat is not true
            and intr.type != 'other'
            and company.id = %s
            and inv.date_invoice >= %s
            and inv.date_invoice <= %s
            and intr.type = %s

        GROUP BY company.id, inv.id, code8, intr.type, product_country_origin_id, partner_country_id, inv.currency_id, intr.procedure_code, intr.transaction_code, prt.vat, inv.partner_id, company_currency_id, intrastat_uom.id, inv_uom.id, transport, department
        '''
        # Execute the big SQL query to get all the lines
        cr.execute(sql, (intrastat.company_id.id, intrastat.start_date, intrastat.end_date, intrastat.type))
        res_sql = cr.fetchall()
        print "res_sql=", res_sql
        print "intrastat.type =", intrastat.type
        line_obj = self.pool.get('report.intrastat.product.line')
        for id, company_id, invoice_id, invoice_currency_id, company_currency_id, intrastat_code_8, partner_country_id, product_country_origin_id, amount_invoice_currency, amount_company_currency, stat_value_company_currency, weight, invoice_qty, invoice_uom_id, intrastat_uom_id, procedure_code, transaction_code, partner_vat, partner_id, type, transport, department in res_sql:
            print "weight =", weight
            print "company_currency_id =", company_currency_id
            print "stat_value_company_currency, =", stat_value_company_currency
            # TODO : apply check only when in "detailed" obligation level ?
            if not weight:
                invoice = self.pool.get('account.invoice').read(cr, uid, invoice_id, ['invoice_number'], context=context)
                raise osv.except_osv(_('Error :'), _('Missing weight on one of the products of invoice %s with HS code %s.'%(invoice['invoice_number'], intrastat_code_8)))
            # TODO : ça crashe quand les valeurs "integer" valent false -> à tester !
            # invoice_qty et subtotal -> déjà vérifié dans requête SQL... quid de stat_value ?
            # Idem pr intrastat_uom et invoice_uom ???
            line_obj.create(cr, uid, {
                'parent_id': ids[0],
                'invoice_id': invoice_id,
                'invoice_qty': int(round(invoice_qty, 0)),
                'invoice_uom_id': invoice_uom_id,
                'intrastat_uom_id': intrastat_uom_id,
                'partner_country_id': partner_country_id,
                'intrastat_code_8': intrastat_code_8,
                'weight': int(round(weight, 0)),
                'amount_invoice_currency': int(round(amount_invoice_currency, 0)),
                'amount_company_currency': int(round(amount_company_currency, 0)),
                'stat_value_company_currency': int(round(stat_value_company_currency, 0)),
                'invoice_currency_id': invoice_currency_id,
                'company_currency_id': company_currency_id,
                'product_country_origin_id': product_country_origin_id,
                'transport': transport,
                'department': department,
                'procedure_code': procedure_code,
                'transaction_code': transaction_code,
                'partner_vat': partner_vat,
                'partner_id': partner_id,
                    }, context=context)
        return None


    def done(self, cr, uid, ids, context=None):
        if len(ids) != 1: raise osv.except_osv(_('Error :'), 'Hara kiri in done')
        self.write(cr, uid, ids[0], {'state': 'done', 'date_done': datetime.strftime(datetime.today(), '%Y-%m-%d')}, context=context)
        return None

    def back2draft(self, cr, uid, ids, context=None):
        if len(ids) != 1: raise osv.except_osv(_('Error :'), 'Hara kiri in back2draft')
        self.write(cr, uid, ids[0], {'state': 'draft'}, context=context)
        return None


    def generate_xml(self, cr, uid, ids, context=None):
        '''Generate the INSTAT XML file export.'''
        from lxml import etree
        import deb_xsd
        intrastat = self.browse(cr, uid, ids[0], context=context)
        start_date_str = intrastat.start_date
        end_date_str = intrastat.end_date
        start_date_datetime = datetime.strptime(start_date_str, '%Y-%m-%d')

        self.pool.get('report.intrastat.common')._check_generate_xml(cr, uid, ids, intrastat, context=context)

        my_company_vat = intrastat.company_id.partner_id.vat.replace(' ', '')

        if not intrastat.company_id.siret_complement:
            raise osv.except_osv(_('Error :'), _('The SIRET complement is not set.'))
        my_company_id = my_company_vat + intrastat.company_id.siret_complement

        my_company_currency = intrastat.company_id.currency_id.code

        root = etree.Element('INSTAT')
        envelope = etree.SubElement(root, 'Envelope')
        envelope_id = etree.SubElement(envelope, 'envelopeId')
        try: envelope_id.text = intrastat.company_id.customs_accreditation
        except: raise osv.except_osv(_('Error :'), _('The customs accreditation identifier is not set for the company "%s".'%intrastat.company_id.name))
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
            raise osv.except_osv(_('Error :'), _("The obligation level for DEB should be 'simplified' or 'detailed'."))
        flow_code = etree.SubElement(declaration, 'flowCode')

        if intrastat.type == 'export':
            flow_code.text = 'D'
        elif intrastat.type == 'import':
            flow_code.text = 'A'
        else:
            raise osv.except_osv(_('Error :'), _('The DEB must be of type "Import" or "Export"'))
        currency_code = etree.SubElement(declaration, 'currencyCode')
        if my_company_currency == 'EUR': # TODO : remove, already tested
            currency_code.text = my_company_currency
        else:
            raise osv.except_osv(_('Error :'), _("Company currency must be 'EUR' for the XML file export, but it is currently '%s'." %my_company_currency))

        # THEN, the fields which vary from a line to the next
        line = 0
        for pline in intrastat.intrastat_line_ids:
            print "parent_type =", pline.parent_type, type(pline.parent_type)
            line += 1 #increment line number
            item = etree.SubElement(declaration, 'Item')
            item_number = etree.SubElement(item, 'itemNumber')
            item_number.text = str(line)
            # START of elements which are only required in "detailed" level
            if intrastat.obligation_level == 'detailed':
                cn8 = etree.SubElement(item, 'CN8')
                cn8_code = etree.SubElement(cn8, 'CN8Code')
                try: cn8_code.text = pline.intrastat_code_8
                except: raise osv.except_osv(_('Error :'), _('Missing Intrastat code on line %d.' %line))
                if pline.intrastat_uom_id:
                    if pline.intrastat_uom_id != pline.invoice_uom_id:
                        raise osv.except_osv(_('Error :'), _("On line %d, the unit of measure on invoice and intrastat code are different. We don't handle this scenario for the moment."%i))
                    else:
                        su_code = etree.SubElement(cn8, 'SUCode')
                        try: su_code.text = pline.intrastat_uom_id.intrastat_label
                        except: raise osv.except_osv(_('Error :'), _('Missing Intrastat UoM on line %d.' %line))
                        destination_country = etree.SubElement(item, 'MSConsDestCode')
                        country_origin = etree.SubElement(item, 'countryOfOriginCode')
                        weight = etree.SubElement(item, 'netMass')
                        quantity_in_SU = etree.SubElement(item, 'quantityInSU')

                        try: quantity_in_SU.text = str(pline.invoice_qty)
                        except: raise osv.except_osv(_('Error :'), _('Missing invoice quantity on line %d.' %line))
                else:
                    destination_country = etree.SubElement(item, 'MSConsDestCode')
                    country_origin = etree.SubElement(item, 'countryOfOriginCode')
                    weight = etree.SubElement(item, 'netMass')

                try: destination_country.text = pline.partner_country_code
                except: raise osv.except_osv(_('Error :'), _('Missing partner country on line %d.' %line))
                try: country_origin.text = pline.product_country_origin_code
                except: raise osv.except_osv(_('Error :'), _('Missing product country of origin on line %d.' %line))
                try: weight.text = str(pline.weight)
                except: raise osv.except_osv(_('Error :'), _('Missing weight on line %d.' %line))

            # START of elements that are part of all DEBs
            invoiced_amount = etree.SubElement(item, 'invoicedAmount')
            try:
                invoiced_amount.text = str(pline.amount_company_currency)
            except: raise osv.except_osv(_('Error :'), _('Missing fiscal value on line %d.' %line))
            # Partner VAT is only declared for export
            if intrastat.type == 'export':
                partner_id = etree.SubElement(item, 'partnerId')
                try: partner_id.text = pline.partner_vat.replace(' ', '')
                except: raise osv.except_osv(_('Error :'), _('Missing VAT number for partner "%s".' %pline.partner_name))
            statistical_procedure_code = etree.SubElement(item, 'statisticalProcedureCode')
            statistical_procedure_code.text = str(pline.procedure_code) # str(integrer) always have a value, so it should never crash here -> no try/except

            # START of elements which are only required in "detailed" level
            if intrastat.obligation_level == 'detailed':
                transaction_nature = etree.SubElement(item, 'NatureOfTransaction')
                transaction_nature_a = etree.SubElement(transaction_nature, 'natureOfTransactionACode')
                transaction_nature_a.text = str(pline.transaction_code)[0] # str(integer)[0] always have a value, so it should never crash here -> no try/except
                transaction_nature_b = etree.SubElement(transaction_nature, 'natureOfTransactionBCode')
                try: transaction_nature_b.text = str(pline.transaction_code)[1]
                except: raise osv.except_osv(_('Error :'), _('Transaction code on line %d should have 2 digits.' %line))
                mode_of_transport_code = etree.SubElement(item, 'modeOfTransportCode')
                if pline.transport:
                    mode_of_transport_code.text = str(pline.transport)
                elif intrastat.company_id.default_intrastat_transport:
                    mode_of_transport_code.text = str(intrastat.company_id.default_intrastat_transport)
                else:
                    raise osv.except_osv(_('Error :'), _('Mode of transport is not set on line %d nor the default mode of transport for the company %s.' %(line, intrastat.company_id.name)))
                region_code = etree.SubElement(item, 'regionCode')
                if pline.department:
                    region_code.text = pline.department
                elif intrastat.company_id.default_intrastat_department:
                    region_code.text = intrastat.company_id.default_intrastat_department
                else:
                    raise osv.except_osv(_('Error :'), _('Department code is not set on line %d nor the default department code for the company %s.' % (line, intrastat.company_id.name)))

        xml_string = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
        # We now validate the XML file against the official XML Schema Definition
        # Because we may catch some problems with the content of the XML file this way
        self.pool.get('report.intrastat.common')._check_xml_schema(cr, uid, root, xml_string, deb_xsd.deb_xsd, context=context)
        # Attach the XML file to the current object
        self.pool.get('report.intrastat.common')._attach_xml_file(cr, uid, ids, self, xml_string, start_date_datetime, 'deb', context=context)
        return None

report_intrastat_product()


class report_intrastat_product_line(osv.osv):
    _name = "report.intrastat.product.line"
    _description = "Lines of intrastat product declaration (DEB)"
    _order = 'invoice_id'
    _columns = {
        'parent_id': fields.many2one('report.intrastat.product', 'Intrastat product ref', ondelete='cascade', select=True),
        'parent_type' : fields.related('parent_id', 'type', type='string', relation='report.intrastat.product', string='Declaration type', readonly=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice ref', readonly=True),
        'invoice_qty': fields.integer('Invoice quantity', readonly=True),
        'invoice_uom_id': fields.many2one('product.uom', 'Invoice UoM', readonly=True),
        'intrastat_uom_id': fields.many2one('product.uom', 'Intrastat UoM', readonly=True),
        'partner_country_id': fields.many2one('res.country', 'Partner country (id)', readonly=True),
        'partner_country_code' : fields.related('partner_country_id', 'code', type='string', relation='res.country', string='Partner country', readonly=True),
        'intrastat_code_8': fields.char('Intrastat code', size=8, readonly=True),
        'weight': fields.integer('Weight', readonly=True),
        'amount_invoice_currency': fields.integer('Fiscal value in invoice currency', readonly=True),
        'amount_company_currency': fields.integer('Fiscal value in company currency', readonly=True),
        'stat_value_company_currency' : fields.integer('Stat value in company currency', readonly=True),
        'invoice_currency_id': fields.many2one('res.currency', "Invoice currency", readonly=True),
        'company_currency_id': fields.many2one('res.currency', "Company currency", readonly=True),
        'product_country_origin_id' : fields.many2one('res.country', 'Product country of origin (id)', readonly=True),
        'product_country_origin_code' : fields.related('product_country_origin_id', 'code', type='string', relation='res.country', string='Product country of origin', readonly=True),
        'transport' : fields.selection([(1, 'Transport maritime'), \
            (2, 'Transport par chemin de fer'), \
            (3, 'Transport par route'), \
            (4, 'Transport par air'), \
            (5, 'Envois postaux'), \
            (7, 'Installations de transport fixes'), \
            (8, 'Transport par navigation intérieure'), \
            (9, 'Propulsion propre')], 'Type of transport', readonly=True),
        'department' : fields.char('Department', size=2, readonly=True),
        'procedure_code': fields.integer('Procedure code', readonly=True),
        'transaction_code': fields.integer('Transaction code', readonly=True),
        'partner_vat': fields.char('Partner VAT', size=32, readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner name', readonly=True),
        'date_invoice' : fields.related('invoice_id', 'date_invoice', type='date', relation='account.invoice', string='Invoice date', readonly=True),
    }

report_intrastat_product_line()

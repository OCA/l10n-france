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

#TODO : vérifier le multi-company

from osv import osv, fields
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from tools.translate import _


class report_intrastat_product(osv.osv):
    _name = "report.intrastat.product"
    _description = "Intrastat report for products"
    _rec_name = "start_date"
    _order = "start_date, type"


    def _compute_numbers(self, cr, uid, ids, name, arg, context=None):
        return self.pool.get('report.intrastat.common')._compute_numbers(cr, uid, ids, self, context=context)

    def _compute_end_date(self, cr, uid, ids, name, arg, context=None):
        return self.pool.get('report.intrastat.common')._compute_end_date(cr, uid, ids, self, context=context)

    def _get_intrastat_from_product_line(self, cr, uid, ids, context=None):
        return self.pool.get('report.intrastat.product').search(cr, uid, [('intrastat_line_ids', 'in', ids)], context=context)

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True, states={'done':[('readonly',True)]}, help="Related company."),
        'start_date': fields.date('Start date', required=True, states={'done':[('readonly',True)]}, help="Start date of the declaration. Must be the first day of a month."),
        'end_date': fields.function(_compute_end_date, method=True, type='date', string='End date', store=True, help="End date for the declaration. Must be the last day of the month of the start date."),
        'type': fields.selection([
            ('import', 'Import'),
            ('export', 'Export')
            ], 'Type', required=True, states={'done':[('readonly',True)]}, help="Select the type of DEB."),
        'obligation_level' : fields.selection([
            ('detailed', 'Detailed'),
            ('simplified', 'Simplified')
            ], 'Obligation level', required=True, states={'done':[('readonly',True)]}, help="Your obligation level for a certain type of DEB (Import or Export) depends on the total value that you export or import per year. Note that the obligation level 'Simplified' doesn't exist for Import."),
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
        'date_done' : fields.datetime('Date done', readonly=True, help="Last date when the intrastat declaration was converted to 'Done' state."),
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
                company = self.pool.get('res.company').read(cr, uid, company_id, ['export_obligation_level'])
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

    def generate_product_lines_from_invoice(self, cr, uid, ids, context=None):
        print "generate lines, ids=", ids
        intrastat = self.browse(cr, uid, ids[0], context=context)
        self.pool.get('report.intrastat.common')._check_generate_lines(cr, uid, ids, intrastat, context=context)
        line_obj = self.pool.get('report.intrastat.product.line')
        # Get current lines that were generated from invoices and delete them
        line_remove_ids = line_obj.search(cr, uid, [('parent_id', '=', ids[0]), ('invoice_id', '!=', False)], context=context)
        print "line_remove", line_remove_ids
        if line_remove_ids:
            line_obj.unlink(cr, uid, line_remove_ids, context=context)

# What about if we sell a product with 100% discount ?
        sql = '''
        SELECT
            min(inv_line.id) as id,
            company.id,
            inv.id as invoice_id,
            inv.number as invoice_number,
            inv.currency_id as invoice_currency_id,
            hs.intrastat_code as intrastat_code,
            pt.intrastat_id as intrastat_code_id,
            inv_address.country_id as partner_country_id,
            pt.country_id as product_country_origin_id,
            sum(inv_line.price_subtotal) as amount_invoice_currency,
            sum(case when company.currency_id != inv.currency_id and res_currency_rate.rate is not null
                then round(inv_line.price_subtotal/res_currency_rate.rate, 2)
                when company.currency_id = inv.currency_id
                then inv_line.price_subtotal
                else 0
                end) as amount_company_currency,

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
                ) as weight_net,

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
            intr.id as intrastat_type_id,
            intr.procedure_code,
            intr.transaction_code,
            intr.is_fiscal_only,
            prt.vat as partner_vat,
            inv.partner_id as partner_id,
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
            left join report_intrastat_type intr on inv.type = intr.invoice_type
            left join res_partner prt on inv.partner_id = prt.id
            left join res_currency_rate on (inv.currency_id = res_currency_rate.currency_id and inv.date_invoice = res_currency_rate.name)
            left join res_company company on inv.company_id=company.id

        WHERE
            inv.state in ('open', 'paid')
            and inv_line.product_id is not null
            and inv_line.price_subtotal != 0
            and inv_country.intrastat=true
            and pt.exclude_from_intrastat is not true
            and pt.type in ('product', 'consu')
            and company.id = %s
            and inv.date_invoice >= %s
            and inv.date_invoice <= %s
            and inv.type in %s

        GROUP BY company.id, inv.id, invoice_number, hs.intrastat_code, intrastat_code_id, product_country_origin_id, partner_country_id, inv.currency_id, intr.procedure_code, intr.transaction_code, intr.is_fiscal_only, prt.vat, inv.partner_id, intrastat_uom.id, inv_uom.id, transport, department, intrastat_type_id
        '''
        # Execute the big SQL query to get all the lines
        invoice_type = False
        if intrastat.type == 'import':
            # Les régularisations commerciales à l'HA ne sont PAS
            # déclarées dans la DEB, cf page 50 du BOD 6883 du 06 janvier 2011
            invoice_type = ('in_invoice', 'POUET') # I need 'POUET' to make it a tuple
        if intrastat.type == 'export':
            invoice_type = ('out_invoice', 'out_refund')

        cr.execute(sql, (intrastat.company_id.id, intrastat.start_date, intrastat.end_date, invoice_type))
        res_sql = cr.fetchall()
        print "res_sql=", res_sql
        for id, company_id, invoice_id, invoice_number, invoice_currency_id, intrastat_code, intrastat_code_id, partner_country_id, product_country_origin_id, amount_invoice_currency, amount_company_currency, weight_net, invoice_qty, invoice_uom_id, intrastat_uom_id, intrastat_type_id, procedure_code, transaction_code, is_fiscal_only, partner_vat, partner_id, transport, department in res_sql:
            print "weight_net =", weight_net
            print "transport =", transport
            print "invoice num =", invoice_number
            if not weight_net:
                raise osv.except_osv(_('Error :'), _('Missing net weight on one of the products of invoice %s with HS code %s.'%(invoice_number, intrastat_code)))
            if not product_country_origin_id:
                raise osv.except_osv(_('Error :'), _('Missing country of origin on one of the products of invoice %s with HS code %s.'%(invoice_number, intrastat_code)))
            # TODO : check many others !
            # TODO : manage the "detailed" obligation level ?
            quantity_to_write = str(int(round(invoice_qty, 0)))
            invoice_uom_id_to_write = invoice_uom_id
            intrastat_uom_id_to_write = intrastat_uom_id
            partner_country_id_to_write = partner_country_id
            intrastat_code_to_write = intrastat_code
            intrastat_code_id_to_write = intrastat_code_id
            weight_to_write = str(int(round(weight_net, 0)))
            product_country_origin_id_to_write = product_country_origin_id
            transport_to_write = transport
            department_to_write = department
            partner_vat_to_write = partner_vat

            # The VAT number should be declared only on Export
            if intrastat.type == 'import':
                partner_vat_to_write = False

            # The origin country should only be declated on Import
            if intrastat.type == 'export':
                product_country_origin_id_to_write = False

            if not transport:
                try: transport_to_write = intrastat.company_id.default_intrastat_transport
                except: raise osv.except_osv(_('Error :'), _('Mode of transport is not set on invoice %s nor the default mode of transport for the company %s.' %(invoice_number, intrastat.company_id.name)))

            if not department:
                try: department_to_write = intrastat.company_id.default_intrastat_department
                except: raise osv.except_osv(_('Error :'), _('Department is not set on invoice %s nor the default department for the company %s.' %(invoice_number, intrastat.company_id.name)))

            # Stats data should not be declared on certain "code régime"
            if is_fiscal_only:
                quantity_to_write = False
                invoice_uom_id_to_write = False
                intrastat_uom_id_to_write = False
                partner_country_id_to_write = False
                intrastat_code_to_write = False
                intrastat_code_id_to_write = False
                weight_to_write = False
                product_country_origin_id_to_write = False
                transport_to_write = False
                department_to_write = False

            if intrastat_uom_id and intrastat_uom_id != invoice_uom_id:
                raise osv.except_osv(_('Error :'), _("On invoice %s, on one of the products with HS code %s, the unit of measure on invoice and on the intrastat code are different. We don't handle this scenario for the moment."%(invoice_number, intrastat_code)))
           # TODO : ça crashe quand les valeurs "integer" valent false -> à tester !
            # Idem pr intrastat_uom et invoice_uom ???
            line_obj.create(cr, uid, {
                'parent_id': ids[0],
                'invoice_id': invoice_id,
                'quantity': quantity_to_write,
                'invoice_uom_id': invoice_uom_id_to_write,
                'intrastat_uom_id': intrastat_uom_id_to_write,
                'partner_country_id': partner_country_id_to_write,
                'intrastat_code': intrastat_code_to_write,
                'intrastat_code_id': intrastat_code_id_to_write,
                'weight': weight_to_write,
                'amount_invoice_currency': int(round(amount_invoice_currency, 0)),
                'amount_company_currency': int(round(amount_company_currency, 0)),
                'invoice_currency_id': invoice_currency_id,
                'product_country_origin_id': product_country_origin_id_to_write,
                'transport': transport_to_write,
                'department': department_to_write,
                'intrastat_type_id': intrastat_type_id,
                'procedure_code': procedure_code,
                'transaction_code': transaction_code,
                'partner_vat': partner_vat_to_write,
                'partner_id': partner_id,
                    }, context=context)
        return None

    def generate_product_lines_from_picking(self, cr, uid, ids, context=None):
        # used to have the lines for repairs
        print "generate_product_lines_from_picking ids=", ids
        intrastat = self.browse(cr, uid, ids[0], context=context)
        self.pool.get('report.intrastat.common')._check_generate_lines(cr, uid, ids, intrastat, context=context)
        # not needed when type = export and oblig_level = simplified, cf p26 du BOD
        if intrastat.type == 'export' and intrastat.obligation_level == 'simplified':
            raise osv.except_osv(_('Error :'), "You don't need to get lines from picking for an export DEB in Simplified obligation level")

        line_obj = self.pool.get('report.intrastat.product.line')
        line_remove_ids = line_obj.search(cr, uid, [('parent_id', '=', ids[0]), ('picking_id', '!=', False)], context=context)
        print "line_remove", line_remove_ids
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if line_remove_ids:
            line_obj.unlink(cr, uid, line_remove_ids, context=context)
        print "New we start to generate new lines"
        pick_obj = self.pool.get('stock.picking')
        pick_type = False
        if intrastat.type == 'import':
            pick_type = 'in'
        if intrastat.type == 'export':
            pick_type = 'out'
        picking_ids = pick_obj.search(cr, uid, [('type', '=', pick_type), ('date_done', '<=', intrastat.end_date), ('date_done', '>=', intrastat.start_date), ('invoice_state', '=', 'none'), ('state', 'not in', ('draft', 'waiting', 'confirmed', 'assigned', 'cancel'))], context=context)  # state = dernière étape du workflow
        print "picking_ids =", picking_ids
        for picking in pick_obj.browse(cr, uid, picking_ids, context=context):
            print "PICKING =", picking.name
            if not picking.address_id.country_id.intrastat:
                continue
            # TODO : regrouper si
# - même intrastat_id, même pays d'origine, même uom
            for move_line in picking.move_lines:
                if move_line.product_id.type not in ('product', 'consu'):
                    continue

                if move_line.product_id.exclude_from_intrastat:
                    continue

                if move_line.state <> 'done':
                    continue

                if not move_line.product_qty:
                    continue # TODO : info/warning pop-up ??
                else:
                    quantity_to_write = str(int(round(move_line.product_qty, 0)))
                #TODO : we can't just read cost price, we have to call the dedicated function
# because other it doesn't take into account the variants
#                if not move_line.product_id.standard_price: # = "valeur marchande" ???
#                    raise osv.except_osv(_('Error :'), 'Product %s, used on picking %s, has no cost price !'%(move_line.product_id.name, picking.name))
#                else:
                amount_company_currency_to_write = int(round(move_line.product_id.standard_price * move_line.product_qty, 0))

                # round(False) = 0.0 -> so we can't use try/except
                if not move_line.product_id.weight_net:
                    raise osv.except_osv(_('Error :'), _('Missing net weight on product %s used on picking %s.'%(move_line.product_id.name, picking.name)))
                else:
                    weight_to_write = str(int(round(move_line.product_id.weight_net * move_line.product_qty, 0)))
                if not move_line.product_uom:
                    raise osv.except_osv(_('Error :'), _('Missing unit of measure on one of the move lines with product %s of picking %s.'%(move_line.product_id.name, picking.name)))
                else:
                    invoice_uom_id_to_write = move_line.product_uom.id # TODO : bien sûr que c ce champ et pas product_uos ????
                if not move_line.product_id.intrastat_id:
                    raise osv.except_osv(_('Error :'), 'Missing H.S. code on product %s, used on picking %s !'%(move_line.product_id.name, picking.name))
                else:
                    intrastat_code_id_to_write = move_line.product_id.intrastat_id.id

                if not move_line.product_id.intrastat_id.intrastat_code:
                    raise osv.except_osv(_('Error :'), 'Missing intrastat code on H.S. code %s (%s)!'%(move_line.product_id.intrastat_id.name, move_line.product_id.intrastat_id.description))
                else:
                    intrastat_code_to_write = move_line.product_id.intrastat_id.intrastat_code
                if not move_line.product_id.intrastat_id.intrastat_uom_id:
                    intrastat_uom_id_to_write = False
                else:
                    intrastat_uom_id_to_write = move_line.product_id.intrastat_id.intrastat_uom_id.id
                print "picking.address_id.name = ", picking.address_id.name
                print "picking.address_id.partner_id.name = ", picking.address_id.partner_id.name
                if not picking.address_id.country_id:
                    raise osv.except_osv(_('Error :'), "Missing country on partner address '%s' used on picking %s !"%(picking.address_id.name, picking.name))
                else:
                    partner_country_id_to_write = picking.address_id.country_id.id

                if not picking.address_id.partner_id:
                    raise osv.except_osv(_('Error :'), "Partner address '%s' used on picking %s is not linked to a partner !"%(move_line.address_id.name, picking.name))
                else:
                    partner_id_to_write = picking.address_id.partner_id.id


                # The origin country should only be declated on Import
                if intrastat.type == 'export':
                    product_country_origin_id_to_write = False
                elif not move_line.product_id.country_id:
                    raise osv.except_osv(_('Error :'), 'Missing country of origin on product %s, used on picking %s !'%(move_line.product_id.name, picking.name))
                else:
                    product_country_origin_id_to_write = move_line.product_id.country_id.id


                # We don't need to declare the VAT number
                partner_vat_to_write = False


                if not picking.intrastat_transport:
                    try: transport_to_write = intrastat.company_id.default_intrastat_transport # TODO : pas de champ company_id !!!
                    except: raise osv.except_osv(_('Error :'), _('Mode of transport is not set on invoice %s nor the default mode of transport for the company %s.' %(invoice_number, intrastat.company_id.name)))
                else:
                    transport_to_write = picking.intrastat_transport

# TODO
#            if not department:
                try: department_to_write = user.company_id.default_intrastat_department
                except: raise osv.except_osv(_('Error :'), _('Missing default department for the company %s.' %(user.company_id.name)))

                intrastat_type_id_29 = self.pool.get('report.intrastat.type').search(cr, uid, [('procedure_code', '=', '29')], context=context)
                if len(intrastat_type_id_29) <> 1:
                    raise osv.except_osv(_('Error :'), _('We should only have one intrastat type with procedure code = 29.'))
                intrastat_type_id_to_write= intrastat_type_id_29[0]

#                department_to_write = '93'

                line_obj.create(cr, uid, {
                'parent_id': ids[0],
                'picking_id': picking.id,
                'quantity': quantity_to_write,
                'invoice_uom_id': invoice_uom_id_to_write, # rename source_uom_id ???
                'intrastat_uom_id': intrastat_uom_id_to_write,
                'partner_country_id': partner_country_id_to_write,
                'intrastat_code': intrastat_code_to_write,
                'intrastat_code_id': intrastat_code_id_to_write,
                'weight': weight_to_write,
                'amount_company_currency': amount_company_currency_to_write,
                'product_country_origin_id': product_country_origin_id_to_write,
                'transport': transport_to_write,
                'department': department_to_write,
                'intrastat_type_id': intrastat_type_id_to_write, #TODO
                'procedure_code': '29', #TODO
                'transaction_code': '41', #TODO
                'partner_vat': partner_vat_to_write,
                'partner_id': partner_id_to_write,
                        }, context=context)

        return None

    def done(self, cr, uid, ids, context=None):
        if len(ids) != 1: raise osv.except_osv(_('Error :'), 'Hara kiri in done')
        self.write(cr, uid, ids[0], {'state': 'done', 'date_done': datetime.strftime(datetime.today(), '%Y-%m-%d %H:%M:%S')}, context=context)
        return None

    def back2draft(self, cr, uid, ids, context=None):
        if len(ids) != 1: raise osv.except_osv(_('Error :'), 'Hara kiri in back2draft')
        self.write(cr, uid, ids[0], {'state': 'draft'}, context=context)
        return None


    def generate_xml(self, cr, uid, ids, context=None):
        '''Generate the INSTAT XML file export.'''
        print "generate_xml ids=", ids
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
        if my_company_currency == 'EUR': # already tested in generate_lines function !
            currency_code.text = my_company_currency
        else:
            raise osv.except_osv(_('Error :'), _("Company currency must be 'EUR' for the XML file export, but it is currently '%s'." %my_company_currency))

        # THEN, the fields which vary from a line to the next
        line = 0
        for pline in intrastat.intrastat_line_ids:
            line += 1 #increment line number
            print "pline.parent_type =", pline.parent_type
            print "line =", line
            try: intrastat_type = self.pool.get('report.intrastat.type').read(cr, uid, pline.intrastat_type_id.id, ['is_fiscal_only'], context=context)
            except: raise osv.except_osv(_('Error :'), _('Missing Intrastat type id on line %d.' %line))
            item = etree.SubElement(declaration, 'Item')
            item_number = etree.SubElement(item, 'itemNumber')
            item_number.text = str(line)
            # START of elements which are only required in "detailed" level
            if intrastat.obligation_level == 'detailed' and not intrastat_type['is_fiscal_only']:
                cn8 = etree.SubElement(item, 'CN8')
                cn8_code = etree.SubElement(cn8, 'CN8Code')
                try: cn8_code.text = pline.intrastat_code
                except: raise osv.except_osv(_('Error :'), _('Missing Intrastat code on line %d.' %line))
                # We fill SUCode only if the H.S. code requires it
                if pline.intrastat_uom_id:
                    su_code = etree.SubElement(cn8, 'SUCode')
                    try: su_code.text = pline.intrastat_uom_id.intrastat_label
                    except: raise osv.except_osv(_('Error :'), _('Missing Intrastat UoM on line %d.' %line))
                    destination_country = etree.SubElement(item, 'MSConsDestCode')
                    if intrastat.type == 'import': country_origin = etree.SubElement(item, 'countryOfOriginCode')
                    weight = etree.SubElement(item, 'netMass')
                    quantity_in_SU = etree.SubElement(item, 'quantityInSU')

                    try: quantity_in_SU.text = pline.quantity
                    except: raise osv.except_osv(_('Error :'), _('Missing quantity on line %d.' %line))
                else:
                    destination_country = etree.SubElement(item, 'MSConsDestCode')
                    if intrastat.type == 'import': country_origin = etree.SubElement(item, 'countryOfOriginCode')
                    weight = etree.SubElement(item, 'netMass')
                try: destination_country.text = pline.partner_country_code
                except: raise osv.except_osv(_('Error :'), _('Missing partner country on line %d.' %line))
                if intrastat.type == 'import':
                    try: country_origin.text = pline.product_country_origin_code
                    except: raise osv.except_osv(_('Error :'), _('Missing product country of origin on line %d.' %line))
                try: weight.text = pline.weight
                except: raise osv.except_osv(_('Error :'), _('Missing weight on line %d.' %line))

            # START of elements that are part of all DEBs
            invoiced_amount = etree.SubElement(item, 'invoicedAmount')
            try:
                invoiced_amount.text = str(pline.amount_company_currency)
            except: raise osv.except_osv(_('Error :'), _('Missing fiscal value on line %d.' %line))
            # Partner VAT is only declared for export when code régime <> 29
            if intrastat.type == 'export' and pline.procedure_code <> '29':
                partner_id = etree.SubElement(item, 'partnerId')
                try: partner_id.text = pline.partner_vat.replace(' ', '')
                except: raise osv.except_osv(_('Error :'), _('Missing VAT number for partner "%s".' %pline.partner_name))
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
                except: raise osv.except_osv(_('Error :'), _('Transaction code on line %d should have 2 digits.' %line))
                mode_of_transport_code = etree.SubElement(item, 'modeOfTransportCode')
                try: mode_of_transport_code.text = str(pline.transport)
                except: raise osv.except_osv(_('Error :'), _('Mode of transport is not set on line %d.' %line))
                region_code = etree.SubElement(item, 'regionCode')
                try: region_code.text = pline.department
                except: raise osv.except_osv(_('Error :'), _('Department code is not set on line %d.' %line))

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
    _order = 'invoice_id, picking_id'
    _columns = {
        'parent_id': fields.many2one('report.intrastat.product', 'Intrastat product ref', ondelete='cascade', select=True, readonly=True),
# Fields.related
        'parent_type' : fields.related('parent_id', 'type', type='string', relation='report.intrastat.product', string='Declaration type', readonly=True),
        'state' : fields.related('parent_id', 'state', type='string', relation='report.intrastat.product', string='State', readonly=True),
        'company_id': fields.related('parent_id', 'company_id', type='many2one', relation='res.company', string="Company", readonly=True),
        'company_currency_id': fields.related('company_id', 'currency_id', type='many2one', relation='res.currency', string="Company currency", readonly=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice ref', readonly=True),
        'picking_id': fields.many2one('stock.picking', 'Picking ref', readonly=True),
        'quantity': fields.char('Quantity', size=10, states={'done':[('readonly',True)]}),
        'invoice_uom_id': fields.many2one('product.uom', 'Invoice UoM', readonly=True),
        'intrastat_uom_id': fields.many2one('product.uom', 'Intrastat UoM', states={'done':[('readonly',True)]}),
        'partner_country_id': fields.many2one('res.country', 'Partner country', states={'done':[('readonly',True)]}),
        'partner_country_code' : fields.related('partner_country_id', 'code', type='string', relation='res.country', string='Partner country', readonly=True),
        'intrastat_code': fields.char('Intrastat code', size=9, states={'done':[('readonly',True)]}),
        'intrastat_code_id': fields.many2one('report.intrastat.code', 'Intrastat code (not used in XML)', states={'done':[('readonly',True)]}),
        # Weight should be an integer... but I want to be able to display nothing in
        # tree view when the value is False (if weight is an integer, a False value would
        # be displayed as 0), that's why weight is now a char !
        'weight': fields.char('Weight', size=10, states={'done':[('readonly',True)]}),
        'amount_invoice_currency': fields.integer('Fiscal value in invoice currency', readonly=True),
        'amount_company_currency': fields.integer('Fiscal value in company currency', required=True, states={'done':[('readonly',True)]}),
        'invoice_currency_id': fields.many2one('res.currency', "Invoice currency", readonly=True),
        'product_country_origin_id' : fields.many2one('res.country', 'Product country of origin', states={'done':[('readonly',True)]}),
        'product_country_origin_code' : fields.related('product_country_origin_id', 'code', type='string', relation='res.country', string='Product country of origin', readonly=True),
        'transport' : fields.selection([(1, 'Transport maritime'), \
            (2, 'Transport par chemin de fer'), \
            (3, 'Transport par route'), \
            (4, 'Transport par air'), \
            (5, 'Envois postaux'), \
            (7, 'Installations de transport fixes'), \
            (8, 'Transport par navigation intérieure'), \
            (9, 'Propulsion propre')], 'Type of transport', states={'done':[('readonly',True)]}),
        'department' : fields.char('Department', size=2, states={'done':[('readonly',True)]}),
        'intrastat_type_id' : fields.many2one('report.intrastat.type', 'Intrastat type', states={'done':[('readonly',True)]}),
# Is fiscal_only is not fields.related because, if obligation_level = simplified, is_fiscal_only is always true
        'is_fiscal_only' : fields.boolean('Intrastat type'),
        'procedure_code': fields.char('Procedure code', size=2, required=True, states={'done':[('readonly',True)]}),
        'transaction_code': fields.char('Transaction code', size=2, states={'done':[('readonly',True)]}),
        'partner_vat': fields.char('Partner VAT', size=32, states={'done':[('readonly',True)]}),
        'partner_id': fields.many2one('res.partner', 'Partner name', states={'done':[('readonly',True)]}),
        'date_invoice' : fields.related('invoice_id', 'date_invoice', type='date', relation='account.invoice', string='Invoice date', readonly=True),
    }

    def _code_check(self, cr, uid, ids):
        for lines in self.read(cr, uid, ids, ['procedure_code', 'transaction_code']):
            self.pool.get('report.intrastat.type').real_code_check(lines)
        return True

    def _integer_check(self, cr, uid, ids):
        for values in self.read(cr, uid, ids, ['weight', 'quantity']):
            if values['weight'] and not values['weight'].isdigit():
                raise osv.except_osv(_('Error :'), _('Weight must be an integer.'))
            if values['quantity'] and not values['quantity'].isdigit():
                raise osv.except_osv(_('Error :'), _('Quantity must be an integer.'))
        return True

    _constraints = [
#        (_intrastat_code, "The 'Intrastat code' should have exactly 8 or 9 digits.", ['intrastat_code']),
        (_code_check, "Error msg in raise", ['procedure_code', 'transaction_code']),
        (_integer_check, "Error msg in raise", ['weight', 'quantity']),
    ]


    def partner_on_change(self, cr, uid, ids, partner_id=False):
        result = {}
        result['value'] = {}
        if partner_id:
            company = self.pool.get('res.partner').read(cr, uid, partner_id, ['vat'])
            result['value'].update({'partner_vat': company['vat']})
        return result

    def intrastat_code_on_change(self, cr, uid, ids, intrastat_code_id=False):
        result = {}
        result['value'] = {}
        if intrastat_code_id:
            intrastat_code = self.pool.get('report.intrastat.code').read(cr, uid, intrastat_code_id, ['intrastat_code'])
            result['value'].update({'intrastat_code': intrastat_code['intrastat_code']})
        return result

    def intrastat_type_on_change(self, cr, uid, ids, intrastat_type_id=False, type=False, obligation_level=False):
        result = {}
        result['value'] = {}
        print "parent.type =", type
        print "parent.obligation_level =", obligation_level
        if type:
            result['value'].update({'parent_type': type})
        if obligation_level=='simplified':
            result['value'].update({'is_fiscal_only': True})
        if intrastat_type_id:
            intrastat_type = self.pool.get('report.intrastat.type').read(cr, uid, intrastat_type_id, ['procedure_code', 'transaction_code', 'is_fiscal_only'])
            result['value'].update({'procedure_code': intrastat_type['procedure_code'], 'transaction_code': intrastat_type['transaction_code']})
            if obligation_level=='detailed':
                result['value'].update({'is_fiscal_only': intrastat_type['is_fiscal_only']})

        if result['value'].get('is_fiscal_only', False):
            result['value'].update({
                'quantity': False,
                'invoice_uom_id': False,
                'intrastat_uom_id': False,
                'partner_country_id': False,
                'intrastat_code': False,
                'intrastat_code_id': False,
                'weight': False,
                'product_country_origin_id': False,
                'transport': False,
                'department': False
            })
        print "intrastat_type_on_change res=", result
        return result



report_intrastat_product_line()

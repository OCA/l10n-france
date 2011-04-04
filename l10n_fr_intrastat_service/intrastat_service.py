# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat service module for OpenERP (DES)
#    Copyright (C) 2010-2011 Akretion (http://www.akretion.com/). All rights reserved.
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
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from tools.translate import _

class report_intrastat_service(osv.osv):
    _name = "report.intrastat.service"
    _order = "start_date"
    _rec_name = "start_date"
    _description = "Intrastat report for services"

    def _compute_numbers(self, cr, uid, ids, name, arg, context=None):
        print "SERVICE _compute numbers start ids=", ids
        return self.pool.get('report.intrastat.common')._compute_numbers(cr, uid, ids, self, context=context)


    def _compute_end_date(self, cr, uid, ids, name, arg, context=None):
        print "SERVICE _compute_end_date START ids=", ids
        return self.pool.get('report.intrastat.common')._compute_end_date(cr, uid, ids, self, context=context)


    def _get_intrastat_from_service_line(self, cr, uid, ids, context=None):
        print "invalidation function CALLED !!!"
        return self.pool.get('report.intrastat.service').search(cr, uid, [('intrastat_line_ids', 'in', ids)], context=context)

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True, states={'done':[('readonly',True)]}, help="Related company."),
        'start_date': fields.date('Start date', required=True, states={'done':[('readonly',True)]}, help="Start date of the declaration. Must be the first day of a month."),
        'end_date': fields.function(_compute_end_date, method=True, type='date', string='End date', store={
            'report.intrastat.service': (lambda self, cr, uid, ids, c={}: ids, ['start_date'], 20)
        }, help="End date for the declaration. Must be the last day of the month of the start date."),
        'intrastat_line_ids': fields.one2many('report.intrastat.service.line', 'parent_id', 'Report intrastat service lines', states={'done':[('readonly',True)]}),
        'num_lines': fields.function(_compute_numbers, method=True, type='integer', multi='numbers', string='Number of lines', store={
            'report.intrastat.service.line': (_get_intrastat_from_service_line, ['parent_id'], 20),
            }, help="Number of lines in this declaration."),
        'total_amount': fields.function(_compute_numbers, method=True, digits=(16,0), multi='numbers', string='Total amount', store={
            'report.intrastat.service.line': (_get_intrastat_from_service_line, ['amount_company_currency', 'parent_id'], 20),
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
        # february the DES of January
        'start_date': lambda *a: datetime.strftime(datetime.today() + relativedelta(day=1, months=-1), '%Y-%m-%d'),
        'state': lambda *a: 'draft',
        'company_id': lambda self, cr, uid, context: \
         self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id,
        }

#TODO : add check on date of children lines ?
    def _check_start_date(self, cr, uid, ids, context=None):
        return self.pool.get('report.intrastat.common')._check_start_date(cr, uid, ids, self, context=context)

    _constraints = [
        (_check_start_date, "Start date must be the first day of a month", ['start_date']),
    ]

    _sql_constraints = [
        ('date_uniq', 'unique(start_date, company_id)', 'You have already created a DES for this month !'),
    ]

    def generate_service_lines(self, cr, uid, ids, context=None):
        print "generate lines, ids=", ids
        intrastat = self.browse(cr, uid, ids[0], context=context)
        self.pool.get('report.intrastat.common')._check_generate_lines(cr, uid, ids, intrastat, context=context)
        # Get current service lines and delete them
        line_remove = self.read(cr, uid, ids[0], ['intrastat_line_ids'], context=context)
        print "line_remove", line_remove
        if line_remove['intrastat_line_ids']:
            self.pool.get('report.intrastat.service.line').unlink(cr, uid, line_remove['intrastat_line_ids'], context=context)
        sql = '''
        select
            min(inv_line.id) as id,
            company.id,
            inv.id as invoice_id,
            inv.currency_id as invoice_currency_id,
            prt.vat as partner_vat,
            inv.partner_id as partner_id,
            res_currency_rate.rate as invoice_currency_rate,
            sum(case when inv.type = 'out_refund'
                then inv_line.price_subtotal * (-1)
                when inv.type = 'out_invoice'
                then inv_line.price_subtotal
               end) as amount_invoice_currency,
            sum(case when company.currency_id != inv.currency_id and res_currency_rate.rate is not null
                then
                  case when inv.type = 'out_refund'
                    then round(inv_line.price_subtotal/res_currency_rate.rate * (-1), 2)
                  when inv.type = 'out_invoice'
                    then round(inv_line.price_subtotal/res_currency_rate.rate, 2)
                  end
                when company.currency_id = inv.currency_id
                then
                   case when inv.type = 'out_refund'
                     then inv_line.price_subtotal * (-1)
                   when inv.type = 'out_invoice'
                     then inv_line.price_subtotal
                   end
                end) as amount_company_currency,
                company.currency_id as company_currency_id

        from account_invoice inv
            left join account_invoice_line inv_line on inv_line.invoice_id=inv.id
            left join (product_template pt
                left join product_product pp on pp.product_tmpl_id = pt.id
                )
            on (inv_line.product_id = pt.id)
            left join (res_partner_address inv_address
                left join res_country inv_country on (inv_country.id = inv_address.country_id))
            on (inv_address.id = inv.address_invoice_id)
            left join res_partner prt on inv.partner_id = prt.id
            left join report_intrastat_type intr on inv.intrastat_type_id = intr.id
            left join res_currency_rate on (inv.currency_id = res_currency_rate.currency_id and inv.date_invoice = res_currency_rate.name)
            left join res_company company on inv.company_id=company.id

        where
            inv.type in ('out_invoice', 'out_refund')
            and inv.state in ('open', 'paid')
            and inv_line.product_id is not null
            and inv_line.price_subtotal != 0
            and inv_country.intrastat = true
            and pt.type = 'service'
            and pt.exclude_from_intrastat is not true
            and intr.type != 'other'
            and company.id = %s
            and inv.date_invoice >= %s
            and inv.date_invoice <= %s

        group by company.id, inv.currency_id, prt.vat, inv.partner_id, inv.id, invoice_currency_rate, company_currency_id
        '''
        # Execute the big SQL query to get all service lines
        cr.execute(sql, (intrastat.company_id.id, intrastat.start_date, intrastat.end_date))
        res_sql = cr.fetchall()
        print "res_sql=", res_sql
        line_obj = self.pool.get('report.intrastat.service.line')
        for id, company_id, invoice_id, invoice_currency_id, partner_vat, partner_id, invoice_currency_rate, amount_invoice_currency, amount_company_currency, company_currency_id in res_sql:
            print "amount_invoice_currency =", amount_invoice_currency
            print "amount_company_currency =", amount_company_currency
            # Store the service lines
            line_obj.create(cr, uid, {
                'parent_id': ids[0],
                'invoice_id': invoice_id,
                'partner_vat': partner_vat,
                'partner_id': partner_id,
                'amount_invoice_currency': int(round(amount_invoice_currency, 0)),
                'invoice_currency_id': invoice_currency_id,
                'amount_company_currency': int(round(amount_company_currency, 0)),
                'company_currency_id': company_currency_id,
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
        print "generate xml ids=", ids
        import des_xsd
        from lxml import etree
        intrastat = self.browse(cr, uid, ids[0], context=context)
        start_date_str = intrastat.start_date
        end_date_str = intrastat.end_date
        start_date_datetime = datetime.strptime(start_date_str, '%Y-%m-%d')

        self.pool.get('report.intrastat.common')._check_generate_xml(cr, uid, ids, intrastat, context=context)

        my_company_vat = intrastat.company_id.partner_id.vat.replace(' ', '')

        # Tech spec of XML export are available here :
        # https://pro.douane.gouv.fr/download/downloadUrl.asp?file=PubliwebBO/fichiers/DES_DTIPlus.pdf
        root = etree.Element('fichier_des')
        decl = etree.SubElement(root, 'declaration_des')
        num_des = etree.SubElement(decl, 'num_des')
        num_des.text = datetime.strftime(start_date_datetime, '%Y%m')
        num_tva = etree.SubElement(decl, 'num_tvaFr')
        num_tva.text = my_company_vat
        mois_des = etree.SubElement(decl, 'mois_des')
        mois_des.text = datetime.strftime(start_date_datetime, '%m') # month 2 digits
        an_des = etree.SubElement(decl, 'an_des')
        an_des.text = datetime.strftime(start_date_datetime, '%Y')
        line = 0
        # we now go through each service line
        for sline in intrastat.intrastat_line_ids:
            line += 1 # increment line number
            ligne_des = etree.SubElement(decl, 'ligne_des')
            numlin_des = etree.SubElement(ligne_des, 'numlin_des')
            numlin_des.text = str(line)
            valeur = etree.SubElement(ligne_des, 'valeur')
            # We take amount_company_currency, to be sure we have amounts in EUR
            valeur.text = str(sline.amount_company_currency)
            partner_des = etree.SubElement(ligne_des, 'partner_des')
            try: partner_des.text = sline.partner_vat.replace(' ', '')
            except: raise osv.except_osv(_('Error :'), _('Missing VAT number for partner "%s".'%sline.partner_id.name))
        xml_string = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
        print "xml_string", xml_string

        # We now validate the XML file against the official XML Schema Definition
        self.pool.get('report.intrastat.common')._check_xml_schema(cr, uid, root, xml_string, des_xsd.des_xsd, context=context)
        # Attach the XML file
        self.pool.get('report.intrastat.common')._attach_xml_file(cr, uid, ids, self, xml_string, start_date_datetime, 'des', context=context)
        return None


report_intrastat_service()

class report_intrastat_service_line(osv.osv):
    _name = "report.intrastat.service.line"
    _description = "Lines of intrastat service declaration (DES)"
    _rec_name = "partner_vat"
    _order = 'invoice_id'
    _columns = {
        'parent_id': fields.many2one('report.intrastat.service', 'Intrastat service ref', ondelete='cascade', select=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice ref', readonly=True),
        'partner_vat': fields.char('Customer VAT', size=32, readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner name', readonly=True),
        'date_invoice' : fields.related('invoice_id', 'date_invoice', type='date', relation='account.invoice', string='Invoice date', readonly=True),
        'amount_invoice_currency': fields.integer('Amount in invoice cur.', readonly=True),
        'invoice_currency_id': fields.many2one('res.currency', "Invoice currency", readonly=True),
        'amount_company_currency': fields.integer('Amount in company cur.', readonly=True),
        'company_currency_id': fields.many2one('res.currency', "Company currency", readonly=True),
    }

report_intrastat_service_line()


# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat service module for OpenERP
#    The service declaration (DES i.e. Déclaration Européenne de Services)
#    was in introduced in France on January 1st 2010
#    Copyright (C) 2010-2011 Akretion (http://www.akretion.com/). All rights reserved.
#       Code written by Alexis de Lattre <alexis.delattre@akretion.com>
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

#TODO
# Arrondis
# Dépôt DES fait le .... sur pro douane
# faire un multi sur les 2 champs calculés de report_intrastat_service

from osv import osv, fields
from tools.sql import drop_view_if_exists
import netsvc
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from tools.translate import _

class report_intrastat_service(osv.osv):
    _name = "report.intrastat.service"
    _order = "start_date"
    _rec_name = "start_date"
    _description = "Intrastat report for service"


    def _compute_num_lines(self, cr, uid, ids, name, arg, context=None):
        print "START _compute_num_lines"
        result = {}
        for intrastat in self.browse(cr, uid, ids, context=context):
            result[intrastat.id] = 0
            for line in intrastat.service_line_ids:
                result[intrastat.id] += 1
        print "_compute_num_lines res = ", result
        return result

    def _compute_total_amount(self, cr, uid, ids, name, arg, context=None):
        print "_compute_total_amount START ids=", ids
        result = {}
        for intrastat in self.browse(cr, uid, ids, context=context):
            result[intrastat.id] = 0.0
            for line in intrastat.service_line_ids:
                result[intrastat.id] += line.amount_company_currency
        print "_compute_total_amount res = ", result
        return result

    def _compute_end_date(self, cr, uid, ids, name, arg, context=None):
        print "_compute_end_date START ids=", ids
        result = {}
        for intrastat in self.browse(cr, uid, ids, context=context):
            start_date_datetime = datetime.strptime(intrastat.start_date, '%Y-%m-%d')
            end_date_str = datetime.strftime(start_date_datetime + relativedelta(day=31), '%Y-%m-%d')
            result[intrastat.id] = end_date_str
        print "_compute_end_date res=", result
        return result
 

    def _get_intrastat_from_service_line(self, cr, uid, ids, context=None):
        print "invalidation function CALLED !!!"
        return self.pool.get('report.intrastat.service').search(cr, uid, [('service_line_ids', 'in', ids)], context=context)

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True, states={'done':[('readonly',True)]}, help="Related company."),
        'start_date': fields.date('Start date', required=True, states={'done':[('readonly',True)]}, help="Start date of the declaration. Must be the first day of a month."),
        'end_date': fields.function(_compute_end_date, method=True, type='date', string='End date', store=True, help="End date for the declaration. Must be the last day of the month of the start date."),
        'service_line_ids': fields.one2many('report.intrastat.service.line', 'parent_id', 'Report intrastat service lines', states={'done':[('readonly',True)]}),
        'num_lines': fields.function(_compute_num_lines, method=True, type='integer', string='Number of lines', store={
            'report.intrastat.service.line': (_get_intrastat_from_service_line, ['parent_id'], 20),
            }, help="Number of lines in this declaration."),
        'total_amount': fields.function(_compute_total_amount, method=True, digits=(16,0), string='Total amount', store={
            'report.intrastat.service.line': (_get_intrastat_from_service_line, ['amount_company_currency', 'parent_id'], 20),
                }, help="Total amount in company currency of the declaration."),
        'state' : fields.selection([
            ('draft','Draft'),
            ('done','Done'),
        ], 'State', select=True, readonly=True, help="State of the declaration. When the state is set to 'Done', the parameters become read-only."),
        'notes' : fields.text('Notes', help="You can add some comments here if you want.")
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
        '''Check that the start date if the first day of the month'''
        for cur_id in ids:
            date_to_check = self.read(cr, uid, cur_id, ['start_date'], context=context)['start_date']
            datetime_to_check = datetime.strptime(date_to_check, '%Y-%m-%d')
            if datetime_to_check.day != 1:
                return False
        return True

    _constraints = [
        (_check_start_date, "Start date must be the first day of a month", ['start_date']),
    ]

    _sql_constraints = [
        ('date_uniq', 'unique(start_date, company_id)', 'You have already created a DES for this month !'),
    ]

    def generate_service_lines(self, cr, uid, ids, context=None):
        print "generate lines, ids=", ids
#TODO delete service lines
        if len(ids) != 1:
            raise osv.except_osv(_('Error :'), _('Hara kiri in generate_service_lines'))
        # Get current lines and delete them
        line_remove = self.read(cr, uid, ids[0], ['service_line_ids'], context=context)
        print "line_remove", line_remove
        if line_remove['service_line_ids']:
            self.pool.get('report.intrastat.service.line').unlink(cr, uid, line_remove['service_line_ids'], context=context)
        #TODO : check on company
        sql = '''
        select
            min(inv_line.id) as id,
            company.id,
            inv.name as name,
            inv.number as invoice_number,
            inv.date_invoice,
            inv.currency_id as invoice_currency_id,
            prt.vat as partner_vat,
            prt.name as partner_name,
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

        group by company.id, inv.date_invoice, inv.number, inv.currency_id, prt.vat, prt.name, inv.name, invoice_currency_rate, company_currency_id
        '''
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company_id = str(user.company_id.id)
        print "company_id =", company_id
        dates = self.read(cr, uid, ids[0], ['start_date', 'end_date'], context=context)
        start_date_str = dates['start_date']
        end_date_str = dates['end_date']
        print "START date", start_date_str
        print "END date", end_date_str
        cr.execute(sql, (company_id, start_date_str, end_date_str))
        res_sql = cr.fetchall()
        print "res_sql=", res_sql
        line_obj = self.pool.get('report.intrastat.service.line')
        for id, name, company_id, invoice_number, date_invoice, invoice_currency_id, partner_vat, partner_name, invoice_currency_rate, amount_invoice_currency, amount_company_currency, company_currency_id in res_sql:
            line_obj.create(cr, uid, {
                'parent_id': ids[0],
                'name': name,
                'invoice_number': invoice_number,
                'partner_vat': partner_vat,
                'partner_name': partner_name,
                'date_invoice': date_invoice,
                'amount_invoice_currency': amount_invoice_currency,
                'invoice_currency_id': invoice_currency_id,
                'amount_company_currency': amount_company_currency,
                'company_currency_id': company_currency_id,
                    }, context=context)
        return None


    def done(self, cr, uid, ids, context=None):
        if len(ids) != 1:
            raise osv.except_osv(_('Error :'), _('Hara kiri in generate_xml'))
        self.write(cr, uid, ids[0], {'state': 'done'}, context=context)
        return None

    def back2draft(self, cr, uid, ids, context=None):
        if len(ids) != 1:
            raise osv.except_osv(_('Error :'), _('Hara kiri in generate_xml'))
        self.write(cr, uid, ids[0], {'state': 'draft'}, context=context)
        return None


    def generate_xml(self, cr, uid, ids, context=None):
        print "generate xml ids=", ids
        import des_xsd
        from lxml import etree
        import base64
        if len(ids) != 1:
            raise osv.except_osv(_('Error :'), _('Hara kiri in generate_xml'))
        dates = self.read(cr, uid, ids[0], ['start_date', 'end_date'], context=context)
        start_date_str = dates['start_date']
        end_date_str = dates['end_date']
        start_date_datetime = datetime.strptime(start_date_str, '%Y-%m-%d')

        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)

        if not user.company_id.currency_id.code == 'EUR':
            raise osv.except_osv(_('Error :'), _('The company currency must be "EUR", but is currently "%s".'%user.company_id.currency_id.code))

        if not user.company_id.partner_id.vat:
            raise osv.except_osv(_('Error :'), _('The VAT number is not set for the partner "%s".'%user.company_id.partner_id.name))
        my_company_vat = user.company_id.partner_id.vat.replace(' ', '')

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
        lines = self.pool.get('report.intrastat.service').browse(cr, uid, context['active_ids'], context=context)
        line = 0
        total_value_cc = 0
        # we now go through each service line
        for sline in self.browse(cr, uid, ids[0], context=context).service_line_ids:
            line += 1 # increment line number
            ligne_des = etree.SubElement(decl, 'ligne_des')
            numlin_des = etree.SubElement(ligne_des, 'numlin_des')
            numlin_des.text = str(line)
            valeur = etree.SubElement(ligne_des, 'valeur')
            # We take amount_company_currency, to be sure we have amounts in EUR
            value_cc = int(round(sline.amount_company_currency,0))
            total_value_cc += value_cc
            valeur.text= str(value_cc)
            partner_des = etree.SubElement(ligne_des, 'partner_des')
            try: partner_des.text = sline.partner_vat.replace(' ', '')
            except: raise osv.except_osv(_('Error :'), _('Missing VAT number for partner "%s".'%sline.partner_name))
        xml_string = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
        print "xml_string", xml_string

        # We now validate the XML file against the official XML Schema Definition
        official_des_xml_schema = etree.XMLSchema(etree.fromstring(des_xsd.des_xsd))
        try: official_des_xml_schema.assertValid(root)
        except Exception, e:   # if the validation of the XSD fails, we arrive here
            logger = netsvc.Logger()
            logger.notifyChannel('intrastat_service', netsvc.LOG_WARNING, "The XML file is invalid against the XSD")
            logger.notifyChannel('intrastat_service', netsvc.LOG_WARNING, xml_string)
            logger.notifyChannel('intrastat_service', netsvc.LOG_WARNING, e)
            raise osv.except_osv(_('Error :'), _('The generated XML file is not valid against the official XML schema. The generated XML file and the full error have been written in the server logs. Here is the exact error, which may give you an idea of the cause of the problem : ' + str(e)))
        #let's give a pretty name to the filename : <year-month_des.xml>
        filename = datetime.strftime(start_date_datetime, '%Y-%m') + '_des.xml'
        attach_name = 'DES ' + datetime.strftime(start_date_datetime, '%Y-%m')

        # Attach the XML file to the intrastat_service object
        attach_obj = self.pool.get('ir.attachment')
        if not context:
            context = {}
        context.update({'default_res_id' : ids[0], 'default_res_model': 'report.intrastat.service'})
        attach_id = attach_obj.create(cr, uid, {'name': attach_name, 'datas': base64.encodestring(xml_string), 'datas_fname': filename}, context=context)
        return None


report_intrastat_service()

class report_intrastat_service_line(osv.osv):
    _name = "report.intrastat.service.line"
    _description = "Lines of intrastat service declaration"
    _order = 'invoice_number'
    _columns = {
        'parent_id': fields.many2one('report.intrastat.service', 'Intrastat service ref', ondelete='cascade', select=True),
        'name': fields.char('Invoice description', size=64, readonly=True),
        'invoice_number': fields.char('Invoice number', size=32, readonly=True, select=True),
        'partner_vat': fields.char('Customer VAT', size=32, readonly=True),
        'partner_name': fields.char('Customer name', size=128, readonly=True),
        'date_invoice' : fields.date('Invoice date', readonly=True),
        'amount_invoice_currency': fields.integer('Amount in invoice cur.', readonly=True),
        'invoice_currency_id': fields.many2one('res.currency', "Invoice currency", readonly=True),
        'amount_company_currency': fields.integer('Amount in company cur.', readonly=True),
        'company_currency_id': fields.many2one('res.currency', "Company currency", readonly=True),
    }

report_intrastat_service_line()


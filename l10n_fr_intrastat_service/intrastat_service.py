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
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tools.translate import _

class report_intrastat_service(osv.osv):
    _name = "report.intrastat.service"
    _order = "start_date"
    _rec_name = "start_date"
    _description = "Intrastat report for services"

    def _compute_numbers(self, cr, uid, ids, name, arg, context=None):
        return self.pool.get('report.intrastat.common')._compute_numbers(cr, uid, ids, self, context=context)


    def _compute_end_date(self, cr, uid, ids, name, arg, context=None):
        return self.pool.get('report.intrastat.common')._compute_end_date(cr, uid, ids, self, context=context)


    def _get_intrastat_from_service_line(self, cr, uid, ids, context=None):
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
        'date_done' : fields.datetime('Date done', readonly=True, help="Last date when the intrastat declaration was converted to 'Done' state."),
        'notes' : fields.text('Notes', help="You can write some comments here if you want."),
    }

    _defaults = {
        # By default, we propose 'current month -1', because you prepare in
        # february the DES of January
        'start_date': lambda *a: datetime.strftime(datetime.today() + relativedelta(day=1, months=-1), '%Y-%m-%d'),
        'state': lambda *a: 'draft',
        'company_id': lambda self, cr, uid, context: \
         self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id,
        }


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
        line_obj = self.pool.get('report.intrastat.service.line')
        invoice_obj = self.pool.get('account.invoice')
        self.pool.get('report.intrastat.common')._check_generate_lines(cr, uid, intrastat, context=context)
        # Get current service lines and delete them
        line_remove = self.read(cr, uid, ids[0], ['intrastat_line_ids'], context=context)
        if line_remove['intrastat_line_ids']:
            line_obj.unlink(cr, uid, line_remove['intrastat_line_ids'], context=context)

        invoice_ids = invoice_obj.search(cr, uid, [
            ('type', 'in', ('out_invoice', 'out_refund')),
            ('date_invoice', '<=', intrastat.end_date),
            ('date_invoice', '>=', intrastat.start_date),
            ('state', 'in', ('open', 'paid')),
            ('company_id', '=', intrastat.company_id.id)
        ], order='date_invoice', context=context)
        print "invoice_ids=", invoice_ids
        for invoice in invoice_obj.browse(cr, uid, invoice_ids, context=context):

            if not invoice.address_invoice_id.country_id:
                raise osv.except_osv(_('Error :'), _("Missing country on partner address '%s' of partner '%s'.") %(invoice.address_invoice_id.name, invoice.address_invoice_id.partner_id.name))
            elif not invoice.address_invoice_id.country_id.intrastat:
                continue

            if not invoice.partner_id.vat:
                raise osv.except_osv(_('Error :'), _("Missing VAT number on partner '%s'.") %invoice.partner_id.name)
            else:
                partner_vat_to_write = invoice.partner_id.vat

            amount_invoice_currency_to_write = 0.0
            amount_company_currency_to_write = 0.0
            context['date'] = invoice.date_invoice

            for line in invoice.invoice_line:
                if not line.product_id:
                    continue

                if line.product_id.type <> 'service':
                    continue

                if line.product_id.exclude_from_intrastat:
                    continue

                if not line.quantity:
                    continue

                skip_this_line = False
                for line_tax in line.invoice_line_tax_id:
                    if line_tax.exclude_from_intrastat_if_present:
                        skip_this_line = True
                if skip_this_line:
                    continue

                if not line.price_subtotal:
                    continue
                else:
                    amount_invoice_currency_to_write += line.price_subtotal
                    if invoice.currency_id.code <> 'EUR':
                        amount_company_currency_to_write += self.pool.get('res.currency').compute(cr, uid, invoice.currency_id.id, intrastat.company_id.currency_id.id, line.price_subtotal, round=False, context=context)
                    else:
                        amount_company_currency_to_write += line.price_subtotal

            if amount_company_currency_to_write:
                if invoice.type == 'out_refund':
                    amount_invoice_currency_to_write = amount_invoice_currency_to_write * (-1)
                    amount_company_currency_to_write = amount_company_currency_to_write * (-1)

                line_obj.create(cr, uid, {
                    'parent_id': ids[0],
                    'invoice_id': invoice.id,
                    'partner_vat': partner_vat_to_write,
                    'partner_id': invoice.partner_id.id,
                    'invoice_currency_id': invoice.currency_id.id,
                    'amount_invoice_currency': int(round(amount_invoice_currency_to_write, 0)),
                    'amount_company_currency': int(round(amount_company_currency_to_write, 0)),
                    }, context=context)

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
        print "generate xml ids=", ids
        import des_xsd
        from lxml import etree
        intrastat = self.browse(cr, uid, ids[0], context=context)
        start_date_str = intrastat.start_date
        end_date_str = intrastat.end_date
        start_date_datetime = datetime.strptime(start_date_str, '%Y-%m-%d')

        self.pool.get('report.intrastat.common')._check_generate_xml(cr, uid, intrastat, context=context)

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
            except: raise osv.except_osv(_('Error :'), _("Missing VAT number for partner '%s'.") %sline.partner_id.name)
        xml_string = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
        print "xml_string", xml_string

        # We now validate the XML file against the official XML Schema Definition
        self.pool.get('report.intrastat.common')._check_xml_schema(cr, uid, root, xml_string, des_xsd.des_xsd, context=context)
        # Attach the XML file
        attach_id = self.pool.get('report.intrastat.common')._attach_xml_file(cr, uid, ids, self, xml_string, start_date_datetime, 'des', context=context)

#        return self.pool.get('report.intrastat.common')._open_attach_view(cr, uid, attach_id, 'DES XML file', context=context) # Works on v6 only - Makes the client crash on v5
        return True


report_intrastat_service()


class report_intrastat_service_line(osv.osv):
    _name = "report.intrastat.service.line"
    _description = "Lines of intrastat service declaration (DES)"
    _rec_name = "partner_vat"
    _order = 'id'
    _columns = {
        'parent_id': fields.many2one('report.intrastat.service', 'Intrastat service ref', ondelete='cascade', select=True),
        'state' : fields.related('parent_id', 'state', type='string', relation='report.intrastat.service', string='State', readonly=True),
        'company_id': fields.related('parent_id', 'company_id', type='many2one', relation='res.company', string="Company", readonly=True),
        'company_currency_id': fields.related('company_id', 'currency_id', type='many2one', relation='res.currency', string="Company currency", readonly=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice ref', readonly=True),
        'date_invoice' : fields.related('invoice_id', 'date_invoice', type='date', relation='account.invoice', string='Invoice date', readonly=True),
        'partner_vat': fields.char('Customer VAT', size=32, states={'done':[('readonly',True)]}),
        'partner_id': fields.many2one('res.partner', 'Partner name', states={'done':[('readonly',True)]}),
        'amount_company_currency': fields.integer('Amount in company cur.', states={'done':[('readonly',True)]}),
        'amount_invoice_currency': fields.integer('Amount in invoice cur.', readonly=True),
        'invoice_currency_id': fields.many2one('res.currency', "Invoice currency", readonly=True),
    }

    def partner_on_change(self, cr, uid, ids, partner_id=False):
        return self.pool.get('report.intrastat.common').partner_on_change(cr, uid, ids, partner_id)

report_intrastat_service_line()


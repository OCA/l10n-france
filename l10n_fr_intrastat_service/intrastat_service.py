# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat service module for OpenERP (DES)
#    Copyright (C) 2010-2013 Akretion (http://www.akretion.com/)
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

logger = logging.getLogger(__name__)


class report_intrastat_service(orm.Model):
    _name = "report.intrastat.service"
    _order = "start_date desc"
    _rec_name = "start_date"
    _inherit = ['mail.thread']
    _description = "Intrastat Service"
    _track = {
        'state': {
            'l10n_fr_intrastat_service.declaration_done': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'done',
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
        return super(report_intrastat_service, self).copy(cr, uid, id, default=default, context=context)


    def _compute_numbers(self, cr, uid, ids, name, arg, context=None):
        return self.pool.get('report.intrastat.common')._compute_numbers(cr, uid, ids, self, context=context)


    def _compute_dates(self, cr, uid, ids, name, arg, context=None):
        return self.pool.get('report.intrastat.common')._compute_dates(cr, uid, ids, self, context=context)


    def _get_intrastat_from_service_line(self, cr, uid, ids, context=None):
        return self.pool.get('report.intrastat.service').search(cr, uid, [('intrastat_line_ids', 'in', ids)], context=context)

    _columns = {
        'company_id': fields.many2one('res.company', 'Company',
            required=True, states={'done': [('readonly', True)]},
            help="Related company."),
        'start_date': fields.date('Start date', required=True,
            states={'done': [('readonly', True)]},
            help="Start date of the declaration. Must be the first day of a month."),
        'end_date': fields.function(_compute_dates, type='date',
            string='End date', multi='intrastat-service-dates', readonly=True,
            store={
                'report.intrastat.service': (lambda self, cr, uid, ids, c={}: ids, ['start_date'], 20)
                },
            help="End date for the declaration. Must be the last day of the month of the start date."),
        'year_month': fields.function(_compute_dates, type='char',
            string='Month', multi='intrastat-service-dates', readonly=True,
            track_visibility='always', store={
                'report.intrastat.service': (lambda self, cr, uid, ids, c={}: ids, ['start_date'], 20)
                },
            help="Year and month of the declaration."),
        'intrastat_line_ids': fields.one2many('report.intrastat.service.line',
            'parent_id', 'Report intrastat service lines',
            states={'done': [('readonly', True)]}),
        'num_lines': fields.function(_compute_numbers,
            type='integer', multi='numbers', string='Number of lines',
            store={
                'report.intrastat.service.line': (_get_intrastat_from_service_line, ['parent_id'], 20),
                },
            track_visibility='always',
            help="Number of lines in this declaration."),
        'total_amount': fields.function(_compute_numbers,
            digits_compute=dp.get_precision('Account'),
            multi='numbers', string='Total amount',
            store={
                'report.intrastat.service.line': (_get_intrastat_from_service_line, ['amount_company_currency', 'parent_id'], 20),
                },
            track_visibility='always',
            help="Total amount in company currency of the declaration."),
        'currency_id': fields.related('company_id', 'currency_id',
            readonly=True, type='many2one', relation='res.currency',
            string='Currency'),
        'state': fields.selection([
                ('draft', 'Draft'),
                ('done', 'Done'),
            ], 'State', select=True, readonly=True, track_visibility='onchange',
            help="State of the declaration. When the state is set to 'Done', the fields become read-only."),
        # No more need for date_done, because chatter does the job
    }

    _defaults = {
        # By default, we propose 'current month -1', because you prepare in
        # february the DES of January
        'start_date': lambda *a: datetime.strftime(datetime.today() + relativedelta(day=1, months=-1), '%Y-%m-%d'),
        'state': 'draft',
        'company_id': lambda self, cr, uid, context:
            self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id,
        }


    def _check_start_date(self, cr, uid, ids):
        return self.pool.get('report.intrastat.common')._check_start_date(cr, uid, ids, self)

    _constraints = [
        (_check_start_date, "Start date must be the first day of a month",
            ['start_date']),
    ]

    _sql_constraints = [
        ('date_uniq', 'unique(start_date, company_id)',
            'A DES for this month already exists !'),
    ]

    def generate_service_lines(self, cr, uid, ids, context=None):
        #print "generate lines, ids=", ids
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
        #print "invoice_ids=", invoice_ids
        for invoice in invoice_obj.browse(cr, uid, invoice_ids, context=context):

            if not invoice.partner_id.country_id:
                raise orm.except_orm(_('Error :'), _("Missing country on partner '%s'.") % invoice.partner_id.name)
            elif not invoice.partner_id.country_id.intrastat:
                continue
            elif invoice.partner_id.country_id.id == intrastat.company_id.country_id.id:
                continue

            amount_invoice_cur_to_write = 0.0
            amount_company_cur_to_write = 0.0
            amount_invoice_cur_regular_service = 0.0
            amount_invoice_cur_accessory_cost = 0.0
            regular_product_in_invoice = False

            for line in invoice.invoice_line:
                if not line.product_id:
                    continue

                if line.product_id.exclude_from_intrastat:
                    continue

                # If we have a regular product/consu in the invoice, we
                # don't take the is_accessory_cost in DES (it will be in DEB)
                # If we don't, we declare the is_accessory_cost in DES as other
                # regular services
                if line.product_id.type != 'service':
                    regular_product_in_invoice = True
                    continue

                # This check on line.price_subtotal must be AFTER the check
                # on line.product_id.type != 'service' in order to handle
                # the case where we have in an invoice :
                # - some HW products with value = 0
                # - some accessory costs
                # => we want to have the accessory costs in DEB, not in DES
                if not line.quantity or not line.price_subtotal:
                    continue

                skip_this_line = False
                for line_tax in line.invoice_line_tax_id:
                    if line_tax.exclude_from_intrastat_if_present:
                        skip_this_line = True
                if skip_this_line:
                    continue

                if line.product_id.is_accessory_cost:
                    amount_invoice_cur_accessory_cost += line.price_subtotal
                else:
                    amount_invoice_cur_regular_service += line.price_subtotal

            # END of the loop on invoice lines
            if regular_product_in_invoice:
                amount_invoice_cur_to_write = amount_invoice_cur_regular_service
            else:
                amount_invoice_cur_to_write = amount_invoice_cur_regular_service + amount_invoice_cur_accessory_cost

            if invoice.currency_id.name != 'EUR':
                context['date'] = invoice.date_invoice
                amount_company_cur_to_write = int(round(self.pool.get('res.currency').compute(cr, uid, invoice.currency_id.id, intrastat.company_id.currency_id.id, amount_invoice_cur_to_write, round=False, context=context), 0))
            else:
                amount_company_cur_to_write = int(round(amount_invoice_cur_to_write, 0))

            if amount_company_cur_to_write:
                if invoice.type == 'out_refund':
                    amount_invoice_cur_to_write = amount_invoice_cur_to_write * (-1)
                    amount_company_cur_to_write = amount_company_cur_to_write * (-1)

                # Why do I check that the Partner has a VAT number only here and not earlier ?
                # Because, if I sell to a physical person in the EU with VAT, then
                # the corresponding partner will not have a VAT number, and the entry
                # will be skipped because line_tax.exclude_from_intrastat_if_present is always
                # True and amount_company_cur_to_write = 0
                # So we should not block with a raise before the end of the loop on the
                # invoice lines and the "if amount_company_cur_to_write:"
                if not invoice.partner_id.vat:
                    raise orm.except_orm(_('Error :'), _("Missing VAT number on partner '%s'.") % invoice.partner_id.name)
                else:
                    partner_vat_to_write = invoice.partner_id.vat

                line_obj.create(cr, uid, {
                    'parent_id': ids[0],
                    'invoice_id': invoice.id,
                    'partner_vat': partner_vat_to_write,
                    'partner_id': invoice.partner_id.id,
                    'invoice_currency_id': invoice.currency_id.id,
                    'amount_invoice_currency': amount_invoice_cur_to_write,
                    'amount_company_currency': amount_company_cur_to_write,
                    }, context=context)

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
        #print "generate xml ids=", ids
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
        mois_des.text = datetime.strftime(start_date_datetime, '%m')  # month 2 digits
        an_des = etree.SubElement(decl, 'an_des')
        an_des.text = datetime.strftime(start_date_datetime, '%Y')
        line = 0
        # we now go through each service line
        for sline in intrastat.intrastat_line_ids:
            line += 1  # increment line number
            ligne_des = etree.SubElement(decl, 'ligne_des')
            numlin_des = etree.SubElement(ligne_des, 'numlin_des')
            numlin_des.text = str(line)
            valeur = etree.SubElement(ligne_des, 'valeur')
            # We take amount_company_currency, to be sure we have amounts in EUR
            valeur.text = str(sline.amount_company_currency)
            partner_des = etree.SubElement(ligne_des, 'partner_des')
            try:
                partner_des.text = sline.partner_vat.replace(' ', '')
            except:
                raise orm.except_orm(_('Error :'), _("Missing VAT number on partner '%s'.") % sline.partner_id.name)
        xml_string = etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
        #print "xml_string", xml_string

        # We now validate the XML file against the official XML Schema Definition
        self.pool.get('report.intrastat.common')._check_xml_schema(cr, uid, root, xml_string, des_xsd.des_xsd, context=context)
        # Attach the XML file
        attach_id = self.pool.get('report.intrastat.common')._attach_xml_file(cr, uid, ids, self, xml_string, start_date_datetime, 'des', context=context)

        return self.pool.get('report.intrastat.common')._open_attach_view(cr, uid, attach_id, 'DES XML file', context=context)


    def _scheduler_reminder(self, cr, uid, context=None):
        if context is None:
            context = {}
        previous_month = datetime.strftime(datetime.today() + relativedelta(day=1, months=-1), '%Y-%m')
        # I can't search on [('country_id', '=', ...)]
        # because it is a fields.function not stored and without fnct_search
        company_ids = self.pool['res.company'].search(
            cr, uid, [], context=context)
        logger.info('Starting the Intrastat Service reminder')
        for company in self.pool['res.company'].browse(cr, uid, company_ids, context=None):
            if company.country_id.code != 'FR':
                continue
            # Check if an intrastat service already exists for month N-1
            intrastat_ids = self.search(cr, uid, [('year_month', '=', previous_month), ('company_id', '=', company.id)], context=context)
            # if it already exists, we don't do anything
            # in the future, we may check the state and send a mail
            # if the state is still in draft ?
            if intrastat_ids:
                logger.info('An Intrastat Service for month %s already exists for company %s' % (previous_month, company.name))
                continue
            else:
                # If not, we create an intrastat.service for month N-1
                intrastat_id = self.create(cr, uid, {
                    'company_id': company.id,
                    }, context=context)
                logger.info('An Intrastat Service for month %s has been created by OpenERP for company %s' % (previous_month, company.name))
                # we try to generate the lines
                try:
                    self.generate_service_lines(cr, uid, [intrastat_id], context=context)
                except Exception as e:  # TODO filter on exception from except_orm
                    context['exception'] = True
                    #print "e=", e
                    context['error_msg'] = e[1]

                # send the reminder email
                self.pool['report.intrastat.common'].send_reminder_email(cr, uid, company, 'l10n_fr_intrastat_service', 'intrastat_service_reminder_email_template', intrastat_id, context=context)
        return True


class report_intrastat_service_line(orm.Model):
    _name = "report.intrastat.service.line"
    _description = "Intrastat Service Lines"
    _rec_name = "partner_vat"
    _order = 'id'
    _columns = {
        'parent_id': fields.many2one('report.intrastat.service',
            'Intrastat service ref', ondelete='cascade'),
        'company_id': fields.related('parent_id', 'company_id',
            type='many2one', relation='res.company',
            string="Company", readonly=True),
        'company_currency_id': fields.related('company_id', 'currency_id',
            type='many2one', relation='res.currency',
            string="Company currency", readonly=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice ref',
            readonly=True),
        'date_invoice': fields.related('invoice_id', 'date_invoice',
            type='date', relation='account.invoice',
            string='Invoice date', readonly=True),
        'partner_vat': fields.char('Customer VAT', size=32),
        'partner_id': fields.many2one('res.partner', 'Partner name'),
        'amount_company_currency': fields.integer('Amount in company currency',
            help="Amount in company currency to write in the declaration. Amount in company currency = amount in invoice currency converted to company currency with the rate of the invoice date and rounded at 0 digits"),
        'amount_invoice_currency': fields.float('Amount in invoice currency',
            digits_compute=dp.get_precision('Account'), readonly=True,
            help="Amount in invoice currency (not rounded)"),
        'invoice_currency_id': fields.many2one('res.currency',
            "Invoice currency", readonly=True),
    }

    def partner_on_change(self, cr, uid, ids, partner_id=False):
        return self.pool.get('report.intrastat.common').partner_on_change(cr, uid, ids, partner_id)

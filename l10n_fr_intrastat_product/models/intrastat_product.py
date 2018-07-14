# -*- coding: utf-8 -*-
# © 2009-2017 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
from lxml import etree

logger = logging.getLogger(__name__)


class IntrastatProductDeclaration(models.Model):
    _inherit = 'intrastat.product.declaration'

    # I wanted to inherit this field in l10n.fr.intrastat.product.declaration
    # but it doesn't work
    total_amount = fields.Float(compute='_compute_fr_numbers')
    # Inherit also num_decl_lines to avoid double loop
    num_decl_lines = fields.Integer(compute='_compute_fr_numbers')

    @api.depends('declaration_line_ids.amount_company_currency')
    def _compute_fr_numbers(self):
        for decl in self:
            total_amount = 0.0
            num_lines = 0
            for line in decl.declaration_line_ids:
                total_amount += line.amount_company_currency *\
                    line.transaction_id.fr_fiscal_value_multiplier
                num_lines += 1
            decl.num_decl_lines = num_lines
            decl.total_amount = total_amount


class L10nFrIntrastatProductDeclaration(models.Model):
    _name = "l10n.fr.intrastat.product.declaration"
    _description = "Intrastat Product for France (DEB)"
    _inherit = ['intrastat.product.declaration', 'mail.thread']

    computation_line_ids = fields.One2many(
        'l10n.fr.intrastat.product.computation.line',
        'parent_id', string='Intrastat Product Computation Lines',
        states={'done': [('readonly', True)]})
    declaration_line_ids = fields.One2many(
        'l10n.fr.intrastat.product.declaration.line',
        'parent_id', string='Intrastat Product Declaration Lines',
        states={'done': [('readonly', True)]})

    def _prepare_invoice_domain(self):
        domain = super(L10nFrIntrastatProductDeclaration, self).\
            _prepare_invoice_domain()
        if self.type == 'arrivals':
            domain.append(('type', '=', 'in_invoice'))
        elif self.type == 'dispatches':
            domain.append(('type', 'in', ('out_invoice', 'out_refund')))
        return domain

    @api.model
    def _get_product_origin_country(self, inv_line):
        """Inherit to add warning when origin_country_id is missing
        for arrivals"""
        if (
                self.type == 'arrivals' and
                self.reporting_level == 'extended' and
                not inv_line.product_id.origin_country_id):
            note = "\n" + _(
                "Missing country of origin on product %s. "
                "This product is present in invoice %s.") % (
                    inv_line.product_id.name_get()[0][1],
                    inv_line.invoice_id.number)
            self._note += note
        return inv_line.product_id.origin_country_id

    @api.model
    def _get_fr_department(self, inv_line):
        dpt = False
        inv_type = inv_line.invoice_id.type
        if inv_type in ('in_invoice', 'in_refund'):
            po_lines = self.env['purchase.order.line'].search(
                [('invoice_lines', 'in', inv_line.id)])
            if po_lines:
                if po_lines[0].order_id.picking_type_id.warehouse_id:
                    dpt = po_lines[0].order_id.picking_type_id.\
                        warehouse_id.get_fr_department()
                elif po_lines[0].move_ids:
                    location = po_lines[0].move_ids[0].location_dest_id
                    dpt = location.get_fr_department()
        elif inv_type in ('out_invoice', 'out_refund'):
            so_lines = self.env['sale.order.line'].search(
                [('invoice_lines', 'in', inv_line.id)])
            if so_lines:
                so = so_lines[0].order_id
                dpt = so.warehouse_id.get_fr_department()
        if not dpt:
            dpt = self.company_id.partner_id.department_id
        return dpt

    @api.model
    def _update_computation_line_vals(self, inv_line, line_vals):
        super(L10nFrIntrastatProductDeclaration, self).\
            _update_computation_line_vals(
                inv_line, line_vals)
        inv = inv_line.invoice_id
        if not inv.partner_id.country_id.intrastat:
            if not inv.partner_id.intrastat_fiscal_representative_id:
                note = "\n" + _(
                    "Missing fiscal representative on partner '%s'"
                    % inv.partner_id.name_get()[0][1])
                self._note += note
            else:
                line_vals['fr_partner_id'] =\
                    inv.partner_id.intrastat_fiscal_representative_id.id
        else:
            line_vals['fr_partner_id'] = inv.partner_id.id
        dpt = self._get_fr_department(inv_line)
        line_vals['fr_department_id'] = dpt and dpt.id or False

    @api.model
    def _group_line_hashcode_fields(self, computation_line):
        res = super(L10nFrIntrastatProductDeclaration, self)\
            ._group_line_hashcode_fields(computation_line)
        res['partner_id'] = computation_line.fr_partner_id.id or False
        return res

    def _get_region(self, inv_line):
        # TODO : modify only for country == FR
        return False

    @api.multi
    def _generate_xml(self):
        '''Generate the INSTAT XML file export.'''
        self._check_generate_xml()

        my_company_vat = self.company_id.partner_id.vat.replace(' ', '')

        if not self.company_id.siret:
            raise UserError(
                _("The SIRET is not set on company '%s'.")
                % self.company_id.name)
        if self.action != 'replace' or self.revision != 1:
            raise UserError(_(
                "Pro.dou@ne only accepts XML file upload for "
                "the original declaration."))
        my_company_identifier = my_company_vat + self.company_id.siret[9:]

        my_company_currency = self.company_id.currency_id.name

        root = etree.Element('INSTAT')
        envelope = etree.SubElement(root, 'Envelope')
        envelope_id = etree.SubElement(envelope, 'envelopeId')
        if not self.company_id.fr_intrastat_accreditation:
            raise UserError(_(
                "The customs accreditation identifier is not set "
                "for the company '%s'.") % self.company_id.name)
        envelope_id.text = self.company_id.fr_intrastat_accreditation
        create_date_time = etree.SubElement(envelope, 'DateTime')
        create_date = etree.SubElement(create_date_time, 'date')
        now_user_tz = fields.Datetime.context_timestamp(self, datetime.now())
        create_date.text = datetime.strftime(now_user_tz, '%Y-%m-%d')
        create_time = etree.SubElement(create_date_time, 'time')
        create_time.text = datetime.strftime(now_user_tz, '%H:%M:%S')
        party = etree.SubElement(
            envelope, 'Party', partyType="PSI", partyRole="PSI")
        party_id = etree.SubElement(party, 'partyId')
        party_id.text = my_company_identifier
        party_name = etree.SubElement(party, 'partyName')
        party_name.text = self.company_id.name
        software_used = etree.SubElement(envelope, 'softwareUsed')
        software_used.text = 'Odoo'
        declaration = etree.SubElement(envelope, 'Declaration')
        declaration_id = etree.SubElement(declaration, 'declarationId')
        declaration_id.text = self.year_month.replace('-', '')
        reference_period = etree.SubElement(declaration, 'referencePeriod')
        reference_period.text = self.year_month
        psi_id = etree.SubElement(declaration, 'PSIId')
        psi_id.text = my_company_identifier
        function = etree.SubElement(declaration, 'Function')
        function_code = etree.SubElement(function, 'functionCode')
        function_code.text = 'O'
        declaration_type_code = etree.SubElement(
            declaration, 'declarationTypeCode')
        assert self.reporting_level in ('standard', 'extended'),\
            "Invalid reporting level"
        if self.reporting_level == 'extended':
            declaration_type_code.text = '1'
        elif self.reporting_level == 'standard':
            declaration_type_code.text = '4'
        flow_code = etree.SubElement(declaration, 'flowCode')

        assert self.type in ('arrivals', 'dispatches'),\
            "The DEB must be of type 'Arrivals' or 'Dispatches'"
        if self.type == 'dispatches':
            flow_code.text = 'D'
        elif self.type == 'arrivals':
            flow_code.text = 'A'
        currency_code = etree.SubElement(declaration, 'currencyCode')
        assert my_company_currency == 'EUR', "Company currency must be 'EUR'"
        currency_code.text = my_company_currency

        # THEN, the fields which vary from a line to the next
        if not self.declaration_line_ids:
            raise UserError(_(
                'No declaration lines. You probably forgot to generate '
                'them !'))
        line = 0
        for pline in self.declaration_line_ids:
            line += 1  # increment line number
            # print "line =", line
            assert pline.transaction_id, "Missing Intrastat Type"
            transaction = pline.transaction_id
            item = etree.SubElement(declaration, 'Item')
            item_number = etree.SubElement(item, 'itemNumber')
            item_number.text = str(line)
            # START of elements which are only required in "detailed" level
            if (
                    self.reporting_level == 'extended' and
                    not transaction.fr_is_fiscal_only):
                cn8 = etree.SubElement(item, 'CN8')
                cn8_code = etree.SubElement(cn8, 'CN8Code')
                if not pline.hs_code_id:
                    raise UserError(
                        _('Missing H.S. code on line %d.') % line)
                # local_code is required=True, so no need to check it
                cn8_code.text = pline.hs_code_id.local_code
                # We fill SUCode only if the H.S. code requires it
                if pline.intrastat_unit_id:
                    su_code = etree.SubElement(cn8, 'SUCode')
                    if not pline.intrastat_unit_id.fr_xml_label:
                        raise UserError(_(
                            "Missing Label for DEB on Intrastat Unit "
                            "of Measure '%s'.")
                            % pline.intrastat_unit_id.name)
                    su_code.text = pline.intrastat_unit_id.fr_xml_label
                    destination_country = etree.SubElement(
                        item, 'MSConsDestCode')
                    if self.type == 'arrivals':
                        country_origin = etree.SubElement(
                            item, 'countryOfOriginCode')
                    weight = etree.SubElement(item, 'netMass')
                    quantity_in_SU = etree.SubElement(item, 'quantityInSU')

                    if not pline.suppl_unit_qty:
                        raise UserError(
                            _('Missing quantity on line %d.') % line)
                    quantity_in_SU.text = unicode(pline.suppl_unit_qty)
                else:
                    destination_country = etree.SubElement(
                        item, 'MSConsDestCode')
                    if self.type == 'arrivals':
                        country_origin = etree.SubElement(
                            item, 'countryOfOriginCode')
                    weight = etree.SubElement(item, 'netMass')
                if not pline.src_dest_country_id:
                    raise UserError(_(
                        'Missing Country of Origin/Destination on line %d.')
                        % line)
                destination_country.text = pline.src_dest_country_id.code
                if self.type == 'arrivals':
                    if not pline.product_origin_country_id:
                        raise UserError(_(
                            'Missing product country of origin on line %d.')
                            % line)
                    country_origin.text = pline.product_origin_country_id.code
                if not pline.weight:
                    raise UserError(
                        _('Missing weight on line %d.') % line)
                weight.text = unicode(pline.weight)

            # START of elements that are part of all DEBs
            invoiced_amount = etree.SubElement(item, 'invoicedAmount')
            if not pline.amount_company_currency:
                raise UserError(
                    _('Missing fiscal value on line %d.') % line)
            invoiced_amount.text = str(pline.amount_company_currency)
            # Partner VAT is only declared for export when code régime != 29
            if (
                    self.type == 'dispatches' and
                    transaction.fr_is_vat_required):
                partner_id = etree.SubElement(item, 'partnerId')
                if not pline.fr_partner_id:
                    raise UserError(_(
                        "Missing partner on line %d.") % line)
                if not pline.fr_partner_id.vat:
                    raise UserError(
                        _("Missing VAT number on partner '%s'.")
                        % pline.fr_partner_id.name)
                partner_id.text = pline.fr_partner_id.vat.replace(' ', '')
            # Code régime is on all DEBs
            statistical_procedure_code = etree.SubElement(
                item, 'statisticalProcedureCode')
            statistical_procedure_code.text = transaction.code

            # START of elements which are only required in "detailed" level
            if (
                    self.reporting_level == 'extended' and
                    not transaction.fr_is_fiscal_only):
                transaction_nature = etree.SubElement(
                    item, 'NatureOfTransaction')
                transaction_nature_a = etree.SubElement(
                    transaction_nature, 'natureOfTransactionACode')
                transaction_nature_a.text = transaction.fr_transaction_code[0]
                transaction_nature_b = etree.SubElement(
                    transaction_nature, 'natureOfTransactionBCode')
                if len(transaction.fr_transaction_code) != 2:
                    raise UserError(
                        _('Transaction code on line %d should have 2 digits.')
                        % line)
                transaction_nature_b.text = transaction.fr_transaction_code[1]
                mode_of_transport_code = etree.SubElement(
                    item, 'modeOfTransportCode')
                if not pline.transport_id:
                    raise UserError(_(
                        'Mode of transport is not set on line %d.') % line)
                mode_of_transport_code.text = str(pline.transport_id.code)
                region_code = etree.SubElement(item, 'regionCode')
                if not pline.fr_department_id:
                    raise UserError(
                        _('Department is not set on line %d.') % line)
                region_code.text = pline.fr_department_id.code

        xml_string = etree.tostring(
            root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
        # We validate the XML file against the official XML Schema Definition
        # Because we may catch some problems with the content
        # of the XML file this way
        self._check_xml_schema(
            xml_string, 'l10n_fr_intrastat_product/data/deb.xsd')
        # Attach the XML file to the current object
        return xml_string

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
            for type in ['arrivals', 'dispatches']:
                if (
                        type == 'arrivals' and
                        company.intrastat_arrivals == 'exempt'):
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
                    reporting_level = False
                    if type == 'arrivals':
                        reporting_level = company.intrastat_arrivals
                    elif type == 'dispatches':
                        reporting_level = company.intrastat_dispatches
                    if not reporting_level:
                        logger.warning(
                            "Missing reporting level for %s "
                            "on company '%s'." % (type, company.name))
                        continue
                    intrastat = self.create({
                        'company_id': company.id,
                        'type': type,
                        'reporting_level': reporting_level,
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


class L10nFrIntrastatProductComputationLine(models.Model):
    _name = 'l10n.fr.intrastat.product.computation.line'
    _inherit = 'intrastat.product.computation.line'

    parent_id = fields.Many2one(
        'l10n.fr.intrastat.product.declaration',
        string='Intrastat Product Declaration',
        ondelete='cascade', readonly=True)
    declaration_line_id = fields.Many2one(
        'l10n.fr.intrastat.product.declaration.line',
        string='Declaration Line', readonly=True)
    fr_partner_id = fields.Many2one(
        'res.partner', string='Partner', ondelete='restrict',
        help='Origin partner for arrivals. '
        'Destination partner (or his fiscal representative) for dispatches')
    fr_department_id = fields.Many2one(
        'res.country.department', string='Departement', ondelete='restrict')
    # the 2 fields below are useful for reports
    amount_company_currency_sign = fields.Float(
        compute='_compute_amount_company_currency_sign', readonly=True,
        store=True)
    amount_accessory_cost_company_currency_sign = fields.Float(
        compute='_compute_amount_company_currency_sign', readonly=True,
        store=True)

    @api.depends(
        'amount_company_currency', 'amount_accessory_cost_company_currency',
        'transaction_id.fr_fiscal_value_multiplier')
    def _compute_amount_company_currency_sign(self):
        for line in self:
            sign = line.transaction_id.fr_fiscal_value_multiplier or 1
            line.amount_company_currency_sign =\
                sign * line.amount_company_currency
            line.amount_accessory_cost_company_currency_sign =\
                sign * line.amount_accessory_cost_company_currency


class L10nFrIntrastatProductDeclarationLine(models.Model):
    _name = 'l10n.fr.intrastat.product.declaration.line'
    _inherit = 'intrastat.product.declaration.line'

    parent_id = fields.Many2one(
        'l10n.fr.intrastat.product.declaration',
        string='Intrastat Product Declaration',
        ondelete='cascade', readonly=True)
    computation_line_ids = fields.One2many(
        'l10n.fr.intrastat.product.computation.line', 'declaration_line_id',
        string='Computation Lines', readonly=True)
    fr_partner_id = fields.Many2one(
        'res.partner', string='Partner',
        help='Origin partner for arrivals. '
        'Destination partner (or his fiscal representative) for dispatches')
    fr_department_id = fields.Many2one(
        'res.country.department', string='Departement', ondelete='restrict')
    # the field below is useful for reports
    amount_company_currency_sign = fields.Float(
        compute='_compute_amount_company_currency_sign', readonly=True,
        store=True)

    @api.depends(
        'amount_company_currency', 'transaction_id.fr_fiscal_value_multiplier')
    def _compute_amount_company_currency_sign(self):
        for line in self:
            sign = line.transaction_id.fr_fiscal_value_multiplier or 1
            line.amount_company_currency_sign =\
                sign * line.amount_company_currency

    @api.model
    def _prepare_grouped_fields(self, computation_line, fields_to_sum):
        vals = super(L10nFrIntrastatProductDeclarationLine, self).\
            _prepare_grouped_fields(computation_line, fields_to_sum)
        vals['fr_partner_id'] = computation_line.fr_partner_id.id
        vals['fr_department_id'] = computation_line.fr_department_id.id
        return vals

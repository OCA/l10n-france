# Copyright 2009-2020 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class IntrastatProductDeclaration(models.Model):
    _inherit = "intrastat.product.declaration"

    # I wanted to inherit this field in l10n.fr.intrastat.product.declaration
    # but it doesn't work
    total_amount = fields.Integer(compute="_compute_fr_numbers")
    # Inherit also num_decl_lines to avoid double loop
    num_decl_lines = fields.Integer(compute="_compute_fr_numbers")

    @api.depends("declaration_line_ids.amount_company_currency")
    def _compute_fr_numbers(self):
        for decl in self:
            total_amount = 0.0
            num_lines = 0
            for line in decl.declaration_line_ids:
                total_amount += (
                    line.amount_company_currency
                    * line.transaction_id.fr_fiscal_value_multiplier
                )
                num_lines += 1
            decl.num_decl_lines = num_lines
            decl.total_amount = total_amount


class L10nFrIntrastatProductDeclaration(models.Model):
    _name = "l10n.fr.intrastat.product.declaration"
    _description = "Intrastat Product for France (DEB)"
    _inherit = [
        "intrastat.product.declaration",
        "mail.thread",
        "mail.activity.mixin",
        "report.intrastat_product.product_declaration_xls",
    ]

    computation_line_ids = fields.One2many(
        "l10n.fr.intrastat.product.computation.line",
        "parent_id",
        string="Intrastat Product Computation Lines",
        states={"done": [("readonly", True)]},
    )
    declaration_line_ids = fields.One2many(
        "l10n.fr.intrastat.product.declaration.line",
        "parent_id",
        string="Intrastat Product Declaration Lines",
        states={"done": [("readonly", True)]},
    )

    def _prepare_invoice_domain(self):
        domain = super()._prepare_invoice_domain()
        for index, entry in enumerate(domain):
            if entry[0] == "move_type":
                domain.pop(index)
        if self.declaration_type == "arrivals":
            domain.append(("move_type", "=", "in_invoice"))
        elif self.declaration_type == "dispatches":
            domain.append(("move_type", "in", ("out_invoice", "out_refund")))
        return domain

    def _get_product_origin_country(self, inv_line, notedict):
        """Inherit to add warning when origin_country_id is missing
        for arrivals"""
        if (
            self.declaration_type == "arrivals"
            and self.reporting_level == "extended"
            and not inv_line.product_id.origin_country_id
        ):
            line_notes = [
                _("Missing country of origin on product '%s'.")
                % inv_line.product_id.display_name
            ]
            self._format_line_note(inv_line, notedict, line_notes)
        return super()._get_product_origin_country(inv_line, notedict)

    def _get_fr_department(self, inv_line, notedict):
        dpt = False
        move_type = inv_line.move_id.move_type
        if move_type in ("in_invoice", "in_refund"):
            po_line = self.env["purchase.order.line"].search(
                [("invoice_lines", "in", inv_line.id)], limit=1
            )
            if po_line:
                wh = po_line.order_id.picking_type_id.warehouse_id
                if wh:
                    dpt = wh.get_fr_department()
                elif po_line.move_ids:
                    location = po_line.move_ids[0].location_dest_id
                    dpt = location.get_fr_department()
        elif move_type in ("out_invoice", "out_refund"):
            so_line = self.env["sale.order.line"].search(
                [("invoice_lines", "in", inv_line.id)], limit=1
            )
            if so_line:
                so = so_line.order_id
                dpt = so.warehouse_id.get_fr_department()
        if not dpt:
            dpt = self.company_id.partner_id.department_id
        return dpt

    def _update_computation_line_vals(self, inv_line, line_vals, notedict):
        super()._update_computation_line_vals(inv_line, line_vals, notedict)
        inv = inv_line.move_id
        if not inv.partner_id.country_id.intrastat:
            if not inv.commercial_partner_id.intrastat_fiscal_representative_id:
                line_notes = [
                    _(
                        "Missing fiscal representative on partner '%s'"
                        % inv.commercial_partner_id.display_name
                    )
                ]
                self._format_line_note(inv_line, notedict, line_notes)
            else:
                line_vals[
                    "fr_partner_id"
                ] = inv.commercial_partner_id.intrastat_fiscal_representative_id.id
        else:
            line_vals["fr_partner_id"] = inv.partner_id.id
        dpt = self._get_fr_department(inv_line, notedict)
        line_vals["fr_department_id"] = dpt and dpt.id or False

    @api.model
    def _group_line_hashcode_fields(self, computation_line):
        res = super()._group_line_hashcode_fields(computation_line)
        res["partner_id"] = computation_line.fr_partner_id.id or False
        return res

    @api.model
    def _prepare_grouped_fields(self, computation_line, fields_to_sum):
        vals = super()._prepare_grouped_fields(computation_line, fields_to_sum)
        vals["fr_partner_id"] = computation_line.fr_partner_id.id
        vals["fr_department_id"] = computation_line.fr_department_id.id
        return vals

    def _get_region(self, inv_line, notedict):
        # TODO : modify only for country == FR
        return False

    @api.model
    def _xls_template(self):
        res = super()._xls_template()
        res.update(
            {
                "fr_department": {
                    "header": {
                        "type": "string",
                        "value": self._("Department"),
                    },
                    "line": {
                        "value": self._render("line.fr_department_id.display_name"),
                    },
                    "width": 18,
                },
                "fr_partner": {
                    "header": {
                        "type": "string",
                        "value": self._("Partner"),
                    },
                    "line": {
                        "value": self._render("line.fr_partner_id.display_name"),
                    },
                    "width": 28,
                },
                "fr_partner_vat": {
                    "header": {
                        "type": "string",
                        "value": self._("Partner VAT"),
                    },
                    "line": {
                        "value": self._render("line.fr_partner_id.vat"),
                    },
                    "width": 18,
                },
            }
        )
        return res

    @api.model
    def _xls_computation_line_fields(self):
        field_list = super()._xls_computation_line_fields()
        field_list += ["fr_partner", "fr_partner_vat", "fr_department"]
        return field_list

    @api.model
    def _xls_declaration_line_fields(self):
        field_list = super()._xls_declaration_line_fields()
        field_list += ["fr_partner", "fr_partner_vat", "fr_department"]
        return field_list

    def _generate_xml(self):
        """Generate the INSTAT XML file export."""
        self._check_generate_xml()

        my_company_vat = self.company_id.partner_id.vat.replace(" ", "")

        if not self.company_id.siret:
            raise UserError(
                _("The SIRET is not set on company '%s'.")
                % self.company_id.display_name
            )
        if self.action != "replace" or self.revision != 1:
            raise UserError(
                _(
                    "Pro.dou@ne only accepts XML file upload for "
                    "the original declaration."
                )
            )
        my_company_identifier = my_company_vat + self.company_id.siret[9:]

        my_company_currency = self.company_id.currency_id.name

        root = etree.Element("INSTAT")
        envelope = etree.SubElement(root, "Envelope")
        envelope_id = etree.SubElement(envelope, "envelopeId")
        if not self.company_id.fr_intrastat_accreditation:
            raise UserError(
                _(
                    "The customs accreditation identifier is not set "
                    "for the company '%s'."
                )
                % self.company_id.display_name
            )
        envelope_id.text = self.company_id.fr_intrastat_accreditation
        create_date_time = etree.SubElement(envelope, "DateTime")
        create_date = etree.SubElement(create_date_time, "date")
        now_user_tz = fields.Datetime.context_timestamp(self, datetime.now())
        create_date.text = datetime.strftime(now_user_tz, "%Y-%m-%d")
        create_time = etree.SubElement(create_date_time, "time")
        create_time.text = datetime.strftime(now_user_tz, "%H:%M:%S")
        party = etree.SubElement(envelope, "Party", partyType="PSI", partyRole="PSI")
        party_id = etree.SubElement(party, "partyId")
        party_id.text = my_company_identifier
        party_name = etree.SubElement(party, "partyName")
        party_name.text = self.company_id.name
        software_used = etree.SubElement(envelope, "softwareUsed")
        software_used.text = "Odoo"
        declaration = etree.SubElement(envelope, "Declaration")
        declaration_id = etree.SubElement(declaration, "declarationId")
        declaration_id.text = self.year_month.replace("-", "")
        reference_period = etree.SubElement(declaration, "referencePeriod")
        reference_period.text = self.year_month
        psi_id = etree.SubElement(declaration, "PSIId")
        psi_id.text = my_company_identifier
        function = etree.SubElement(declaration, "Function")
        function_code = etree.SubElement(function, "functionCode")
        function_code.text = "O"
        declaration_type_code = etree.SubElement(declaration, "declarationTypeCode")
        level2letter = {
            "standard": "4",
            "extended": "1",
        }
        assert self.reporting_level in level2letter
        declaration_type_code.text = level2letter[self.reporting_level]
        flow_code = etree.SubElement(declaration, "flowCode")
        type2letter = {
            "arrivals": "A",
            "dispatches": "D",
        }
        assert self.declaration_type in type2letter
        flow_code.text = type2letter[self.declaration_type]
        currency_code = etree.SubElement(declaration, "currencyCode")
        assert my_company_currency == "EUR", "Company currency must be 'EUR'"
        currency_code.text = my_company_currency

        # THEN, the fields which vary from a line to the next
        if not self.declaration_line_ids:
            raise UserError(
                _("No declaration lines. You probably forgot to generate " "them !")
            )
        line = 0
        for pline in self.declaration_line_ids:
            line += 1  # increment line number
            # print "line =", line
            assert pline.transaction_id, "Missing Intrastat Type"
            transaction = pline.transaction_id
            item = etree.SubElement(declaration, "Item")
            item_number = etree.SubElement(item, "itemNumber")
            item_number.text = str(line)
            # START of elements which are only required in "detailed" level
            if self.reporting_level == "extended" and not transaction.fr_is_fiscal_only:
                cn8 = etree.SubElement(item, "CN8")
                cn8_code = etree.SubElement(cn8, "CN8Code")
                if not pline.hs_code_id:
                    raise UserError(_("Missing H.S. code on line %d.") % line)
                # local_code is required=True, so no need to check it
                cn8_code.text = pline.hs_code_id.local_code
                # We fill SUCode only if the H.S. code requires it
                iunit_id = pline.intrastat_unit_id
                if iunit_id:
                    su_code = etree.SubElement(cn8, "SUCode")
                    su_code.text = iunit_id.fr_xml_label or iunit_id.name
                    destination_country = etree.SubElement(item, "MSConsDestCode")
                    if self.declaration_type == "arrivals":
                        country_origin = etree.SubElement(item, "countryOfOriginCode")
                    weight = etree.SubElement(item, "netMass")
                    quantity_in_SU = etree.SubElement(item, "quantityInSU")

                    if not pline.suppl_unit_qty:
                        raise UserError(_("Missing quantity on line %d.") % line)
                    quantity_in_SU.text = str(pline.suppl_unit_qty)
                else:
                    destination_country = etree.SubElement(item, "MSConsDestCode")
                    if self.declaration_type == "arrivals":
                        country_origin = etree.SubElement(item, "countryOfOriginCode")
                    weight = etree.SubElement(item, "netMass")
                if not pline.src_dest_country_id:
                    raise UserError(
                        _("Missing Country of Origin/Destination on line %d.") % line
                    )
                destination_country.text = pline.src_dest_country_id.code
                if self.declaration_type == "arrivals":
                    if not pline.product_origin_country_id:
                        raise UserError(
                            _("Missing product country of origin on line %d.") % line
                        )
                    country_origin.text = pline.product_origin_country_id.code
                if not pline.weight:
                    raise UserError(_("Missing weight on line %d.") % line)
                weight.text = str(pline.weight)

            # START of elements that are part of all DEBs
            invoiced_amount = etree.SubElement(item, "invoicedAmount")
            if not pline.amount_company_currency:
                raise UserError(_("Missing fiscal value on line %d.") % line)
            invoiced_amount.text = str(pline.amount_company_currency)
            # Partner VAT is only declared for export when code régime != 29
            if self.declaration_type == "dispatches" and transaction.fr_is_vat_required:
                partner_id = etree.SubElement(item, "partnerId")
                if not pline.fr_partner_id:
                    raise UserError(_("Missing partner on line %d.") % line)
                if not pline.fr_partner_id.vat:
                    raise UserError(
                        _("Missing VAT number on partner '%s'.")
                        % pline.fr_partner_id.name
                    )
                partner_id.text = pline.fr_partner_id.vat.replace(" ", "")
            # Code régime is on all DEBs
            statistical_procedure_code = etree.SubElement(
                item, "statisticalProcedureCode"
            )
            statistical_procedure_code.text = transaction.code

            # START of elements which are only required in "detailed" level
            if self.reporting_level == "extended" and not transaction.fr_is_fiscal_only:
                transaction_nature = etree.SubElement(item, "NatureOfTransaction")
                transaction_nature_a = etree.SubElement(
                    transaction_nature, "natureOfTransactionACode"
                )
                transaction_nature_a.text = transaction.fr_transaction_code[0]
                transaction_nature_b = etree.SubElement(
                    transaction_nature, "natureOfTransactionBCode"
                )
                if len(transaction.fr_transaction_code) != 2:
                    raise UserError(
                        _("Transaction code on line %d should have 2 digits.") % line
                    )
                transaction_nature_b.text = transaction.fr_transaction_code[1]
                mode_of_transport_code = etree.SubElement(item, "modeOfTransportCode")
                if not pline.transport_id:
                    raise UserError(
                        _("Mode of transport is not set on line %d.") % line
                    )
                mode_of_transport_code.text = str(pline.transport_id.code)
                region_code = etree.SubElement(item, "regionCode")
                if not pline.fr_department_id:
                    raise UserError(_("Department is not set on line %d.") % line)
                region_code.text = pline.fr_department_id.code

        xml_bytes = etree.tostring(
            root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )
        # We validate the XML file against the official XML Schema Definition
        # Because we may catch some problems with the content
        # of the XML file this way
        self._check_xml_schema(xml_bytes, "l10n_fr_intrastat_product/data/deb.xsd")
        # Attach the XML file to the current object
        return xml_bytes

    @api.model
    def _scheduler_reminder(self):
        previous_month = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=-1), "%Y-%m"
        )
        # I can't search on [('country_id', '=', ..)]
        # because it is a fields.function not stored and without fnct_search
        companies = self.env["res.company"].search([])
        logger.info("Starting the Intrastat Product reminder")
        for company in companies:
            if company.country_id.code != "FR":
                continue
            for declaration_type in ["arrivals", "dispatches"]:
                # Check if a declaration already exists for month N-1
                intrastats = self.search(
                    [
                        ("year_month", "=", previous_month),
                        ("declaration_type", "=", declaration_type),
                        ("company_id", "=", company.id),
                    ]
                )
                if intrastats:
                    # if it already exists, we don't do anything
                    logger.info(
                        "An %s Intrastat Product for month %s already "
                        "exists for company %s",
                        declaration_type,
                        previous_month,
                        company.display_name,
                    )
                    continue
                else:
                    # If not, we create one for month N-1
                    reporting_level = False
                    if declaration_type == "arrivals":
                        reporting_level = company.intrastat_arrivals
                    elif declaration_type == "dispatches":
                        reporting_level = company.intrastat_dispatches
                    if not reporting_level:
                        logger.warning(
                            "Missing reporting level for %s on company '%s'.",
                            declaration_type,
                            company.display_name,
                        )
                        continue
                    if reporting_level == "exempt":
                        logger.info(
                            "Reporting level is exempt for %s on company %s.",
                            declaration_type,
                            company.display_name,
                        )
                        continue
                    intrastat = self.create(
                        {
                            "company_id": company.id,
                            "declaration_type": declaration_type,
                            "reporting_level": reporting_level,
                        }
                    )
                    logger.info(
                        "An %s Intrastat Product for month %s "
                        "has been created by Odoo for company %s",
                        declaration_type,
                        previous_month,
                        company.display_name,
                    )
                    try:
                        intrastat.action_gather()
                    except Warning as e:
                        intrastat = intrastat.with_context(exception=True, error_msg=e)
                    # send the reminder e-mail
                    # TODO : how could we translate ${object.type}
                    # in the mail tpl ?
                    intrastat.send_reminder_email(
                        "l10n_fr_intrastat_product."
                        "l10n_fr_intrastat_product_reminder_email_template"
                    )
        return True


class L10nFrIntrastatProductComputationLine(models.Model):
    _name = "l10n.fr.intrastat.product.computation.line"
    _description = "DEB computation lines"
    _inherit = "intrastat.product.computation.line"

    parent_id = fields.Many2one(
        "l10n.fr.intrastat.product.declaration",
        string="Intrastat Product Declaration",
        ondelete="cascade",
        readonly=True,
    )
    declaration_line_id = fields.Many2one(
        "l10n.fr.intrastat.product.declaration.line",
        string="Declaration Line",
        readonly=True,
    )
    fr_partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        ondelete="restrict",
        help="Origin partner for arrivals. "
        "Destination partner (or his fiscal representative) for dispatches.",
    )
    fr_department_id = fields.Many2one(
        "res.country.department", string="Department", ondelete="restrict"
    )
    # the 2 fields below are useful for reports
    amount_company_currency_sign = fields.Float(
        compute="_compute_amount_company_currency_sign", store=True
    )
    amount_accessory_cost_company_currency_sign = fields.Float(
        compute="_compute_amount_company_currency_sign", store=True
    )

    @api.depends(
        "amount_company_currency",
        "amount_accessory_cost_company_currency",
        "transaction_id.fr_fiscal_value_multiplier",
    )
    def _compute_amount_company_currency_sign(self):
        for line in self:
            sign = line.transaction_id.fr_fiscal_value_multiplier or 1
            line.amount_company_currency_sign = sign * line.amount_company_currency
            line.amount_accessory_cost_company_currency_sign = (
                sign * line.amount_accessory_cost_company_currency
            )


class L10nFrIntrastatProductDeclarationLine(models.Model):
    _name = "l10n.fr.intrastat.product.declaration.line"
    _description = "DEB declaration lines"
    _inherit = "intrastat.product.declaration.line"

    parent_id = fields.Many2one(
        "l10n.fr.intrastat.product.declaration",
        string="Intrastat Product Declaration",
        ondelete="cascade",
        readonly=True,
    )
    computation_line_ids = fields.One2many(
        "l10n.fr.intrastat.product.computation.line",
        "declaration_line_id",
        string="Computation Lines",
        readonly=True,
    )
    fr_partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        help="Origin partner for arrivals. "
        "Destination partner (or his fiscal representative) for dispatches",
    )
    fr_department_id = fields.Many2one(
        "res.country.department", string="Departement", ondelete="restrict"
    )
    # the field below is useful for reports
    amount_company_currency_sign = fields.Float(
        compute="_compute_amount_company_currency_sign", store=True
    )

    @api.depends("amount_company_currency", "transaction_id.fr_fiscal_value_multiplier")
    def _compute_amount_company_currency_sign(self):
        for line in self:
            sign = line.transaction_id.fr_fiscal_value_multiplier or 1
            line.amount_company_currency_sign = sign * line.amount_company_currency

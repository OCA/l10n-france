# Copyright 2009-2022 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta
from lxml import etree, objectify

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

logger = logging.getLogger(__name__)


class IntrastatProductDeclaration(models.Model):
    _name = "intrastat.product.declaration"
    _inherit = [
        "intrastat.product.declaration",
        "report.intrastat_product.product_declaration_xls",
    ]
    _description = "EMEBI"

    total_amount = fields.Integer(compute="_compute_fr_numbers")
    # Inherit also num_decl_lines to avoid double loop
    num_decl_lines = fields.Integer(compute="_compute_fr_numbers")

    @api.depends("declaration_line_ids.amount_company_currency")
    def _compute_fr_numbers(self):
        for decl in self:
            total_amount = 0.0
            num_lines = 0
            for line in decl.declaration_line_ids:
                multi = 1
                if line.fr_regime_id:
                    multi = line.fr_regime_id.fiscal_value_multiplier
                total_amount += line.amount_company_currency * multi
                num_lines += 1
            decl.num_decl_lines = num_lines
            decl.total_amount = total_amount

    @api.constrains("reporting_level", "declaration_type")
    def _check_fr_declaration(self):
        for decl in self:
            if (
                decl.declaration_type == "arrivals"
                and decl.reporting_level == "standard"
                and decl.company_id.country_id.code == "FR"
            ):
                raise ValidationError(
                    _(
                        "In France, an arrival EMEBI cannot have a 'standard' reporting level."
                    )
                )

    def _prepare_invoice_domain(self):
        domain = super()._prepare_invoice_domain()
        if self.declaration_type == "arrivals":
            for index, entry in enumerate(domain):
                if entry[0] == "move_type":
                    domain.pop(index)
            domain.append(("move_type", "=", "in_invoice"))
        return domain

    def _get_region_code(self, inv_line, notedict):
        if self.company_id.country_id.code != "FR":
            return super()._get_region_code(inv_line, notedict)
        else:
            dpt = self._get_fr_department(inv_line, notedict)
            region_code = dpt and dpt.code or False
            return region_code

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
                    dpt = wh._get_fr_department()
                elif po_line.move_ids:
                    location = po_line.move_ids[0].location_dest_id
                    dpt = location._get_fr_department()
        elif move_type in ("out_invoice", "out_refund"):
            so_line = self.env["sale.order.line"].search(
                [("invoice_lines", "in", inv_line.id)], limit=1
            )
            if so_line:
                so = so_line.order_id
                dpt = so.warehouse_id._get_fr_department()
        if not dpt:
            dpt = self.company_id.partner_id.country_department_id
            if not dpt:
                msg = _(
                    "Missing department. "
                    "To set it, set the country and the zip code on this partner."
                )
                partner_name = self.company_id.partner_id.display_name
                notedict["partner"][partner_name][msg].add(notedict["inv_origin"])
        return dpt

    def _update_computation_line_vals(self, inv_line, line_vals, notedict):
        super()._update_computation_line_vals(inv_line, line_vals, notedict)
        if self.company_id.country_id.code == "FR":
            invoice = inv_line.move_id
            regime_code = False
            # TODO improve by taking into account the transaction code
            # to set the best regime code
            # example : if transaction code is 51/52 => regime code is 19 or 29
            if invoice.move_type == "in_invoice":
                regime_code = 11
            elif invoice.move_type == "out_refund":
                if invoice.intrastat_fiscal_position == "b2b":
                    regime_code = 25
                elif invoice.intrastat_fiscal_position == "b2c":
                    # TODO customer refund B2C : what are we supposed to do ?
                    # As we don't have a VAT number and regime 25 requires
                    # a VAT number, I decided for the moment not to mention
                    # it in EMEBI
                    line_vals.clear()
                    return
            elif invoice.move_type == "out_invoice":
                if invoice.intrastat_fiscal_position == "b2b":
                    regime_code = 21
                elif invoice.intrastat_fiscal_position == "b2c":
                    regime_code = 29
            if regime_code:
                regime = self.env.ref(
                    "l10n_fr_intrastat_product.fr_regime_%d" % regime_code
                )
                line_vals["fr_regime_id"] = regime.id

    def _generate_xml(self):
        """Generate the INSTAT XML file export."""
        if self.company_id.country_id.code != "FR":
            return super()._generate_xml()
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
        eu_countries = self.env.ref("base.europe").country_ids

        root = objectify.Element("INSTAT")
        envelope = objectify.SubElement(root, "Envelope")
        if not self.company_id.fr_intrastat_accreditation:
            self.message_post(
                body=_(
                    "No XML file generated because the <b>Customs Accreditation "
                    "Identifier</b> is not set on the accounting configuration "
                    "page of the company '%s'."
                )
                % self.company_id.display_name
            )
            return
        envelope.envelopeId = self.company_id.fr_intrastat_accreditation
        create_date_time = objectify.SubElement(envelope, "DateTime")
        now_user_tz = fields.Datetime.context_timestamp(self, datetime.now())
        create_date_time.date = datetime.strftime(now_user_tz, "%Y-%m-%d")
        create_date_time.time = datetime.strftime(now_user_tz, "%H:%M:%S")
        party = objectify.SubElement(
            envelope, "Party", partyType="PSI", partyRole="PSI"
        )
        party.partyId = my_company_identifier
        party.partyName = self.company_id.name
        envelope.softwareUsed = "Odoo"
        declaration = objectify.SubElement(envelope, "Declaration")
        declaration.declarationId = self.year_month.replace("-", "")
        declaration.referencePeriod = self.year_month
        declaration.PSIId = my_company_identifier
        function = objectify.SubElement(declaration, "Function")
        function.functionCode = "O"  # O = Déclaration originelle
        level2letter = {
            "standard": "4",
            "extended": "5",  # EMEBI 2022: stat + fisc, 2 in 1 combo
        }
        assert self.reporting_level in level2letter
        declaration.declarationTypeCode = level2letter[self.reporting_level]
        type2letter = {
            "arrivals": "A",
            "dispatches": "D",
        }
        assert self.declaration_type in type2letter
        declaration.flowCode = type2letter[self.declaration_type]
        assert my_company_currency == "EUR", "Company currency must be 'EUR'"
        declaration.currencyCode = my_company_currency

        # THEN, the fields which vary from a line to the next
        if not self.declaration_line_ids:
            raise UserError(
                _("No declaration lines. You probably forgot to generate " "them !")
            )
        line = 0
        for pline in self.declaration_line_ids:
            line += 1  # increment line number
            pline._generate_xml_line(declaration, eu_countries, line)

        objectify.deannotate(root, xsi_nil=True)
        etree.cleanup_namespaces(root)
        xml_bytes = etree.tostring(
            root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )
        # We validate the XML file against the official XML Schema Definition
        # Because we may catch some problems with the content
        # of the XML file this way
        self.company_id._intrastat_check_xml_schema(
            xml_bytes, "l10n_fr_intrastat_product/data/deb.xsd"
        )
        # Attach the XML file to the current object
        return xml_bytes

    @api.model
    def _scheduler_reminder(self):
        logger.info("Start EMEBI reminder")
        previous_month = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=-1), "%Y-%m"
        )
        # I can't search on [('country_id', '=', ..)]
        # because it is a fields.function not stored and without fnct_search
        companies = self.env["res.company"].search([])
        mail_template = self.env.ref(
            "l10n_fr_intrastat_product."
            "l10n_fr_intrastat_product_reminder_email_template"
        )
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
                        "An %s EMEBI for month %s has been created by Odoo for "
                        "company %s",
                        declaration_type,
                        previous_month,
                        company.display_name,
                    )
                    intrastat.message_post(
                        body=_(
                            "This EMEBI has been auto-generated by the EMEBI reminder "
                            "scheduled action."
                        )
                    )
                    try:
                        intrastat.action_gather()
                    except Warning as e:
                        intrastat = intrastat.with_context(exception=True, error_msg=e)
                    # send the reminder e-mail
                    # TODO : how could we translate ${object.type}
                    # in the mail tpl ?
                    if company.intrastat_remind_user_ids:
                        mail_template.send_mail(intrastat.id)
                        logger.info(
                            "EMEBI Reminder email has been sent to %s",
                            company.intrastat_email_list,
                        )
                    else:
                        logger.info(
                            "The list of users receiving the Intrastat Reminder "
                            "is empty on company %s",
                            company.display_name,
                        )
        logger.info("End of the EMEBI reminder")
        return

    @api.model
    def _xls_template(self):
        res = super()._xls_template()
        res.update(
            {
                "fr_regime_id": {
                    "header": {
                        "type": "string",
                        "value": _("Regime"),
                    },
                    "line": {
                        "value": self._render(
                            "line.fr_regime_id and line.fr_regime_id.display_name or ''"
                        ),
                    },
                    "width": 65,
                },
                "fr_regime_code": {
                    "header": {
                        "type": "string",
                        "value": _("Regime Code"),
                    },
                    "line": {
                        "value": self._render("line.fr_regime_code"),
                    },
                    "width": 8,
                },
            }
        )
        return res

    @api.model
    def _xls_computation_line_fields(self):
        res = super()._xls_computation_line_fields()
        res.insert(6, "fr_regime_id")
        return res

    @api.model
    def _xls_declaration_line_fields(self):
        res = super()._xls_declaration_line_fields()
        res.insert(3, "fr_regime_code")
        return res


class IntrastatProductComputationLine(models.Model):
    _inherit = "intrastat.product.computation.line"

    # regime is certainly not the best word in English
    # but the advantage is that, when we read the field name, we know what it is!
    fr_regime_id = fields.Many2one(
        "intrastat.fr.regime",
        domain="[('declaration_type', '=', declaration_type)]",
        string="Regime",
    )
    fr_regime_code = fields.Char(
        related="fr_regime_id.code", store=True, string="Regime Code"
    )

    def _group_line_hashcode_fields(self):
        res = super()._group_line_hashcode_fields()
        res["fr_regime_id"] = self.fr_regime_id.id or False
        return res

    def _prepare_grouped_fields(self, fields_to_sum):
        vals = super()._prepare_grouped_fields(fields_to_sum)
        vals["fr_regime_id"] = self.fr_regime_id.id or False
        return vals


class IntrastatProductDeclarationLine(models.Model):
    _inherit = "intrastat.product.declaration.line"

    fr_regime_id = fields.Many2one("intrastat.fr.regime", string="Regime")
    fr_regime_code = fields.Char(
        related="fr_regime_id.code", store=True, string="Regime Code"
    )

    # flake8: noqa: C901
    # TODO update error message to avoid quoting declaration line number
    def _generate_xml_line(self, parent_node, eu_countries, line_number):
        self.ensure_one()
        decl = self.parent_id
        assert self.fr_regime_id, "Missing Intrastat Type"
        transaction = self.transaction_id
        regime = self.fr_regime_id
        item = objectify.SubElement(parent_node, "Item")
        item.itemNumber = str(line_number)
        # START of elements which are only required in "detailed" level
        if decl.reporting_level == "extended" and not regime.is_fiscal_only:
            cn8 = objectify.SubElement(item, "CN8")
            if not self.hs_code_id:
                raise UserError(_("Missing H.S. code on line %d.") % line_number)
            # local_code is required=True, so no need to check it
            cn8.CN8Code = self.hs_code_id.local_code
            # We fill SUCode only if the H.S. code requires it
            iunit_id = self.intrastat_unit_id
            if iunit_id:
                cn8.SUCode = iunit_id.fr_xml_label or iunit_id.name

            if not self.src_dest_country_code:
                raise UserError(
                    _("Missing Country Code of Origin/Destination on line %d.")
                    % line_number
                )
            item.MSConsDestCode = self.src_dest_country_code

            # EMEBI 2022 : origin country is now for arrival AND dispatches
            if not self.product_origin_country_code:
                raise UserError(
                    _("Missing product country of origin code on line %d.")
                    % line_number
                )
            item.countryOfOriginCode = self.product_origin_country_code

            if not self.weight:
                raise UserError(_("Missing weight on line %d.") % line_number)
            item.netMass = str(self.weight)

            if iunit_id:
                if not self.suppl_unit_qty:
                    raise UserError(_("Missing quantity on line %d.") % line_number)
                item.quantityInSU = str(self.suppl_unit_qty)

        # START of elements that are part of all EMEBIs
        if not self.amount_company_currency:
            raise UserError(_("Missing fiscal value on line %d.") % line_number)
        item.invoicedAmount = str(self.amount_company_currency)
        # EMEBI 2022 : Partner VAT now required for all dispatches with
        # some exceptions for regime 29 in case of B2C
        if decl.declaration_type == "dispatches":
            if not self.vat and regime.code != "29":
                raise UserError(_("Missing VAT number on line %d.") % line_number)
            if self.vat and self.vat.startswith("GB") and decl.year >= "2021":
                raise UserError(
                    _(
                        "Bad VAT number '%(vat)s' on line %(line_number)d. "
                        "Brexit took place on January 1st 2021 and companies "
                        "in Northern Ireland have a new VAT number starting with 'XI'."
                    )
                    % {"vat": self.vat, "line_number": line_number}
                )
            item.partnerId = self.vat or ""
        # Code régime is on all EMEBIs
        item.statisticalProcedureCode = regime.code

        # START of elements which are only required in "detailed" level
        if decl.reporting_level == "extended" and not regime.is_fiscal_only:
            transaction_nature = objectify.SubElement(item, "NatureOfTransaction")
            transaction_nature.natureOfTransactionACode = transaction.code[0]
            if len(transaction.code) != 2:
                raise UserError(
                    _("Transaction code on line %d should have 2 digits.") % line_number
                )
            transaction_nature.natureOfTransactionBCode = transaction.code[1]
            if not self.transport_id:
                raise UserError(
                    _("Mode of transport is not set on line %d.") % line_number
                )
            item.modeOfTransportCode = str(self.transport_id.code)
            if not self.region_code:
                raise UserError(_("Region Code is not set on line %d.") % line_number)
            item.regionCode = self.region_code

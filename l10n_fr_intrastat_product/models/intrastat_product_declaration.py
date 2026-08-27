# Copyright 2009-2022 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta
from lxml import etree, objectify

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain

logger = logging.getLogger(__name__)


class IntrastatProductDeclaration(models.Model):
    _name = "intrastat.product.declaration"
    _inherit = [
        "intrastat.product.declaration",
        "report.intrastat_product.product_declaration_xls",
    ]
    _description = "EMEBI"

    def _compute_numbers(self):
        res = super()._compute_numbers()
        for decl in self:
            if decl.company_id.country_id.code == "FR":
                total_amount = 0
                for line in decl.declaration_line_ids:
                    multi = 1
                    if line.fr_regime_id:
                        multi = line.fr_regime_id.fiscal_value_multiplier
                    total_amount += int(round(line.amount_company_currency)) * multi
                decl.total_amount = total_amount
        return res

    @api.constrains("reporting_level", "declaration_type")
    def _check_fr_declaration(self):
        for decl in self:
            if (
                decl.declaration_type == "arrivals"
                and decl.reporting_level == "standard"
                and decl.company_id.country_id.code == "FR"
            ):
                raise ValidationError(
                    self.env._(
                        "In France, an arrival EMEBI cannot have a 'standard' "
                        "reporting level."
                    )
                )

    def _prepare_invoice_domain(self):
        domain = super()._prepare_invoice_domain()
        if self.declaration_type == "arrivals":
            # Drop the existing ``move_type`` condition
            domain = domain.map_conditions(
                lambda cond: Domain.TRUE if cond.field_expr == "move_type" else cond
            )
            domain &= Domain("move_type", "=", "in_invoice")
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
                Domain("invoice_lines", "in", inv_line.id), limit=1
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
                Domain("invoice_lines", "in", inv_line.id), limit=1
            )
            if so_line:
                so = so_line.order_id
                dpt = so.warehouse_id._get_fr_department()
        if not dpt:
            dpt = self.company_id.partner_id.country_department_id
            if not dpt:
                msg = self.env._(
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
                    # 29 is only for EMEBI (extended),
                    # not for the fiscal declaration (standard)
                    if self.reporting_level == "standard":
                        line_vals.clear()
                        return
                    else:
                        regime_code = 29
            if regime_code:
                regime = self.env.ref(
                    f"l10n_fr_intrastat_product.fr_regime_{regime_code}"
                )
                line_vals["fr_regime_id"] = regime.id

    def _prepare_xml_data(self):
        self.ensure_one()
        if self.action != "replace" or self.revision != 1:
            raise UserError(
                self.env._(
                    "Pro.dou@ne only accepts XML file upload for "
                    "the original declaration."
                )
            )
        if not self.declaration_line_ids:
            raise UserError(
                self.env._(
                    "No declaration lines. You probably forgot to generate them !"
                )
            )
        if not self.company_id.fr_intrastat_accreditation:
            msg = self.env._(
                "The Customs Accreditation Identifier is not set for the company '%s'.",
                self.company_id.display_name,
            )
            self._account_config_warning(msg)

        my_company_vat = self.company_id.partner_id.vat.replace(" ", "")
        company_siren = self.company_id._get_siren(raise_if_none=True)
        my_company_currency = self.company_id.currency_id.name
        assert self.company_id.currency_id.name == "EUR"
        level2letter = {
            "standard": "4",
            "extended": "5",  # EMEBI 2022: stat + fisc, 2 in 1 combo
        }
        assert self.reporting_level in level2letter
        type2letter = {
            "arrivals": "A",
            "dispatches": "D",
        }
        assert self.declaration_type in type2letter
        now_user_tz = fields.Datetime.context_timestamp(self, datetime.now())

        data = {
            "my_company_vat": my_company_vat,
            "my_company_identifier": my_company_vat + company_siren,
            "my_company_name": self.company_id.name,
            "my_company_currency": my_company_currency,
            "accreditation": self.company_id.fr_intrastat_accreditation,
            "date": datetime.strftime(now_user_tz, "%Y-%m-%d"),
            "time": datetime.strftime(now_user_tz, "%H:%M:%S"),
            "soft": "Odoo",
            "decl_id": self.year_month.replace("-", ""),
            "period": self.year_month,
            "function_code": "O",  # O = Déclaration originelle
            "decl_type_code": level2letter[self.reporting_level],
            "flow_code": type2letter[self.declaration_type],
            "currency_code": "EUR",
            "lines": [
                line._prepare_xml_line_data() for line in self.declaration_line_ids
            ],
        }
        return data

    def _generate_xml(self):
        """Generate the INSTAT XML file export."""
        if self.company_id.country_id.code != "FR":
            return super()._generate_xml()
        data = self._prepare_xml_data()

        E = objectify.ElementMaker(annotate=False)
        root = E.INSTAT(
            E.Envelope(
                E.envelopeId(data["accreditation"]),
                E.DateTime(
                    E.date(data["date"]),
                    E.time(data["time"]),
                ),
                E.Party(
                    E.partyId(data["my_company_identifier"]),
                    E.partyName(data["my_company_name"]),
                    partyType="PSI",
                    partyRole="PSI",
                ),
                E.softwareUsed("Odoo"),
                E.Declaration(
                    E.declarationId(data["decl_id"]),
                    E.referencePeriod(data["period"]),
                    E.PSIId(data["my_company_identifier"]),
                    E.Function(
                        E.functionCode(data["function_code"]),
                    ),
                    E.declarationTypeCode(data["decl_type_code"]),
                    E.flowCode(data["flow_code"]),
                    E.currencyCode(data["currency_code"]),
                    *[
                        E.Item(
                            E.itemNumber(ldata["line_number"]),
                            *[
                                E.CN8(
                                    E.CN8Code(ldata["hs_code"]),
                                    *[
                                        E.SUCode(ldata["unit_code"])
                                        for _ in [1]
                                        if ldata.get("unit_code")
                                    ],
                                )
                                for _ in [1]
                                if ldata.get("hs_code")
                            ],
                            *[
                                E.MSConsDestCode(ldata["src_dest_country_code"])
                                for _ in [1]
                                if ldata.get("src_dest_country_code")
                            ],
                            *[
                                E.countryOfOriginCode(
                                    ldata["product_origin_country_code"]
                                )
                                for _ in [1]
                                if ldata.get("product_origin_country_code")
                            ],
                            *[
                                E.netMass(ldata["weight"])
                                for _ in [1]
                                if ldata.get("weight")
                            ],
                            *[
                                E.quantityInSU(ldata["qty"])
                                for _ in [1]
                                if ldata.get("qty")
                            ],
                            E.invoicedAmount(ldata["amount"]),
                            *[E.partnerId(ldata["vat"]) for _ in [1] if "vat" in ldata],
                            E.statisticalProcedureCode(ldata["regime_code"]),
                            *[
                                E.NatureOfTransaction(
                                    E.natureOfTransactionACode(
                                        ldata["nature_code_first_digit"]
                                    ),
                                    E.natureOfTransactionBCode(
                                        ldata["nature_code_second_digit"]
                                    ),
                                )
                                for _ in [1]
                                if ldata.get("nature_code_first_digit")
                            ],
                            *[
                                E.modeOfTransportCode(ldata["transport_code"])
                                for _ in [1]
                                if ldata.get("transport_code")
                            ],
                            *[
                                E.regionCode(ldata["region_code"])
                                for _ in [1]
                                if ldata.get("region_code")
                            ],
                        )
                        for ldata in data["lines"]
                    ],
                ),
            )
        )

        xml_bytes = etree.tostring(
            root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )
        # Validate XML file against the official XSD
        self.company_id._intrastat_check_xml_schema(
            xml_bytes, "l10n_fr_intrastat_product/data/deb.xsd"
        )
        return xml_bytes

    @api.model
    def _scheduler_reminder(self):
        logger.info("Start EMEBI reminder")
        previous_month = datetime.strftime(
            datetime.today() + relativedelta(day=1, months=-1), "%Y-%m"
        )
        # I can't search on [('country_id', '=', ..)]
        # because it is a fields.function not stored and without fnct_search
        companies = self.env["res.company"].search(Domain.TRUE)
        mail_template = self.env.ref(
            "l10n_fr_intrastat_product."
            "l10n_fr_intrastat_product_reminder_email_template"
        )
        for company in companies:
            if company.country_id.code != "FR":
                continue
            for declaration_type in ["arrivals", "dispatches"]:
                # Check if a declaration already exists for month N-1
                intrastat_count = self.search_count(
                    Domain("year_month", "=", previous_month)
                    & Domain("declaration_type", "=", declaration_type)
                    & Domain("company_id", "=", company.id)
                )
                if intrastat_count:
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
                        body=self.env._(
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
                        "value": self.env._("Regime"),
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
                        "value": self.env._("Regime Code"),
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

    def _prepare_declaration_line(self, line_number):
        vals = super()._prepare_declaration_line(line_number)
        if self[0].company_id.country_id and self[0].company_id.country_id.code == "FR":
            fields_to_sum = self._fields_to_sum()
            for field in fields_to_sum:
                vals[field] = int(round(vals[field]))
            # the EMEBI specs say that, if the value for weight and suppl_unit_qty
            # is between 0 and 0.5, it should be rounded to 1
            if not vals["weight"]:
                vals["weight"] = 1
            if vals["intrastat_unit_id"] and not vals["suppl_unit_qty"]:
                vals["suppl_unit_qty"] = 1
            vals["amount_company_currency"] = int(
                round(vals["amount_company_currency"])
            )
            if (
                self[0].transaction_id
                and self[0].transaction_id.code == "12"
                and self[0].fr_regime_id
                and self[0].fr_regime_id.code == "29"
                and not self[0].vat
            ):
                vals["vat"] = "QN999999999999"
        return vals


class IntrastatProductDeclarationLine(models.Model):
    _inherit = "intrastat.product.declaration.line"

    fr_regime_id = fields.Many2one("intrastat.fr.regime", string="Regime")
    fr_regime_code = fields.Char(
        related="fr_regime_id.code", store=True, string="Regime Code"
    )

    def _prepare_xml_line_data(self):
        self.ensure_one()

        decl = self.parent_id
        assert self.fr_regime_id, "Missing Intrastat Type"
        transaction = self.transaction_id
        regime = self.fr_regime_id
        # no need for is_zero() because amount_company_currency is an integer
        # on decl lines
        if not self.amount_company_currency:
            raise UserError(
                self.env._(
                    "Missing fiscal value on declaration line %d.", self.line_number
                )
            )

        ldata = {
            "line_number": self.line_number,
            # amount_company_currency is a Monetary field but the DEB XSD
            # requires invoicedAmount to be an xsd:integer
            "amount": round(self.amount_company_currency),
            "regime_code": regime.code,
        }

        if decl.declaration_type == "dispatches":
            if not self.vat:
                raise UserError(
                    self.env._(
                        "Missing VAT number on declaration line %d.", self.line_number
                    )
                )
            if self.vat and self.vat.startswith("GB") and decl.year >= "2021":
                raise UserError(
                    self.env._(
                        "Bad VAT number '%(vat)s' on declaration line %(line_number)d. "
                        "Brexit took place on January 1st 2021 and companies "
                        "in Northern Ireland have a new VAT number starting with 'XI'.",
                        vat=self.vat,
                        line_number=self.line_number,
                    )
                )
            ldata["vat"] = self.vat or ""

        if decl.reporting_level == "extended" and not regime.is_fiscal_only:
            if not self.hs_code_id:
                raise UserError(
                    self.env._(
                        "Missing H.S. code on declaration line %d.", self.line_number
                    )
                )
            if not self.src_dest_country_code:
                raise UserError(
                    self.env._(
                        "Missing country code of origin/destination on "
                        "declaration line %d.",
                        self.line_number,
                    )
                )
            # EMEBI 2022 : origin country is now for arrival AND dispatches
            if not self.product_origin_country_code:
                raise UserError(
                    self.env._(
                        "Missing product country of origin code "
                        "on declaration line %d.",
                        self.line_number,
                    )
                )
            # no need for float_is_zero() because weight is an integer on decl lines
            if not self.weight:
                raise UserError(
                    self.env._(
                        "Missing weight on declaration line %d.", self.line_number
                    )
                )
            if not transaction:
                raise UserError(
                    self.env._(
                        "Missing intrastat transaction on declaration line %d.",
                        self.line_number,
                    )
                )
            if len(transaction.code) != 2 or not transaction.code.isdigit():
                raise UserError(
                    self.env._(
                        "Transaction code on declaration line %d should have 2 digits.",
                        self.line_number,
                    )
                )
            if not self.transport_id:
                raise UserError(
                    self.env._(
                        "Missing mode of transport on declaration line %d.",
                        self.line_number,
                    )
                )
            if not self.region_code:
                raise UserError(
                    self.env._(
                        "Missing region code on declaration line %d.", self.line_number
                    )
                )

            ldata.update(
                {
                    "hs_code": self.hs_code_id.local_code,
                    "src_dest_country_code": self.src_dest_country_code,
                    "product_origin_country_code": self.product_origin_country_code,
                    # weight is a Float field but the DEB XSD requires netMass
                    # to be an xsd:integer
                    "weight": round(self.weight),
                    "nature_code_first_digit": transaction.code[0],
                    "nature_code_second_digit": transaction.code[1],
                    "transport_code": self.transport_id.code,
                    "region_code": self.region_code,
                }
            )
            iunit_id = self.intrastat_unit_id
            if iunit_id:
                # no need for float_is_zero() because suppl_unit_qty is an integer
                # on declaration lines
                if not self.suppl_unit_qty:
                    raise UserError(
                        self.env._(
                            "Missing quantity on declaration line %d.", self.line_number
                        )
                    )
                ldata["unit_code"] = iunit_id.fr_xml_label or iunit_id.name
                ldata["qty"] = self.suppl_unit_qty
        return ldata

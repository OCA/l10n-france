# Copyright 2010-2022 Akretion France (http://www.akretion.com/)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import logging

from dateutil.relativedelta import relativedelta
from lxml import etree
from stdnum import vatin

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

logger = logging.getLogger(__name__)


class L10nFrIntrastatServiceDeclaration(models.Model):
    _name = "l10n.fr.intrastat.service.declaration"
    _order = "year_month desc"
    _rec_name = "year_month"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "DES"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        states={"done": [("readonly", True)]},
        default=lambda self: self.env.company,
    )
    start_date = fields.Date(
        required=True,
        default=lambda self: self._default_start_date(),
        states={"done": [("readonly", True)]},
    )
    end_date = fields.Date(compute="_compute_dates", store=True)
    year_month = fields.Char(
        compute="_compute_dates", store=True, string="Period", tracking=True
    )
    declaration_line_ids = fields.One2many(
        "l10n.fr.intrastat.service.declaration.line",
        "parent_id",
        string="DES Lines",
        states={"done": [("readonly", True)]},
        copy=False,
    )
    num_decl_lines = fields.Integer(
        compute="_compute_numbers", string="Number of Lines", store=True, tracking=True
    )
    # For the field 'total_amount', we could have used a fields.Integer
    # like for the field 'amount_company_currency' on lines. But this field is not
    # used in the DES, so it's not an important field, therefore it's simpler
    # to use a fields.Monetary (no need to explicitly define the widget and
    # currency in views)
    total_amount = fields.Monetary(
        compute="_compute_numbers",
        currency_field="currency_id",
        store=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id", string="Company Currency", store=True
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
        ],
        readonly=True,
        tracking=True,
        default="draft",
        copy=False,
    )
    attachment_id = fields.Many2one("ir.attachment")
    attachment_datas = fields.Binary(related="attachment_id.datas", string="XML Export")
    attachment_name = fields.Char(related="attachment_id.name", string="XML Filename")

    _sql_constraints = [
        (
            "date_uniq",
            "unique(year_month, company_id)",
            "A DES already exists for this month!",
        )
    ]

    @api.constrains("start_date")
    def _check_start_date(self):
        for rec in self:
            if rec.start_date and rec.start_date.day != 1:
                raise ValidationError(
                    _("The start date must be the first day of a month.")
                )

    @api.depends("declaration_line_ids.amount_company_currency")
    def _compute_numbers(self):
        rg_res = self.env["l10n.fr.intrastat.service.declaration.line"].read_group(
            [("parent_id", "in", self.ids)],
            ["parent_id", "amount_company_currency"],
            ["parent_id"],
        )
        data = {
            x["parent_id"][0]: {
                "total_amount": x["amount_company_currency"],
                "num_decl_lines": x["parent_id_count"],
            }
            for x in rg_res
        }
        for rec in self:
            rec.write(data.get(rec.id, {}))

    @api.depends("start_date")
    def _compute_dates(self):
        for rec in self:
            end_date = year_month = False
            if rec.start_date:
                end_date = rec.start_date + relativedelta(day=31)
                year_month = fields.Date.to_string(rec.start_date)[:7]
            rec.end_date = end_date
            rec.year_month = year_month

    @api.model
    def _default_start_date(self):
        return fields.Date.context_today(self) - relativedelta(months=1, day=1)

    @api.onchange("start_date")
    def start_date_change(self):
        if self.start_date and self.start_date.day != 1:
            self.start_date = self.start_date + relativedelta(day=1)

    def unlink(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(
                    _("Cannot delete '%s' because it is in Done state.")
                    % rec.display_name
                )
        return super().unlink()

    @api.depends("year_month")
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, "DES %s" % rec.year_month))
        return res

    def _prepare_domain(self):
        self.ensure_one()
        domain = [
            ("move_type", "in", ("out_invoice", "out_refund")),
            ("invoice_date", "<=", self.end_date),
            ("invoice_date", ">=", self.start_date),
            ("state", "=", "posted"),
            ("intrastat_fiscal_position", "=", True),
            ("company_id", "=", self.company_id.id),
        ]
        return domain

    def _is_service(self, invoice_line):
        if invoice_line.product_id.type == "service":
            return True
        else:
            return False

    def generate_service_lines(self):
        self.ensure_one()
        line_obj = self.env["l10n.fr.intrastat.service.declaration.line"]
        amo = self.env["account.move"]
        # delete all DES lines generated from invoices
        lines_to_remove = line_obj.search(
            [("move_id", "!=", False), ("parent_id", "=", self.id)]
        )
        lines_to_remove.unlink()
        company_currency = self.company_id.currency_id
        invoices = amo.search(self._prepare_domain(), order="invoice_date")
        for invoice in invoices:
            if (
                invoice.commercial_partner_id.country_id.code == "GB"
                and self.year_month >= "2021-01"
            ):
                logger.info(
                    "Skipping invoice %s because of Brexit and the fact that "
                    "services sold in Northern Ireland are not under the EU "
                    "VAT regime",
                    invoice.name,
                )
                continue
            amount_invoice_cur_to_write = 0.0
            amount_company_cur_to_write = 0.0
            amount_invoice_cur_regular_service = 0.0
            amount_invoice_cur_accessory_cost = 0.0
            regular_product_in_invoice = False

            for line in invoice.invoice_line_ids.filtered(
                lambda x: not x.display_type and x.product_id
            ):
                # If we have a regular product/consu in the invoice, we
                # don't take the is_accessory_cost in DES (it will be in DEB)
                # If we don't, we declare the is_accessory_cost in DES as other
                # regular services
                if not self._is_service(line):
                    regular_product_in_invoice = True
                    continue

                # This check on line.price_subtotal must be AFTER the check
                # on line.product_id.type != 'service' in order to handle
                # the case where we have in an invoice :
                # - some HW products with value = 0
                # - some accessory costs
                # => we want to have the accessory costs in DEB, not in DES
                if line.currency_id.is_zero(line.price_subtotal):
                    continue

                if line.product_id.is_accessory_cost:
                    amount_invoice_cur_accessory_cost += line.price_subtotal
                else:
                    amount_invoice_cur_regular_service += line.price_subtotal

            # END of the loop on invoice lines
            if regular_product_in_invoice:
                amount_invoice_cur_to_write = amount_invoice_cur_regular_service
            else:
                amount_invoice_cur_to_write = (
                    amount_invoice_cur_regular_service
                    + amount_invoice_cur_accessory_cost
                )

            amount_company_cur_to_write = int(
                round(
                    invoice.currency_id._convert(
                        amount_invoice_cur_to_write,
                        company_currency,
                        self.company_id,
                        invoice.invoice_date,
                    )
                )
            )

            if amount_company_cur_to_write:
                if invoice.move_type == "out_refund":
                    amount_invoice_cur_to_write *= -1
                    amount_company_cur_to_write *= -1

                # Why do I check that the Partner has a VAT number
                # only here and not earlier ? Because, if I sell
                # to a physical person in the EU with VAT, then
                # the corresponding partner will not have a VAT
                # number, and the entry will be skipped because
                # line_tax.exclude_from_intrastat_if_present is
                # always True and amount_company_cur_to_write = 0
                # So we should not block with a raise before the
                # end of the loop on the invoice lines and the "if
                # amount_company_cur_to_write:"
                if not invoice.commercial_partner_id.vat:
                    raise UserError(
                        _("Missing VAT number on partner '%s'.")
                        % invoice.commercial_partner_id.display_name
                    )
                else:
                    partner_vat_to_write = invoice.commercial_partner_id.vat

                line_obj.create(
                    {
                        "parent_id": self.id,
                        "move_id": invoice.id,
                        "partner_vat": partner_vat_to_write,
                        "partner_id": invoice.commercial_partner_id.id,
                        "invoice_currency_id": invoice.currency_id.id,
                        "amount_invoice_currency": amount_invoice_cur_to_write,
                        "amount_company_currency": amount_company_cur_to_write,
                    }
                )
        self.message_post(body=_("Re-generating lines from invoices"))
        return

    def done(self):
        self.write({"state": "done"})

    def back2draft(self):
        for decl in self:
            if decl.attachment_id:
                raise UserError(
                    _("Before going back to draft, you must delete the XML export.")
                )
        self.write({"state": "draft"})

    def _generate_des_xml_root(self):
        self.ensure_one()
        if not self.company_id.partner_id.vat:
            raise UserError(
                _("Missing VAT number on company '%s'.") % self.company_id.display_name
            )
        my_company_vat = self.company_id.partner_id.vat.replace(" ", "")

        # Tech spec of XML export are available here :
        # https://www.douane.gouv.fr/sites/default/files/uploads/files/2020-10/ManuelDesXML.pdf # noqa
        root = etree.Element("fichier_des")
        decl = etree.SubElement(root, "declaration_des")
        num_des = etree.SubElement(decl, "num_des")
        num_des.text = self.year_month.replace("-", "")
        num_tva = etree.SubElement(decl, "num_tvaFr")
        num_tva.text = my_company_vat
        mois_des = etree.SubElement(decl, "mois_des")
        mois_des.text = self.year_month[5:7]
        # month 2 digits
        an_des = etree.SubElement(decl, "an_des")
        an_des.text = self.year_month[:4]
        line = 0
        # we now go through each service line
        for sline in self.declaration_line_ids:
            line += 1  # increment line number
            ligne_des = etree.SubElement(decl, "ligne_des")
            numlin_des = etree.SubElement(ligne_des, "numlin_des")
            numlin_des.text = str(line)
            valeur = etree.SubElement(ligne_des, "valeur")
            valeur.text = str(sline.amount_company_currency)
            partner_des = etree.SubElement(ligne_des, "partner_des")
            vat = sline.partner_vat.replace(" ", "")
            if not vat:
                raise UserError(
                    _("Missing VAT number on partner '%s'.")
                    % sline.partner_id.display_name
                )
            if vat.startswith("GB") and self.year_month >= "2021-01":
                raise UserError(
                    _(
                        "VAT Number '%s' cannot be used because Brexit took "
                        "place on January 1st 2021 and services sold "
                        "in Northern Ireland are not under the EU VAT regime."
                    )
                    % vat
                )
            partner_des.text = vat
        return root

    def generate_xml(self):
        self.ensure_one()
        if self.attachment_id:
            raise UserError(
                _(
                    "An XML Export already exists for %s. "
                    "To re-generate it, you must first delete it."
                )
                % self.display_name
            )
        root = self._generate_des_xml_root()
        xml_bytes = etree.tostring(
            root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )

        # We now validate the XML file against the official XSD
        self.company_id._intrastat_check_xml_schema(
            xml_bytes, "l10n_fr_intrastat_service/data/des.xsd"
        )
        # Attach the XML file
        attach_id = self._attach_xml_file(xml_bytes)
        self.write({"attachment_id": attach_id})

    def _attach_xml_file(self, xml_bytes):
        self.ensure_one()
        filename = "%s_des.xml" % self.year_month
        attach = self.env["ir.attachment"].create(
            {
                "name": filename,
                "res_id": self.id,
                "res_model": self._name,
                "raw": xml_bytes,
            }
        )
        return attach.id

    def delete_xml(self):
        self.ensure_one()
        self.attachment_id and self.attachment_id.unlink()

    @api.model
    def _scheduler_reminder(self):
        logger.info("Start DES reminder")
        previous_month = fields.Date.context_today(self) + relativedelta(
            day=1, months=-1
        )
        # I can't search on [('country_id', '=', ...)]
        # because it is a fields.function not stored and without fnct_search
        fr_countries = self.env["res.country"].search(
            [("code", "in", ("FR", "GP", "MQ", "GF", "RE", "YT"))]
        )
        companies = self.env["res.company"].search(
            [("partner_id.country_id", "in", fr_countries.ids)]
        )
        mail_template = self.env.ref(
            "l10n_fr_intrastat_service.intrastat_service_reminder_email_template"
        )
        for company in companies:
            # Check if a DES already exists for month N-1
            intrastats = self.search(
                [("start_date", "=", previous_month), ("company_id", "=", company.id)]
            )
            # if it already exists, we don't do anything
            # in the future, we may check the state and send a mail
            # if the state is still in draft ?
            if intrastats:
                logger.info(
                    "A DES for month %s already exists for company %s",
                    previous_month,
                    company.name,
                )
            else:
                # If not, we create an intrastat.service for month N-1
                intrastat = self.create({"company_id": company.id})
                intrastat.message_post(
                    body=_(
                        "This DES has been auto-generated by the DES reminder "
                        "scheduled action."
                    )
                )
                logger.info(
                    "A DES for month %s has been created by Odoo for " "company %s",
                    previous_month,
                    company.name,
                )
                # we try to generate the lines
                exception = error_msg = False
                try:
                    intrastat.generate_service_lines()
                except UserError as e:
                    exception = True
                    error_msg = e
                # send the reminder email
                if company.intrastat_remind_user_ids:
                    mail_template.with_context(
                        exception=exception, error_msg=error_msg
                    ).send_mail(intrastat.id)
                    logger.info(
                        "DES Reminder email has been sent to %s",
                        company.intrastat_email_list,
                    )
                else:
                    logger.info(
                        "The list of users receiving the Intrastat Reminder is "
                        "empty on company %s",
                        company.display_name,
                    )
        logger.info("End of the DES reminder")
        return

    def create_xlsx(self):
        action = {
            "type": "ir.actions.report",
            "report_type": "xlsx",
            "report_name": "l10n.fr.intrastat.service.declaration.xlsx",
            "context": dict(self.env.context),
            "data": {"dynamic_report": True},
        }
        return action


class L10nFrIntrastatServiceDeclarationLine(models.Model):
    _name = "l10n.fr.intrastat.service.declaration.line"
    _description = "DES Line"
    _rec_name = "partner_vat"
    _order = "id"

    parent_id = fields.Many2one(
        "l10n.fr.intrastat.service.declaration",
        string="DES",
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company", related="parent_id.company_id", string="Company", store=True
    )
    company_currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Company Currency",
        store=True,
    )
    move_id = fields.Many2one(
        "account.move", string="Invoice", readonly=True, ondelete="restrict"
    )
    invoice_date = fields.Date(
        related="move_id.invoice_date", string="Invoice Date", store=True
    )
    partner_vat = fields.Char(string="Customer VAT", required=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner Name",
        ondelete="restrict",
        domain=[("parent_id", "=", False)],
    )
    amount_company_currency = fields.Integer(
        string="Amount",
        required=True,
        help="Amount in company currency to write in the declaration. "
        "Amount in company currency = amount in invoice currency "
        "converted to company currency with the rate of the invoice "
        "date and rounded at 0 digits",
    )
    amount_invoice_currency = fields.Monetary(
        string="Amount in Invoice Currency",
        readonly=True,
        currency_field="invoice_currency_id",
    )
    invoice_currency_id = fields.Many2one(
        "res.currency", "Invoice Currency", readonly=True
    )

    @api.onchange("partner_id")
    def partner_on_change(self):
        if self.partner_id and self.partner_id.vat:
            self.partner_vat = self.partner_id.vat

    @api.constrains("partner_vat")
    def _check_partner_vat(self):
        for line in self:
            if line.partner_vat and not vatin.is_valid(line.partner_vat):
                raise ValidationError(
                    _("The VAT number '%s' is invalid.") % line.partner_vat
                )

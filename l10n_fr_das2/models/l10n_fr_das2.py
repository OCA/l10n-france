# Copyright 2020-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import logging
from datetime import datetime

from stdnum.fr.siret import is_valid

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

logger = logging.getLogger(__name__)

try:
    from unidecode import unidecode
except ImportError:
    unidecode = False
    logger.debug("Cannot import unidecode")


FRANCE_CODES = (
    "FR",
    "GP",
    "MQ",
    "GF",
    "RE",
    "YT",
    "NC",
    "PF",
    "TF",
    "MF",
    "BL",
    "PM",
    "WF",
)
AMOUNT_FIELDS = [
    "fee_amount",
    "commission_amount",
    "brokerage_amount",
    "discount_amount",
    "attendance_fee_amount",
    "copyright_royalties_amount",
    "licence_royalties_amount",
    "other_income_amount",
    "allowance_amount",
    "benefits_in_kind_amount",
    "withholding_tax_amount",
]


class L10nFrDas2(models.Model):
    _name = "l10n.fr.das2"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "year desc"
    _description = "DAS2"

    year = fields.Integer(
        string="Year",
        required=True,
        states={"done": [("readonly", True)]},
        tracking=True,
        default=lambda self: self._default_year(),
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
        ],
        default="draft",
        readonly=True,
        string="State",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        ondelete="cascade",
        required=True,
        states={"done": [("readonly", True)]},
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        readonly=True,
        store=True,
        string="Company Currency",
    )
    payment_journal_ids = fields.Many2many(
        "account.journal",
        string="Payment Journals",
        required=True,
        default=lambda self: self._default_payment_journals(),
        domain="[('company_id', '=', company_id)]",
        states={"done": [("readonly", True)]},
    )
    line_ids = fields.One2many(
        "l10n.fr.das2.line",
        "parent_id",
        string="Lines",
        states={"done": [("readonly", True)]},
    )
    partner_declare_threshold = fields.Integer(
        string="Partner Declaration Threshold", readonly=True
    )
    dads_type = fields.Selection(
        [
            ("4", "La société verse des salaires"),
            ("1", "La société ne verse pas de salaires"),
        ],
        "DADS Type",
        required=True,
        states={"done": [("readonly", True)]},
        tracking=True,
        default=lambda self: self._default_dads_type(),
    )
    # option for draft moves ?
    contact_id = fields.Many2one(
        "res.partner",
        string="Administrative Contact",
        states={"done": [("readonly", True)]},
        default=lambda self: self.env.user.partner_id.id,
        tracking=True,
        help="Contact in the company for the fiscal administration: the name, "
        "email and phone number of this partner will be used in the file.",
    )
    attachment_id = fields.Many2one("ir.attachment", string="Attachment", readonly=True)
    attachment_datas = fields.Binary(
        related="attachment_id.datas", string="File Export"
    )
    attachment_name = fields.Char(related="attachment_id.name", string="Filename")
    # The only drawback of the warning_msg solution is that I didn't find a way
    # to put a link to partners inside it
    warning_msg = fields.Html(readonly=True)

    _sql_constraints = [
        (
            "year_company_uniq",
            "unique(company_id, year)",
            "A DAS2 already exists for that year!",
        )
    ]

    @api.model
    def _default_dads_type(self):
        previous_decl = self.search(
            [("dads_type", "!=", False)], order="year desc", limit=1
        )
        if previous_decl:
            return previous_decl.dads_type
        else:
            return "4"

    @api.model
    def _default_payment_journals(self):
        res = []
        pay_journals = self.env["account.journal"].search(
            [("type", "in", ("bank", "cash")), ("company_id", "=", self.env.company.id)]
        )
        if pay_journals:
            res = pay_journals.ids
        return res

    @api.model
    def _default_year(self):
        last_year = datetime.today().year - 1
        return last_year

    @api.depends("year")
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, "DAS2 %s" % rec.year))
        return res

    def done(self):
        self.write({"state": "done"})
        return

    def back2draft(self):
        self.write({"state": "draft"})
        return

    def unlink(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(
                    _("Cannot delete declaration %s in done state.") % rec.display_name
                )
        return super().unlink()

    def generate_lines(self):
        self.ensure_one()
        lfdlo = self.env["l10n.fr.das2.line"]
        company = self.company_id
        if not company.country_id:
            raise UserError(
                _("Country not set on company '%s'.") % company.display_name
            )
        if company.country_id.code not in FRANCE_CODES:
            raise UserError(
                _(
                    "Company '%s' is configured in country '%s'. The DAS2 is "
                    "only for France and it's oversea territories."
                )
                % (company.display_name, company.country_id.name)
            )
        if company.currency_id != self.env.ref("base.EUR"):
            raise UserError(
                _("Company '%s' is configured with currency '%s'. " "It should be EUR.")
                % (company.display_name, company.currency_id.name)
            )
        if company.fr_das2_partner_declare_threshold <= 0:
            raise UserError(
                _(
                    "The DAS2 partner declaration threshold is not set on "
                    "company '%s'."
                )
                % company.display_name
            )
        self.partner_declare_threshold = company.fr_das2_partner_declare_threshold
        das2_partners = self.env["res.partner"].search(
            [("parent_id", "=", False), ("fr_das2_type", "!=", False)]
        )
        if not das2_partners:
            raise UserError(_("There are no partners configured for DAS2."))
        self.line_ids.unlink()
        base_domain = [
            ("company_id", "=", self.company_id.id),
            ("date", ">=", "%d-01-01" % self.year),
            ("date", "<=", "%d-12-31" % self.year),
            ("journal_id", "in", self.payment_journal_ids.ids),
            ("balance", "!=", 0),
            ("parent_state", "=", "posted"),
        ]
        for partner in das2_partners:
            vals = self._prepare_line(partner, base_domain)
            if vals:
                lfdlo.create(vals)
        self.generate_warning_msg(das2_partners)

    def _prepare_line(self, partner, base_domain):
        amlo = self.env["account.move.line"]
        mlines = amlo.search(
            base_domain
            + [
                ("partner_id", "=", partner.id),
                ("account_id", "=", partner.property_account_payable_id.id),
            ]
        )
        note = []
        amount = 0.0
        for mline in mlines:
            amount += mline.balance
            note.append(
                _("Payment dated %s in journal '%s': " "%.2f € (journal entry %s)")
                % (
                    mline.date,
                    mline.journal_id.display_name,
                    mline.balance,
                    mline.move_id.name,
                )
            )
        res = False
        amount_int = int(round(amount))
        if note and amount_int > 0:
            field_name = "%s_amount" % partner.fr_das2_type
            res = {
                field_name: amount_int,
                "parent_id": self.id,
                "partner_id": partner.id,
                "job": partner.fr_das2_job,
                "note": "\n".join(note),
            }
            if partner.siren and partner.nic:
                res["partner_siret"] = partner.siret
        return res

    def generate_warning_msg(self, das2_partners):
        amlo = self.env["account.move.line"]
        aao = self.env["account.account"]
        ajo = self.env["account.journal"]
        rpo = self.env["res.partner"]
        company = self.company_id
        purchase_journals = ajo.search(
            [("type", "=", "purchase"), ("company_id", "=", company.id)]
        )
        das2_accounts = aao.search(
            [
                ("company_id", "=", company.id),
                "|",
                "|",
                "|",
                "|",
                "|",
                ("code", "=like", "6221%"),
                ("code", "=like", "6222%"),
                ("code", "=like", "6226%"),
                ("code", "=like", "6228%"),
                ("code", "=like", "653%"),
                ("code", "=like", "6516%"),
            ]
        )
        rg_res = amlo.read_group(
            [
                ("company_id", "=", company.id),
                ("date", ">=", "%d-10-01" % (self.year - 1)),
                ("date", "<=", "%d-12-31" % self.year),
                ("journal_id", "in", purchase_journals.ids),
                ("partner_id", "!=", False),
                ("partner_id", "not in", das2_partners.ids),
                ("account_id", "in", das2_accounts.ids),
                ("balance", "!=", 0),
                ("parent_state", "=", "posted"),
            ],
            ["partner_id"],
            ["partner_id"],
        )
        msg = False
        msg_post = _("DAS2 lines generated. ")
        if rg_res:
            msg = _(
                "The following partners are not configured for DAS2 but "
                "they have expenses in some accounts that indicate "
                "they should probably be configured for DAS2:<ul>"
            )
            msg_post += msg
            for rg_re in rg_res:
                partner = rpo.browse(rg_re["partner_id"][0])
                msg_post += (
                    '<li><a href="#" data-oe-model="res.partner" '
                    'data-oe-id="%d">%s</a></li>' % (partner.id, partner.display_name)
                )
                msg += "<li>%s</li>" % partner.display_name
            msg_post += "</ul>"
            msg += "</ul>"
        self.message_post(body=msg_post)
        self.write({"warning_msg": msg})

    @api.model
    def _prepare_field(
        self, field_name, partner, value, size, required=False, numeric=False
    ):
        """This function is designed to be inherited."""
        if numeric:
            if not value:
                value = 0
            if not isinstance(value, int):
                try:
                    value = int(value)
                except Exception:
                    raise UserError(
                        _("Failed to convert field '%s' (partner %s) " "to integer.")
                        % (field_name, partner.display_name)
                    )
            value = str(value)
            if len(value) > size:
                raise UserError(
                    _(
                        "Field %s (partner %s) has value %s: "
                        "it is bigger than the maximum size "
                        "(%d characters)"
                    )
                    % (field_name, partner.display_name, value, size)
                )
            if len(value) < size:
                value = value.rjust(size, "0")
            return value
        if required and not value:
            raise UserError(
                _(
                    "The field '%s' (partner %s) is empty or 0. "
                    "It should have a non-null value."
                )
                % (field_name, partner.display_name)
            )
        if not value:
            value = " " * size
        # Cut if too long
        value = value[0:size]
        # enlarge if too small
        if len(value) < size:
            value = value.ljust(size, " ")
        return value

    def _prepare_address(self, partner):
        cstreet2 = self._prepare_field("Street2", partner, partner.street2, 32)
        cstreet = self._prepare_field("Street", partner, partner.street, 32)
        # specs section 5.4 : only bureau distributeur and code postal are
        # required. And they say it is tolerated to set city as
        # bureau distributeur
        # And we don't set the commune field because we put the same info
        # in bureau distributeur (section 5.4.1.3)
        # specs section 5.4 and 5.4.1.2.b: it is possible to set the field
        # "Adresse voie" without structuration on 32 chars => that's what we do
        if not partner.city:
            raise UserError(_("Missing city on partner '%s'.") % partner.display_name)
        if partner.country_id and partner.country_id.code not in FRANCE_CODES:
            if not partner.country_id.fr_cog:
                raise UserError(
                    _("Missing Code Officiel Géographique on country '%s'.")
                    % partner.country_id.display_name
                )
            cog = self._prepare_field(
                "COG", partner, partner.country_id.fr_cog, 5, True, numeric=True
            )
            raw_country_name = partner.with_context(lang="fr_FR").country_id.name
            country_name = self._prepare_field(
                "Nom du pays", partner, raw_country_name, 26, True
            )
            raw_commune = partner.city
            if partner.zip:
                raw_commune = "{} {}".format(partner.zip, partner.city)
            commune = self._prepare_field("Commune", partner, raw_commune, 26, True)
            caddress = (
                cstreet2
                + " "
                + cstreet
                + cog
                + " "
                + commune
                + cog
                + " "
                + country_name
            )
        # According to the specs, we should have some code specific for DOM-TOM
        # But it's not easy, because we are supposed to give the INSEE code
        # of the city, not of the territory => we don't handle that for the
        # moment
        else:
            ccity = self._prepare_field("City", partner, partner.city, 26, True)
            czip = self._prepare_field("Zip", partner, partner.zip, 5, True)
            caddress = (
                cstreet2 + " " + cstreet + "0" * 5 + " " + " " * 26 + czip + " " + ccity
            )
        assert len(caddress) == 129
        return caddress

    def _prepare_file(self):
        company = self.company_id
        cpartner = company.partner_id
        contact = self.contact_id
        csiren = self._prepare_field("SIREN", cpartner, cpartner.siren, 9, True)
        csiret = self._prepare_field("SIRET", cpartner, cpartner.siret, 14, True)
        cape = self._prepare_field("APE", cpartner, company.ape, 5, True)
        cname = self._prepare_field("Name", cpartner, company.name, 50, True)
        file_type = "X"  # tous déclarants honoraires seuls
        year = str(self.year)
        assert len(year) == 4
        caddress = self._prepare_address(cpartner)
        cprefix = csiret + "01" + year + self.dads_type
        # line 010 Company header
        flines = []
        flines.append(
            csiren
            + "0" * 12
            + "010"
            + " " * 14
            + cape
            + " " * 4
            + cname
            + caddress
            + " " * 8
            + file_type
            + csiret
            + " " * 5
            + caddress
            + " "
            + " " * 288
        )

        # ligne 020 Etablissement header
        # We don't add a field for profession on the company
        # because it's not even a field on the paper form!
        # We only set profession for suppliers
        flines.append(
            cprefix
            + "020"
            + " " * 14
            + cape
            + "0" * 14
            + " " * 41
            + cname
            + caddress
            + " " * 40
            + " " * 53
            + "N" * 6
            + " " * 296
        )

        i = 0
        for line in self.line_ids.filtered(lambda x: x.to_declare):
            i += 1
            partner = line.partner_id
            if (
                partner.country_id
                and partner.country_id.code in FRANCE_CODES
                and not line.partner_siret
            ):
                raise UserError(
                    _("Missing SIRET for french partner %s.") % partner.display_name
                )
            # ligne 210 honoraire
            if partner.is_company:
                partner_name = self._prepare_field(
                    "Partner name", partner, partner.name, 50, True
                )
                lastname = " " * 30
                firstname = " " * 20
            else:
                partner_name = " " * 50
                if hasattr(partner, "firstname") and partner.firstname:
                    lastname = self._prepare_field(
                        "Lastname", partner, partner.lastname, 30, True
                    )
                    firstname = self._prepare_field(
                        "Firstname", partner, partner.firstname, 20, True
                    )
                else:
                    lastname = self._prepare_field(
                        "Partner name", partner, partner.name, 30, True
                    )
                    firstname = " " * 20
            address = self._prepare_address(partner)
            partner_siret = self._prepare_field(
                "SIRET", partner, line.partner_siret, 14
            )
            job = self._prepare_field("Profession", partner, line.job, 30)
            amount_fields_list = [
                self._prepare_field(x, partner, line[x], 10, numeric=True)
                for x in AMOUNT_FIELDS
            ]
            if line.benefits_in_kind_amount:
                bik_letters = ""
                bik_letters += line.benefits_in_kind_food and "N" or " "
                bik_letters += line.benefits_in_kind_accomodation and "L" or " "
                bik_letters += line.benefits_in_kind_car and "V" or " "
                bik_letters += line.benefits_in_kind_other and "A" or " "
                bik_letters += line.benefits_in_kind_nict and "T" or " "
            else:
                bik_letters = " " * 5
            if line.allowance_amount:
                allow_letters = ""
                allow_letters += line.allowance_fixed and "F" or " "
                allow_letters += line.allowance_real and "R" or " "
                allow_letters += line.allowance_employer and "P" or " "
            else:
                allow_letters = " " * 3
            flines.append(
                cprefix
                + "210"
                + partner_siret
                + lastname
                + firstname
                + partner_name
                + job
                + address
                + "".join(amount_fields_list)
                + bik_letters
                + allow_letters
                + " " * 2
                + "0" * 10
                + " " * 245
            )
        rg = self.env["l10n.fr.das2.line"].read_group(
            [("parent_id", "=", self.id)], AMOUNT_FIELDS, []
        )[0]
        total_fields_list = [
            self._prepare_field(x, cpartner, rg[x], 12, numeric=True)
            for x in AMOUNT_FIELDS
        ]
        contact_name = self._prepare_field(
            "Administrative contact name", contact, contact.name, 50
        )
        contact_email = self._prepare_field(
            "Administrative contact email", contact, contact.email, 60
        )
        phone = contact.phone or contact.mobile
        phone = (
            phone.replace(" ", "")
            .replace(".", "")
            .replace("-", "")
            .replace("\u00A0", "")
        )
        if phone.startswith("+33"):
            phone = "0%s" % phone[3:]
        contact_phone = self._prepare_field(
            "Administrative contact phone", contact, phone, 10
        )
        flines.append(
            cprefix
            + "300"
            + " " * 36
            + "0" * 12 * 9
            + "".join(total_fields_list)
            + " " * 12
            + "0" * 12 * 2
            + "0" * 6
            + "0" * 12 * 5
            + " " * 74
            + contact_name
            + contact_phone
            + contact_email
            + " " * 76
        )

        lines_number = self._prepare_field(
            "Number of lines", cpartner, i, 6, numeric=True
        )
        flines.append(
            csiren
            + "9" * 12
            + "310"
            + "00001"
            + "0" * 6
            + lines_number
            + "0" * 6 * 3
            + " " * 18
            + "0" * 12 * 9
            + "".join(total_fields_list)
            + " " * 12
            + "0" * 12 * 2
            + "0" * 6
            + "0" * 12 * 5
            + " " * 253
        )
        for fline in flines:
            if len(fline) != 672:
                raise UserError(
                    _(
                        "One of the lines has a length of %d. "
                        "All lines should have a length of 672. Line: %s."
                    )
                    % (len(fline), fline)
                )
        file_content = "\r\n".join(flines) + "\r\n"
        return file_content

    def generate_file(self):
        self.ensure_one()
        company = self.company_id
        if not self.line_ids:
            raise UserError(_("The DAS2 has no lines."))
        if not company.siret:
            raise UserError(_("Missing SIRET on company '%s'.") % company.display_name)
        if not company.ape:
            raise UserError(_("Missing APE on company '%s'.") % company.display_name)
        if not company.street:
            raise UserError(_("Missing Street on company '%s'") % company.display_name)
        contact = self.contact_id
        if not contact:
            raise UserError(_("Missing administrative contact."))
        if not contact.email:
            raise UserError(
                _("The email is not set on the administrative contact " "partner '%s'.")
                % contact.display_name
            )
        if not contact.phone and not contact.mobile:
            raise UserError(
                _(
                    "The phone number is not set on the administrative contact "
                    "partner '%s'."
                )
                % contact.display_name
            )
        if self.attachment_id:
            raise UserError(
                _(
                    "An export file already exists. First, delete it via the "
                    "attachments and then re-generate it."
                )
            )

        file_content = self._prepare_file()
        try:
            file_content_encoded = file_content.encode("latin1")
        except UnicodeEncodeError:
            raise UserError(
                _(
                    "A special character in the DAS2 file is not in the latin1 "
                    "table. Please locate this special character and replace "
                    "it by a standard character and try again."
                )
            )
        filename = "DAS2_{}_{}.txt".format(self.year, company.name.replace(" ", "_"))
        attach = self.env["ir.attachment"].create(
            {
                "name": filename,
                "res_id": self.id,
                "res_model": self._name,
                "datas": base64.encodebytes(file_content_encoded),
            }
        )
        self.attachment_id = attach.id
        self.message_post(body=_("DAS2 file generated."))

    def button_lines_fullscreen(self):
        self.ensure_one()
        action = self.env.ref("l10n_fr_das2.l10n_fr_das2_line_action").sudo().read()[0]
        action.update(
            {
                "domain": [("parent_id", "=", self.id)],
                "views": False,
            }
        )
        return action


class L10nFrDas2Line(models.Model):
    _name = "l10n.fr.das2.line"
    _description = "DAS2 line"

    parent_id = fields.Many2one(
        "l10n.fr.das2", string="DAS2 Report", ondelete="cascade"
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Supplier",
        ondelete="restrict",
        domain=[("parent_id", "=", False)],
        states={"done": [("readonly", True)]},
        required=True,
    )
    partner_siret = fields.Char(
        string="SIRET", size=14, states={"done": [("readonly", True)]}
    )
    company_id = fields.Many2one(
        related="parent_id.company_id", store=True, readonly=True
    )
    currency_id = fields.Many2one(
        related="parent_id.company_id.currency_id",
        store=True,
        readonly=True,
        string="Company Currency",
    )
    fee_amount = fields.Integer(
        string="Honoraires et vacations", states={"done": [("readonly", True)]}
    )
    commission_amount = fields.Integer(
        string="Commissions", states={"done": [("readonly", True)]}
    )
    brokerage_amount = fields.Integer(
        string="Courtages", states={"done": [("readonly", True)]}
    )
    discount_amount = fields.Integer(
        string="Ristournes", states={"done": [("readonly", True)]}
    )
    attendance_fee_amount = fields.Integer(
        string="Jetons de présence", states={"done": [("readonly", True)]}
    )
    copyright_royalties_amount = fields.Integer(
        string="Droits d'auteur", states={"done": [("readonly", True)]}
    )
    licence_royalties_amount = fields.Integer(
        string="Droits d'inventeur", states={"done": [("readonly", True)]}
    )
    other_income_amount = fields.Integer(
        string="Autre rémunérations", states={"done": [("readonly", True)]}
    )
    allowance_amount = fields.Integer(
        string="Indemnités et remboursements", states={"done": [("readonly", True)]}
    )
    benefits_in_kind_amount = fields.Integer(
        string="Avantages en nature", states={"done": [("readonly", True)]}
    )
    withholding_tax_amount = fields.Integer(
        string="Retenue à la source", states={"done": [("readonly", True)]}
    )
    total_amount = fields.Integer(
        compute="_compute_total_amount",
        string="Total Amount",
        store=True,
        readonly=True,
    )
    to_declare = fields.Boolean(
        compute="_compute_total_amount", string="To Declare", readonly=True, store=True
    )
    allowance_fixed = fields.Boolean(
        "Allocation forfaitaire", states={"done": [("readonly", True)]}
    )
    allowance_real = fields.Boolean(
        "Sur frais réels", states={"done": [("readonly", True)]}
    )
    allowance_employer = fields.Boolean(
        "Prise en charge directe par l'employeur", states={"done": [("readonly", True)]}
    )
    benefits_in_kind_food = fields.Boolean(
        "Nourriture", states={"done": [("readonly", True)]}
    )
    benefits_in_kind_accomodation = fields.Boolean(
        "Logement", states={"done": [("readonly", True)]}
    )
    benefits_in_kind_car = fields.Boolean(
        "Voiture", states={"done": [("readonly", True)]}
    )
    benefits_in_kind_other = fields.Boolean(
        "Autres", states={"done": [("readonly", True)]}
    )
    benefits_in_kind_nict = fields.Boolean(
        "Outils issus des NTIC", states={"done": [("readonly", True)]}
    )
    state = fields.Selection(related="parent_id.state", store=True, readonly=True)
    note = fields.Text()
    job = fields.Char(
        string="Profession", size=30, states={"done": [("readonly", True)]}
    )

    _sql_constraints = [
        (
            "partner_parent_unique",
            "unique(partner_id, parent_id)",
            "Same partner used on several lines!",
        ),
        (
            "fee_amount_positive",
            "CHECK(fee_amount >= 0)",
            "Negative amounts not allowed!",
        ),
        (
            "commission_amount_positive",
            "CHECK(commission_amount >= 0)",
            "Negative amounts not allowed!",
        ),
        (
            "brokerage_amount_positive",
            "CHECK(brokerage_amount >= 0)",
            "Negative amounts not allowed!",
        ),
        (
            "discount_amount_positive",
            "CHECK(discount_amount >= 0)",
            "Negative amounts not allowed!",
        ),
        (
            "attendance_fee_amount_positive",
            "CHECK(attendance_fee_amount >= 0)",
            "Negative amounts not allowed!",
        ),
        (
            "copyright_royalties_amount_positive",
            "CHECK(copyright_royalties_amount >= 0)",
            "Negative amounts not allowed!",
        ),
        (
            "licence_royalties_amount_positive",
            "CHECK(licence_royalties_amount >= 0)",
            "Negative amounts not allowed!",
        ),
        (
            "other_income_amount_positive",
            "CHECK(other_income_amount >= 0)",
            "Negative amounts not allowed!",
        ),
        (
            "allowance_amount_positive",
            "CHECK(allowance_amount >= 0)",
            "Negative amounts not allowed!",
        ),
        (
            "benefits_in_kind_amount_positive",
            "CHECK(benefits_in_kind_amount >= 0)",
            "Negative amounts not allowed!",
        ),
        (
            "withholding_tax_amount_positive",
            "CHECK(withholding_tax_amount >= 0)",
            "Negative amounts not allowed!",
        ),
    ]

    @api.depends(
        "parent_id.partner_declare_threshold",
        "fee_amount",
        "commission_amount",
        "brokerage_amount",
        "discount_amount",
        "attendance_fee_amount",
        "copyright_royalties_amount",
        "licence_royalties_amount",
        "other_income_amount",
        "allowance_amount",
        "benefits_in_kind_amount",
        "withholding_tax_amount",
    )
    def _compute_total_amount(self):
        for line in self:
            total_amount = 0
            for field_name in AMOUNT_FIELDS:
                total_amount += line[field_name]
            to_declare = False
            if line.parent_id:
                if total_amount >= line.parent_id.partner_declare_threshold:
                    to_declare = True
            line.to_declare = to_declare
            line.total_amount = total_amount

    @api.constrains("partner_siret")
    def check_siret(self):
        for line in self:
            if line.partner_siret and not is_valid(line.partner_siret):
                raise ValidationError(_("SIRET '%s' is invalid.") % line.partner_siret)

    @api.onchange("partner_id")
    def partner_id_change(self):
        if self.partner_id:
            if self.partner_id.siren and self.partner_id.nic:
                self.partner_siret = self.partner_id.siret
            if self.partner_id.fr_das2_job:
                self.job = self.partner_id.fr_das2_job

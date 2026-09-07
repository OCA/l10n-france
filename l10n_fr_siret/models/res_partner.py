import logging

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError

logger = logging.getLogger(__name__)
try:
    from stdnum.fr import siren, siret
except ImportError:
    logger.debug("Cannot import stdnum")


class Partner(models.Model):
    _inherit = "res.partner"

    # This module doesn't depend on 'mail', so we can't add tracking=True
    # tracking=True is added in l10n_fr_siret_account
    siren = fields.Char(
        string="SIREN",
        size=9,
        help="The SIREN number is the official identity "
        "number of the company in France. It composes "
        "the first 9 digits of the SIRET number.",
    )
    nic = fields.Char(
        string="NIC",
        size=5,
        help="The NIC number is the official rank number "
        "of this office in the company in France. It "
        "composes the last 5 digits of the SIRET "
        "number.",
    )
    # the original SIRET field is definied in l10n_fr
    # We add an inverse method to make it easier to copy/paste a SIRET
    # from an external source to the partner form view of Odoo
    siret = fields.Char(
        compute="_compute_siret",
        inverse="_inverse_siret",
        store=True,
        precompute=True,
        readonly=False,
        help="The SIRET number is the official identity number of this "
        "company's office in France. It is composed of the 9 digits "
        "of the SIREN number and the 5 digits of the NIC number, ie. "
        "14 digits.",
    )
    parent_is_company = fields.Boolean(
        related="parent_id.is_company", string="Parent is a Company"
    )
    same_siren_partner_ids = fields.Many2many(
        "res.partner",
        compute="_compute_same_siren_partner_ids",
        string="Partners with same SIREN",
        compute_sudo=True,
    )
    # Field below is identical to the field on res.company defined in l10n_fr.
    # It is different from fiscal_country_codes defined in the 'account' module
    # which takes into account both the country of the company
    # AND the country of the partner
    is_france_country = fields.Boolean(
        compute="_compute_is_france_country",
    )

    @api.depends("siren", "nic")
    def _compute_siret(self):
        """Concatenate the SIREN and NIC to form the SIRET"""
        for rec in self:
            if rec.siren:
                if rec.nic:
                    rec.siret = rec.siren + rec.nic
                else:
                    rec.siret = rec.siren + "*****"
            else:
                rec.siret = False

    def _siret_check_active(self):
        """Return True if SIRET/SIREN checksum validation must run"""
        if tools.config["test_enable"]:
            return bool(self.env.context.get("_enable_siret_check"))
        return True

    def _inverse_siret(self):
        check_active = self._siret_check_active()
        for rec in self:
            if rec.siret:
                if siret.is_valid(rec.siret):
                    rec.write({"siren": rec.siret[:9], "nic": rec.siret[9:]})
                elif siren.is_valid(rec.siret[:9]) and rec.siret[9:] == "*****":
                    rec.write({"siren": rec.siret[:9], "nic": False})
                elif not check_active:
                    rec.write({"siren": rec.siret[:9], "nic": rec.siret[9:]})
                else:
                    raise ValidationError(_("SIRET '%s' is invalid.") % rec.siret)
            else:
                rec.write({"siren": False, "nic": False})

    @api.depends("siren", "company_id")
    def _compute_same_siren_partner_ids(self):
        # Inspired by same_vat_partner_id from 'base' module
        for partner in self:
            same_siren_partner_ids = False
            if partner.siren and not partner.parent_id:
                domain = [
                    ("siren", "=", partner.siren),
                    ("parent_id", "=", False),
                ]
                if partner.company_id:
                    domain += [
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", partner.company_id.id),
                    ]
                # use _origin to deal with onchange()
                partner_id = partner._origin.id
                if partner_id:
                    domain.append(("id", "!=", partner_id))
                same_siren_partner_ids = (
                    self.with_context(active_test=False).search(domain)
                ).ids or False
            partner.same_siren_partner_ids = same_siren_partner_ids

    @api.depends("country_id")
    def _compute_is_france_country(self):
        fr_country_codes = self.env["res.company"]._get_france_country_codes()
        for partner in self:
            is_france_country = False
            if partner.country_id and partner.country_id.code in fr_country_codes:
                is_france_country = True
            partner.is_france_country = is_france_country

    @api.constrains("siren", "nic", "vat")
    def _check_siret(self):
        """Check the SIREN's and NIC's keys (last digits)"""
        if not self._siret_check_active():
            return
        for rec in self:
            if rec.type == "contact" and rec.parent_id:
                continue
            if rec.nic:
                # Check the NIC type and length
                if not rec.nic.isdigit() or len(rec.nic) != 5:
                    raise ValidationError(
                        _(
                            "The NIC '{nic}' of partner '{partner_name}' is "
                            "incorrect: it must have exactly 5 digits."
                        ).format(nic=rec.nic, partner_name=rec.display_name)
                    )
            if rec.siren:
                # Check the SIREN type, length and key
                if not rec.siren.isdigit() or len(rec.siren) != 9:
                    raise ValidationError(
                        _(
                            "The SIREN '{siren}' of partner '{partner_name}' is "
                            "incorrect: it must have exactly 9 digits."
                        ).format(siren=rec.siren, partner_name=rec.display_name)
                    )
                if not siren.is_valid(rec.siren):
                    raise ValidationError(
                        _(
                            "The SIREN '{siren}' of partner '{partner_name}' is "
                            "invalid: the checksum is wrong."
                        ).format(siren=rec.siren, partner_name=rec.display_name)
                    )
                # Check the NIC key (you need both SIREN and NIC to check it)
                if rec.nic and not siret.is_valid(rec.siren + rec.nic):
                    raise ValidationError(
                        _(
                            "The SIRET '{siret}' of partner '{partner_name}' is "
                            "invalid: the checksum is wrong."
                        ).format(
                            siret=(rec.siren + rec.nic), partner_name=rec.display_name
                        )
                    )
                if rec.vat:
                    vat = "".join(x for x in rec.vat if not x.isspace())
                    # vat numbers have no spaces when base_vat is installed
                    # but installation of base_vat doesn't remove spaces in vat numbers
                    # encoded before the installation of the module
                    if vat and vat.startswith("FR") and not vat.endswith(rec.siren):
                        raise ValidationError(
                            _(
                                "On partner '%(partner_name)s', "
                                "the VAT number %(vat)s is not consistent with "
                                "SIREN %(siren)s: a french VAT number has the 9 "
                                "digits of SIREN at the end.",
                                partner_name=rec.display_name,
                                siren=rec.siren,
                                vat=vat,
                            )
                        )

    @api.model
    def _commercial_fields(self):
        # SIREN is the same for the whole company
        # NIC is different for each address
        res = super()._commercial_fields()
        res.append("siren")
        return res

    @api.model
    def _address_fields(self):
        res = super()._address_fields()
        res.append("nic")
        return res

    def action_open_business_doc(self):
        """Method called when you click on the link in the duplicate warning banner"""
        # WARNING: the exact same method is provided by the modules
        # partner_mobile_duplicate_warn and partner_email_duplicate_warn.
        # Let's hope that in future versions of Odoo this method will be present
        # in the "base" module and we'll remove that code!
        self.ensure_one()
        action = {
            "name": _("Partners"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_model": self._name,
            "res_id": self.id,
            "target": "current",
        }
        return action

    def _get_siren(self, raise_if_none=False):
        self.ensure_one()
        partner = self.parent_id or self
        running_env = tools.config.get("running_env")
        # Hack for SUPER PDP sandbox because, unfortunately,
        # SUPER PDP demo SIRENs don't have a compliant checksum
        if running_env in ("test", "dev") and partner.siren in (
            "000000001",
            "000000002",
        ):
            return partner.siren
        if partner.vat:
            vat = "".join(x for x in partner.vat if not x.isspace())
            if (
                vat
                and vat.startswith("FR")
                and len(vat) == 13
                and siren.is_valid(vat[4:])
            ):
                return vat[4:]
        if partner.siren and siren.is_valid(partner.siren):
            return partner.siren
        if raise_if_none:
            raise UserError(
                self.env._(
                    "SIREN is not set on partner '%(partner)s'.",
                    partner=partner.display_name,
                )
            )
        return None

    def _get_siret(self, raise_if_none=False):
        self.ensure_one()
        if self.siren and self.nic and siret.is_valid(self.siret):
            return self.siret
        if raise_if_none:
            raise UserError(
                self.env._(
                    "SIRET is not set on partner '%(partner)s'.",
                    partner=self.display_name,
                )
            )
        return None

    def _get_nic(self, raise_if_none=False):
        self.ensure_one()
        if self.siren and self.nic and siret.is_valid(self.siret):
            return self.nic
        if raise_if_none:
            raise UserError(
                self.env._(
                    "NIC is not set on partner '%(partner)s'.",
                    partner=self.display_name,
                )
            )
        return None

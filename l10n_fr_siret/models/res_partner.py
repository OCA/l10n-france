# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from stdnum.eu.vat import is_valid as vat_is_valid
from stdnum.fr.siren import is_valid as siren_is_valid
from stdnum.fr.siret import is_valid as siret_is_valid

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain


class Partner(models.Model):
    _inherit = "res.partner"

    same_siren_partner_ids = fields.Many2many(
        "res.partner",
        compute="_compute_same_siren_partner_ids",
        string="Partners with same SIREN",
    )
    # Space removal in SIRET is inspired by the implementation in base_vat
    # I don't know if it's the best way to do it though...
    company_registry = fields.Char(inverse="_inverse_fr_company_registry", store=True)

    def _inverse_fr_company_registry(self):
        fr_country_codes = self.env["res.company"]._get_france_country_codes()
        for partner in self:
            if (
                partner.country_id
                and partner.country_id.code in fr_country_codes
                and partner.company_registry
            ):
                company_registry = "".join(
                    x for x in partner.company_registry if not x.isspace()
                )
                if company_registry != partner.company_registry:
                    partner.company_registry = company_registry

    @api.depends("company_registry", "company_id", "country_id", "vat")
    def _compute_same_siren_partner_ids(self):
        # In the "base" module, the fields same_vat_partner_id and
        # same_company_registry_partner_id are implemented.
        # Here, we want to display the warning banner in scenarios
        # that are not fully covered by the "base" module.
        # User may have both the native banner and this banner... but it's
        # difficult to avoid that.
        fr_country_codes = self.env["res.company"]._get_france_country_codes()
        for partner in self:
            same_siren_partner_ids = []
            if not partner.parent_id:
                siren = partner._get_siren()
                if siren:
                    domain = Domain(
                        [
                            ("parent_id", "=", False),
                            ("id", "!=", partner._origin.id),
                        ]
                    )
                    if partner.company_id:
                        domain &= Domain(
                            "company_id", "in", (False, partner.company_id.id)
                        )

                    domain &= Domain("vat", "=like", f"FR%{siren}") | Domain(
                        [
                            ("country_id", "in", fr_country_codes),
                            ("company_registry", "=like", f"{siren}%"),
                        ]
                    )
                    same_siren_partner_ids = list(
                        self.with_context(active_test=False)._search(domain)
                    )
            partner.same_siren_partner_ids = [Command.set(same_siren_partner_ids)]

    @api.constrains("company_registry", "country_id", "parent_id", "vat")
    def _check_siret(self):
        """Check the SIREN's and NIC's keys (last digits)"""
        fr_country_codes = self.env["res.company"]._get_france_country_codes()
        for rec in self:
            if not rec.country_id or not rec.company_registry:
                continue
            if rec.country_id.code not in fr_country_codes:
                continue
            company_registry = "".join(
                x for x in rec.company_registry if not x.isspace()
            )
            if company_registry:
                if not company_registry.isdigit():
                    raise ValidationError(
                        self.env._(
                            "The SIRET (or SIREN) '%(company_registry)s' "
                            "of partner '%(partner_name)s' is "
                            "incorrect: it must contain only digits.",
                            company_registry=company_registry,
                            partner_name=rec.display_name,
                        )
                    )
                if len(company_registry) == 9:
                    if not siren_is_valid(company_registry):
                        raise ValidationError(
                            self.env._(
                                "The SIREN '%(company_registry)s' "
                                "of partner '%(partner_name)s' is "
                                "invalid: the checksum is wrong.",
                                company_registry=company_registry,
                                partner_name=rec.display_name,
                            )
                        )
                elif len(company_registry) == 14:
                    if not siret_is_valid(company_registry):
                        raise ValidationError(
                            self.env._(
                                "The SIRET '%(company_registry)s' "
                                "of partner '%(partner_name)s' is "
                                "invalid: the checksum is wrong.",
                                company_registry=company_registry,
                                partner_name=rec.display_name,
                            )
                        )
                else:
                    raise ValidationError(
                        self.env._(
                            "The SIRET (or SIREN) '%(company_registry)s' "
                            "of partner '%(partner_name)s' is "
                            "wrong: it should have 14 digits (or 9 digits for SIREN).",
                            company_registry=company_registry,
                            partner_name=rec.display_name,
                        )
                    )
                siren = company_registry[:9]
                assert siren_is_valid(siren)
                if rec.vat:
                    vat = "".join(x for x in rec.vat if not x.isspace())
                    # vat numbers have no spaces when base_vat is installed
                    # but installation of base_vat doesn't remove spaces in vat numbers
                    # encoded before the installation of the module
                    if vat.startswith("FR") and not vat.endswith(siren):
                        raise ValidationError(
                            self.env._(
                                "On partner '%(partner_name)s', "
                                "the VAT number %(vat)s is not consistent with "
                                "SIREN %(siren)s: a french VAT number has the 9 "
                                "digits of SIREN at the end.",
                                partner_name=rec.display_name,
                                siren=siren,
                                vat=vat,
                            )
                        )
                if rec.parent_id:
                    parent_siren = rec.parent_id._get_siren(raise_if_none=False)
                    if parent_siren and parent_siren != siren:
                        raise ValidationError(
                            self.env._(
                                "SIREN '%(child_siren)s' of child partner "
                                "'%(child_partner)s' is different from SIREN "
                                "'%(parent_siren)s' of its parent partner "
                                "'%(parent_partner)s'.",
                                child_siren=siren,
                                child_partner=rec.display_name,
                                parent_siren=parent_siren,
                                parent_partner=rec.parent_id.display_name,
                            )
                        )

    def _common_get_siren_siret(self, field, raise_if_none=False):
        if not self.country_id:
            if raise_if_none:
                raise UserError(
                    self.env._(
                        "Cannot get %(field)s of partner '%(partner)s' "
                        "because the country is not set on that partner.",
                        field=field,
                        partner=self.display_name,
                    )
                )
            return None
        fr_country_codes = self.env["res.company"]._get_france_country_codes()
        if self.country_id.code not in fr_country_codes:
            if raise_if_none:
                raise UserError(
                    self.env._(
                        "Cannot get %(field)s of partner '%(partner)s' "
                        "because the partner's country is %(country)s "
                        "which is not France.",
                        field=field,
                        partner=self.display_name,
                        country=self.country_id.name,
                    )
                )
            return None
        company_registry = self.company_registry and "".join(
            x for x in self.company_registry if not x.isspace()
        )
        if not company_registry:
            if raise_if_none:
                raise UserError(
                    self.env._(
                        "Cannot get %(field)s of partner '%(partner)s' "
                        "because the SIRET field is empty.",
                        field=field,
                        partner=self.display_name,
                    )
                )
            return None
        return company_registry

    def _get_siren(self, raise_if_none=False):
        partner = self.parent_id or self
        if partner.vat:
            vat = "".join(x for x in partner.vat if not x.isspace())
            if (
                vat
                and vat.startswith("FR")
                and len(vat) == 13
                and vat_is_valid(vat)
                and siren_is_valid(vat[4:])
            ):
                return vat[4:]
        company_registry = partner._common_get_siren_siret(
            "SIREN", raise_if_none=raise_if_none
        )
        if company_registry:
            if len(company_registry) == 14 and siret_is_valid(company_registry):
                return company_registry[:9]
            if len(company_registry) == 9 and siren_is_valid(company_registry):
                return company_registry
            if raise_if_none:
                raise UserError(
                    self.env._(
                        "Cannot get SIREN of partner '%(partner)s' because "
                        "the SIRET field is invalid (%(company_registry)s).",
                        partner=partner.display_name,
                        company_registry=company_registry,
                    )
                )
        return None

    def _get_siret(self, raise_if_none=False):
        # partner = self.parent_id or self
        company_registry = self._common_get_siren_siret(
            "SIRET", raise_if_none=raise_if_none
        )
        if company_registry and len(company_registry) == 14:
            return company_registry
        if raise_if_none:
            raise UserError(
                self.env._(
                    "Cannot get SIRET of partner '%(partner)s' because "
                    "the SIRET field is invalid (%(company_registry)s).",
                    partner=self.display_name,
                    company_registry=company_registry,
                )
            )
        return None

    def _get_nic(self, raise_if_none=False):
        company_registry = self._common_get_siren_siret(
            "SIRET", raise_if_none=raise_if_none
        )
        if company_registry and len(company_registry) == 14:
            return company_registry[9:]
        if raise_if_none:
            raise UserError(
                self.env._(
                    "Cannot get NIC of partner '%(partner)s' because "
                    "the SIRET field (%(company_registry)s) doesn't "
                    "contain a full SIRET.",
                    partner=self.display_name,
                    company_registry=company_registry,
                )
            )
        return None

    def action_open_business_doc(self):
        """Method called when you click on the link in the duplicate warning banner"""
        # WARNING: the exact same method is provided by the modules
        # partner_mobile_duplicate_warn and partner_email_duplicate_warn.
        # Let's hope that in future versions of Odoo this method will be present
        # in the "base" module and we'll remove that code!
        self.ensure_one()
        action = {
            "name": self.env._("Partners"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_model": self._name,
            "res_id": self.id,
            "target": "current",
        }
        return action

    def write(self, vals):
        # When moving a partner to a new parent partner, reset the company_registry
        # and let _fields_sync() do the job. This will avoid to be blocked by
        # the constraint to have the same SIREN on parent and child
        if vals.get("parent_id") and any(
            [vals["parent_id"] != p.parent_id.id for p in self]
        ):
            vals["company_registry"] = False
        return super().write(vals)

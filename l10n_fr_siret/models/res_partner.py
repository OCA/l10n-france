# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from stdnum.eu.vat import is_valid as vat_is_valid

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL


class Partner(models.Model):
    _inherit = "res.partner"

    same_siren_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        compute="_compute_same_siren_partner_ids",
        string="Partners with same SIREN",
    )
    # Those 2 fields are declared in l10n_fr_account
    l10n_fr_siren = fields.Char(
        string="SIREN",
        search="_search_l10n_fr_siren",
    )
    l10n_fr_siret = fields.Char(
        string="SIRET",
    )

    # -------------------------------------------------
    # Compute
    # -------------------------------------------------
    @api.depends("company_id", "country_id", "vat", "additional_identifiers")
    def _compute_same_siren_partner_ids(self):
        fr_country_codes = self.env["res.company"]._get_france_country_codes()
        for partner in self:
            same_siren_partner_ids = []
            if not partner.parent_id and (siren := partner._get_siren()):
                domain = Domain(
                    [
                        ("parent_id", "=", False),
                        ("additional_identifiers", "!=", False),
                        # exclude 'same_vat_partner_id' to avoid displaying
                        # both the native VAT warning and our SIREN warning banners
                        (
                            "id",
                            "not in",
                            [partner._origin.id, partner.same_vat_partner_id.id],
                        ),
                    ]
                )
                if partner.company_id:
                    domain &= Domain("company_id", "in", (False, partner.company_id.id))

                domain &= Domain("vat", "=like", f"FR%{siren}") | Domain(
                    [
                        ("country_id", "in", fr_country_codes),
                        ("l10n_fr_siren", "=", siren),
                    ]
                )
                same_siren_partner_ids = list(
                    self.with_context(active_test=False)._search(domain)
                )
            partner.same_siren_partner_ids = [Command.set(same_siren_partner_ids)]

    @api.model
    def _search_l10n_fr_siren(self, operator, value):
        if operator not in ("=", "ilike"):
            return NotImplemented
        sql_operator = "=" if operator == "=" else "LIKE"

        query = SQL(
            f"""
                SELECT id
                FROM res_partner
                WHERE additional_identifiers->>'FR_SIREN' {sql_operator} %s
            """,
            value,
        )
        return [("id", "in", query)]

    # -------------------------------------------------
    # Constrains
    # -------------------------------------------------
    @api.constrains("country_id", "parent_id", "vat", "additional_identifiers")
    def _check_siret(self):
        """
        Checks done in `base`: checksums of VAT, SIREN and SIRET
        Checks done here:
        - consistency between VAT and SIREN
        - same SIREN between parent & child
        """
        # Note: we do not run those checks in native '_validate_identifier()'
        # because we need more fields in @api.constrains()
        if self.env.context.get("skip_check_siret"):
            return
        fr_country_codes = self.env["res.company"]._get_france_country_codes()
        for partner in self:
            if (
                not partner.country_id
                or partner.country_code not in fr_country_codes
                or not (siren := partner._get_siren())
            ):
                continue

            # Consistency between SIREN and SIRET
            if (siret := partner._get_siret()) and siret[:9] != siren:
                raise ValidationError(
                    self.env._(
                        "On partner '%(partner_name)s', "
                        "the SIREN %(siren)s is not consistent with the "
                        "SIRET %(siret)s: the SIREN must corresponds to the "
                        "9 first digits of the SIRET.",
                        partner_name=partner.display_name,
                        siren=siren,
                        siret=siret,
                    )
                )

            # Consistency between VAT and SIREN
            if (
                partner.vat
                and partner.vat.startswith("FR")
                and siren != partner._l10n_fr_get_siren_from_vat()
            ):
                raise ValidationError(
                    self.env._(
                        "On partner '%(partner_name)s', "
                        "the VAT number %(vat)s is not consistent with "
                        "SIREN %(siren)s: a french VAT number has the 9 "
                        "digits of SIREN at the end.",
                        partner_name=partner.display_name,
                        siren=siren,
                        vat=partner.vat,
                    )
                )

            # Same SIREN between parent & child
            if (
                (parent_partner := partner.parent_id)
                and (parent_siren := parent_partner._get_siren())
                and parent_siren != siren
            ):
                raise ValidationError(
                    self.env._(
                        "SIREN '%(child_siren)s' of child partner "
                        "'%(child_partner)s' is different from SIREN "
                        "'%(parent_siren)s' of its parent partner "
                        "'%(parent_partner)s'.",
                        child_siren=siren,
                        child_partner=partner.display_name,
                        parent_siren=parent_siren,
                        parent_partner=parent_partner.display_name,
                    )
                )

    # -------------------------------------------------
    # ORM
    # -------------------------------------------------
    def write(self, vals):
        # When moving a partner to a new parent partner, we must silence the
        # contraint to let _fields_sync() do the job. It will synch the SIREN
        # between parent and child
        if vals.get("parent_id") and any(
            vals["parent_id"] != p.parent_id.id for p in self
        ):
            return super(Partner, self.with_context(skip_check_siret=True)).write(vals)
        return super().write(vals)

    # -------------------------------------------------
    # Wrappers
    # -------------------------------------------------
    def _common_get_siren_siret(self, field, raise_if_none=False):
        """Ensure the country is France before returning a SIREN or SIRET"""
        self.ensure_one()
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
        if value := self._get_additional_identifier(f"FR_{field}"):
            value = "".join(x for x in value if not x.isspace())
        return value

    def _get_siren(self, raise_if_none=False):
        # Note: SIREN is already synched between parent and child partner
        siren = (
            # From VAT first
            (vat := self.vat)
            and vat.startswith("FR")
            and len(vat) == 13
            and vat_is_valid(vat)
            and self._l10n_fr_get_siren_from_vat()
            # Or SIREN
            or self._common_get_siren_siret("SIREN", raise_if_none=raise_if_none)
        )
        if siren:
            return siren
        if raise_if_none:
            raise UserError(
                self.env._(
                    "Cannot get SIREN of partner '%(partner)s' because "
                    "the VAT and SIREN fields are empty.",
                    partner=self.display_name,
                )
            )
        return None

    def _get_siret(self, raise_if_none=False):
        # Since we disabled synch of SIRET between child & parent,
        # we look for it first in the child but then also in the parents
        partner, siret = self, None
        while not siret:
            siret = partner._common_get_siren_siret(
                "SIRET", raise_if_none=raise_if_none
            )
            if not (partner := partner.parent_id):
                break
        if siret:
            return siret
        if raise_if_none:
            raise UserError(
                self.env._(
                    "Cannot get SIRET of partner '%(partner)s' because "
                    "the SIRET field is empty.",
                    partner=self.display_name,
                )
            )
        return None

    def _get_nic(self, raise_if_none=False):
        if (siret := self._get_siret()) and len(siret) == 14:
            return siret[9:]
        if raise_if_none:
            raise UserError(
                self.env._(
                    "Cannot get NIC of partner '%(partner)s' because "
                    "the SIRET field is empty.",
                    partner=self.display_name,
                )
            )
        return None

    # -------------------------------------------------
    # Actions
    # -------------------------------------------------
    def action_open_business_doc(self):
        """Method called when you click on the link in the duplicate warning banner"""
        # WARNING: the exact same method is provided by the modules
        # partner_mobile_duplicate_warn and partner_email_duplicate_warn.
        return self._get_records_action(name=self.env._("Partners"))

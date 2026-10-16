import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

logger = logging.getLogger(__name__)
try:
    from stdnum.fr import siren, siret
except ImportError:
    logger.debug("Cannot import stdnum")


class Partner(models.Model):
    _inherit = "res.partner"

    siren = fields.Char(
        string="SIREN",
        size=9,
        tracking=50,
        help="The SIREN number is the official identity "
        "number of the company in France. It composes "
        "the first 9 digits of the SIRET number.",
    )
    nic = fields.Char(
        string="NIC",
        size=5,
        tracking=51,
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
    # company_registry is native since v16, cf
    # https://github.com/OCA/l10n-france/issues/501
    # Should we rename it... or stop using it ?
    # company_registry = fields.Char(
    #    help="The name of official registry where this company was declared.",
    # )

    parent_is_company = fields.Boolean(
        related="parent_id.is_company", string="Parent is a Company"
    )
    same_siren_partner_id = fields.Many2one(
        "res.partner",
        compute="_compute_same_siren_partner_id",
        string="Partner with same SIREN",
        compute_sudo=True,
    )

    @api.depends("siren", "nic")
    def _compute_siret(self):
        """Concatenate the SIREN and NIC to form the SIRET"""
        self.siret = ""
        for partner in self.filtered("siren"):
            partner.siret = partner.siren + (partner.nic or partner._nic_placeholder)

    def _inverse_siret(self):
        """Split the SIRET to find the SIREN and NIC"""
        self.write({"siren": "", "nic": ""})
        for partner in self.filtered("siret"):
            psiret = partner.siret
            if siret.is_valid(psiret):
                partner.write({"siren": psiret[:9], "nic": psiret[9:]})
            elif siren.is_valid(psiret[:9]) and psiret[9:] == partner._nic_placeholder:
                partner.write({"siren": psiret[:9], "nic": ""})

    @api.constrains("siret")
    def _check_siret(self):
        """Checks whether the SIRET is valid

        :raises ValidationError:
        """
        for partner in self._filter_eligible_for_identity_number_check("siret"):
            if not partner._is_siret_valid(partner.siret):
                raise ValidationError(_("SIRET '%s' is invalid.", partner.siret))

    @api.constrains("siren")
    def _check_siren(self):
        """Checks whether the SIREN is valid

        :raises ValidationError:
        """
        for partner in self._filter_eligible_for_identity_number_check("siren"):
            if not partner._is_siren_valid(partner.siren):
                raise ValidationError(
                    _(
                        "The SIREN '%(siren)s' of partner '%(partner_name)s' is"
                        " incorrect: it must have exactly 9 digits and pass the Luhn"
                        " checksum.",
                        siren=partner.siren,
                        partner_name=partner.display_name,
                    )
                )

    @api.constrains("nic")
    def _check_nic(self):
        """Checks whether the NIC is valid

        :raises ValidationError:
        """
        for partner in self._filter_eligible_for_identity_number_check("nic"):
            if not partner._is_nic_valid(partner.nic):
                raise ValidationError(
                    _(
                        "The NIC '%(nic)s' of partner '%(partner_name)s' is "
                        "incorrect: it must have exactly 5 digits.",
                        nic=partner.nic,
                        partner_name=partner.display_name,
                    )
                )

    def _filter_eligible_for_identity_number_check(self, fname: str):
        """Returns the subset of records with Identity Number ``fname`` to be checked

        :rtype: Partner
        """
        return self.filtered(lambda p: p._is_eligible_for_identity_number_check(fname))

    def _is_eligible_for_identity_number_check(self, fname: str):
        """Checks if the Identity Number ``fname`` should be checked on ``self``

        :rtype: bool
        """
        self.ensure_one()
        return self[fname] and not (self.type == "contact" and self.parent_id)

    @api.model
    def _is_siret_valid(self, siret_str: str):
        """Checks whether the SIRET is valid

        :rtype: bool
        """
        if siret.is_valid(siret_str):
            return True
        # If the SIRET is not valid in itself, split it into SIREN and NIC and check:
        # - that the SIREN is valid
        # - that the NIC is set as the placeholder value
        siren_str, nic_str = siret_str[:9], siret_str[9:]
        return self._is_siren_valid(siren_str) and self._is_nic_placeholder(nic_str)

    @api.model
    def _is_siren_valid(self, siren_str: str):
        """Checks whether the SIREN is valid

        :rtype: bool
        """
        # NB: ``siren.is_valid()`` already checks that the SIREN is a 9-chars string
        # containing all digits, so we don't need to do it here
        return siren.is_valid(siren_str)

    @api.model
    def _is_nic_valid(self, nic_str: str):
        """Checks whether the NIC is valid

        :rtype: bool
        """
        return len(nic_str) == 5 and nic_str.isdigit()

    @api.model
    def _is_nic_placeholder(self, nic_str: str):
        """Checks whether the NIC is the placeholder string

        :rtype: bool
        """
        return nic_str == self._nic_placeholder

    @property
    def _nic_placeholder(self):
        return "*****"

    @api.depends("siren", "company_id")
    def _compute_same_siren_partner_id(self):
        # Inspired by same_vat_partner_id from 'base' module
        for partner in self:
            same_siren_partner_id = False
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
                same_siren_partner_id = (
                    self.with_context(active_test=False).search(domain, limit=1)
                ).id or False
            partner.same_siren_partner_id = same_siren_partner_id

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

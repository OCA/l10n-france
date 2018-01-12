from odoo import models, fields


class ResCompany(models.Model):
    """Replace the company's fields for SIRET/RC with the partner's"""
    _inherit = 'res.company'

    # siret field is defined in l10n_fr module
    siret = fields.Char(
        string='SIRET', related='partner_id.siret', store=True)
    siren = fields.Char(
        string='SIREN', related='partner_id.siren', store=True)
    nic = fields.Char(
        string='NIC', related='partner_id.nic', store=True)
    # company_registry field is definied in base module
    company_registry = fields.Char(
        string='Company Registry', related='partner_id.company_registry',
        store=True)

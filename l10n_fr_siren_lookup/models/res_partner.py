# -*- coding: utf-8 -*-

# © 2018 Le Filament (<http://www.le-filament.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class PartnerSiren(models.Model):
	_inherit = 'res.partner'

	## Fields
	forme_juridique = fields.Char("Legal Type")
	siren = fields.Char("SIREN")
	siret = fields.Char("SIRET")
	ape = fields.Char("APE Code")
	lib_ape = fields.Char("APE Label")
	date_creation = fields.Date("Creation date")
	effectif = fields.Char("# Staff")
	lib_ess = fields.Char("ESS Label")
	date_ess = fields.Date("ESS Date")
	ess = fields.Boolean("ESS (Economie Sociale et Solidaire)")
	categorie = fields.Char("Category")

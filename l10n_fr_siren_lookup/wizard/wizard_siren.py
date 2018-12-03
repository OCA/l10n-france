# -*- coding: utf-8 -*-

# © 2018 Le Filament (<http://www.le-filament.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import urllib2
import requests

from odoo import api, fields, models

URL = "https://data.opendatasoft.com/api/records/1.0/search/?dataset=sirene%40public&q="
CHAMPS = "&rows=100"

class SirenWizard(models.TransientModel):
	_name = 'siren.wizard'
	_description = 'Get values from companies'


	## Default functions
	@api.model
	def _default_name(self):
		return self.env['res.partner'].browse(self.env.context.get('active_id')).name

	@api.model
	def _default_partner(self):
		return self.env.context.get('active_id')

	## Fields
	name = fields.Char(string='Company', default=_default_name)
	company_lines = fields.One2many('siren.wizard.company', 'wizard_id', string="Results",)
	partner_id = fields.Integer('Partner', default=_default_partner)


	## Action
	def get_company_lines(self):
		# Get request
		r = requests.get(URL + self.name + CHAMPS)
		# Serialization request to JSON
		companies = r.json()
		# Unlink all company lines
		self.company_lines.unlink()
		# Fill new company lines
		for company in companies['records']:
			new_company = self.company_lines.create({
					'wizard_id': self.id,
					'name': company['fields']['l1_normalisee'],
				})
			if company['fields'].get('l4_normalisee'):
				new_company.street = company['fields']['l4_normalisee']
			if company['fields'].get('codpos'):
				new_company.zip =  company['fields']['codpos']
			if company['fields'].get('libcom'):
				new_company.city = company['fields']['libcom']
			if company['fields'].get('siren'):
				new_company.siren = company['fields']['siren']
			if company['fields'].get('siret'):
				new_company.siret = company['fields']['siret']
			if company['fields'].get('categorie'):
				new_company.categorie = company['fields']['categorie']
			if company['fields'].get('dcret'):
				new_company.date_creation = company['fields']['dcret']
			if company['fields'].get('apen700'):
				new_company.ape = company['fields']['apen700']
			if company['fields'].get('libapet'):
				new_company.lib_ape = company['fields']['libapet']
			if company['fields'].get('dateess'):
				new_company.date_ess = company['fields']['dateess']
			if company['fields'].get('ess') == "O":
				new_company.ess = True
			if company['fields'].get('libessen'):
				new_company.lib_ess = company['fields']['libessen']
			if company['fields'].get('libnj'):
				new_company.forme_juridique = company['fields']['libnj']
			if company['fields']['efetcent'] in ["NN","0"]:
				new_company.effectif = 0
			else:
				new_company.effectif = int(company['fields']['efetcent'])
			
		return { "type": "ir.actions.do_nothing", }


class SirenWizardCompanies(models.TransientModel):
	_name = 'siren.wizard.company'
	_description = 'Companies Selection'

	## Fields
	wizard_id = fields.Many2one('siren.wizard', string='Wizard',)
	name = fields.Char(string='Name')
	street = fields.Char(string='Street')
	zip = fields.Char(string='CP')
	city = fields.Char(string='City')

	forme_juridique = fields.Char("Legal Type")
	siren = fields.Char("SIREN")
	siret = fields.Char("SIRET")
	ape = fields.Char("APE Code")
	lib_ape = fields.Char("APE Label")
	date_creation = fields.Date("Creation date")
	effectif = fields.Char("# Staff")
	lib_ess = fields.Char("ESS Label")
	date_ess = fields.Date("ESS Date")
	ess = fields.Boolean("ESS", default=False)
	categorie = fields.Char("Category")

	
	## Action
	@api.multi
	def update_partner(self):
		partner = self.env['res.partner'].browse(self.wizard_id.partner_id)
		partner.write({
			'name': self.name,
			'street': self.street,
			'zip': self.zip,
			'city': self.city,
			'forme_juridique': self.forme_juridique,
			'siren': self.siren,
			'siret': self.siret,
			'ape': self.ape,
			'lib_ape': self.lib_ape,
			'date_creation': self.date_creation,
			'effectif': self.effectif,
			'lib_ess': self.lib_ess,
			'date_ess': self.date_ess,
			'ess': self.ess,
			'categorie': self.categorie,
		})

		return True

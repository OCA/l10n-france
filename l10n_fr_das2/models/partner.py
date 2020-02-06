# -*- coding: utf-8 -*-
# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    fr_das2_type = fields.Selection([
        ('fee', u'Honoraires et vacations'),
        ('commission', u'Commissions'),
        ('brokerage', u'Courtages'),
        ('discount', u'Ristournes'),
        ('attendance_fee', u'Jetons de présence'),
        ('copyright_royalties', u"Droits d'auteur"),
        ('licence_royalties', u"Droits d'inventeur"),
        ('other_income', u'Autre rémunérations'),
        ('allowance', u'Indemnités et remboursements'),
        ], string='DAS2 Type', track_visibility='onchange')
    fr_das2_job = fields.Char(
        string='DAS2 Job', size=30,
        help="Used in the field 'Profession' of DAS2.")

# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return

    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        rpo = env['res.partner']
        cpso = env['chorus.partner.service']
        cr.execute(
            'SELECT id, fr_chorus_service_code FROM res_partner '
            'WHERE fr_chorus_service_code IS NOT null')
        res = cr.fetchall()
        for partner_sql in res:
            partner = rpo.browse(partner_sql[0])
            fr_chorus_service_code = partner_sql[1]
            service = cpso.search([
                ('partner_id', '=', partner.id),
                ('code', '=', fr_chorus_service_code)], limit=1)
            if not service:
                service = cpso.create({
                    'code': fr_chorus_service_code,
                    'partner_id': partner.commercial_partner_id.id,
                    'name': 'TO UPDATE (MIGRATION)',
                    })
            partner.fr_chorus_service_id = service.id

# -*- coding: utf-8 -*-
# Copyright (C) 2018 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo.api import Environment

import odoo.tests


class TestL10nFrCertificationPos(odoo.tests.HttpCase):

    def test_01_pos_basic_order(self):
        cr = self.registry.cursor()
        env = Environment(cr, self.uid, {})

        journal_obj = env['account.journal']
        account_obj = env['account.account']
        order_obj = env['pos.order']
        field_obj = env['ir.model.fields']
        property_obj = env['ir.property']
        french_country = env.ref('base.fr')
        main_company = env.ref('base.main_company')
        main_pos_config = env.ref('point_of_sale.pos_config_main')
        type_receivable = env.ref('account.data_account_type_receivable')

        field = field_obj.search([
            ('name', '=', 'property_account_receivable_id'),
            ('model', '=', 'res.partner'),
            ('relation', '=', 'account.account'),
        ], limit=1)

        # Create account receivable
        account_receivable = account_obj.create({
            'code': 'X1012',
            'name': 'Account Receivable - Test',
            'user_type_id': type_receivable.id,
            'reconcile': True,
         })

        # Create property
        property_obj.create({
            'name': 'property_account_receivable_id',
            'company_id': main_company.id,
            'fields_id': field.id,
            'value': 'account.account,' + str(account_receivable.id),
        })

        # set the company currency to USD, otherwise it will assume
        # euro's. this will cause issues as the sale journal is in
        # USD, because of this all products would have a different
        # price
        main_company.currency_id = env.ref('base.USD')

        test_sale_journal = journal_obj.create({
            'name': 'Sale Journal - Test',
            'code': 'TSJ',
            'type': 'sale',
            'company_id': main_company.id,
        })

        env['product.pricelist'].search([]).write(
            dict(currency_id=main_company.currency_id.id))

        main_pos_config.write({
            'journal_id': test_sale_journal.id,
            'invoice_journal_id': test_sale_journal.id,
            'journal_ids': [(0, 0, {
                'name': 'Cash Journal - Test',
                'code': 'TSC',
                'type': 'cash',
                'company_id': main_company.id,
                'journal_user': True,
            })],
        })

        # Change the country of the main company and configure Pos Config
        # to print hash, and to no print via proxy
        main_company.country_id = french_country.id
        main_pos_config.l10n_fr_prevent_print_legacy = 'hash_or_warning'
        main_pos_config.iface_print_via_proxy = False

        # open a session, the /pos/web controller will redirect to it
        main_pos_config.open_session_cb()

        # needed because tests are run before the module is marked as
        # installed. In js web will only load qweb coming from modules
        # that are returned by the backend in module_boot. Without
        # this you end up with js, css but no qweb.
        current_module = env['ir.module.module'].search(
            [('name', '=', 'l10n_fr_certification_pos_offline')], limit=1)
        current_module.state = 'installed'
        cr.release()

        before_order_qty = len(order_obj.search([]))

        web_tour_str = "odoo.__DEBUG__.services['web_tour.tour']"

        self.phantom_js(
            "/pos/web",
            web_tour_str + ".run('l10n_fr_certification_pos_offline')",
            web_tour_str + ".tours.l10n_fr_certification_pos_offline.ready",
            login="admin")

        after_order_qty = len(order_obj.search([]))

        self.assertEqual(
            before_order_qty + 1, after_order_qty,
            "Creation of French PoS Order failed")

        order = order_obj.search([], order='date_order desc', limit=1)
        self.assertNotEqual(
            order.l10n_fr_hash, False,
            "Certifified French PoS Order should have a hash defined")

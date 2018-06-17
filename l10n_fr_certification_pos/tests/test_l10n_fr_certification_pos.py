# -*- coding: utf-8 -*-
# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.tests.common import TransactionCase
from openerp.exceptions import ValidationError


class TestL10nFrCertificationPos(TransactionCase):

    def setUp(self):
        super(TestL10nFrCertificationPos, self).setUp()
        self.pos_config = self.env.ref('point_of_sale.pos_config_main')
        self.main_company = self.env.ref('base.main_company')

    def test_01_company_setting(self):
        """Setting a company to french should change generate a Sequence
        for the pos config"""
        # Set company country to France
        self.main_company.country_id = self.env.ref('base.fr')
        self.assertNotEqual(
            self.env.ref(
                'point_of_sale.pos_config_main').l10n_fr_secure_sequence_id,
            False,
            "Set France to a company should create Sequence fof Pos Configs")

    def test_02_company_setting_opened_session(self):
        """ Changing setting to a french company that has an open session
        should fail"""
        pos_session = self.env['pos.session'].create({
            'config_id': self.pos_config.id,
        })
        pos_session.open_cb()
        # Set company country to France should fail if pos session is open
        with self.assertRaises(ValidationError):
            self.main_company.country_id = self.env.ref('base.fr')

    def test_03_alteration(self):
        """Creating a PoS Order and altering in by DB, should mark the order
        as corrupted.
        """
        # Change current user company
        self.env.ref('base.user_root').company_id = self.env.ref(
            'l10n_fr_certification_abstract.french_company').id
        # Open a Session
        session_obj = self.env['pos.session']
        session = session_obj.create({
            'config_id': self.env.ref(
                'l10n_fr_certification_pos.french_pos_config').id,
        })
        session.open_cb()

        # Create Order
        order_obj = self.env['pos.order']
        order = order_obj.create({
            'session_id': session.id,
            'lines': [[0, False, {
                'price_unit': 1.50, 'qty': 1,
                'product_id': self.env.ref(
                    'point_of_sale.lays_pickles_250g').id,
            }]],
        })

        order._compute_l10n_fr_string_to_hash()
        order._compute_l10n_fr_secure_state()
        self.assertEqual(
            order.l10n_fr_secure_state, 'not_concerned',
            "Create a draft french PoS order should set it in a"
            " 'non concerned' inalterability state.")

        # Mark Payment
        payment_wizard_obj = self.env['pos.make.payment']
        payment_wizard = payment_wizard_obj.create({
            'journal_id': self.env.ref(
                'l10n_fr_certification_abstract'
                '.french_cash_account_journal').id,
            'amount': 1.5,
        })
        payment_wizard.with_context(active_id=order.id).check()

        # Check security process
        self.assertEqual(
            order.l10n_fr_secure_sequence_number, 1,
            "Confirm a french PoS order should increase sequence number")

        self.assertNotEqual(
            order.l10n_fr_hash, False,
            "Confirm a french PoS order should generate a hash")

        order._compute_l10n_fr_string_to_hash()
        order._compute_l10n_fr_secure_state()
        self.assertEqual(
            order.l10n_fr_secure_state, 'certified',
            "Confirm a french PoS order should set it in a 'certified'"
            " inalterability state.")

        # Alter pos order by sql
        order.date_order = '2000-01-01'
        order._compute_l10n_fr_string_to_hash()
        order._compute_l10n_fr_secure_state()
        self.assertEqual(
            order.l10n_fr_secure_state, 'corrupted',
            "Confirm a french PoS order should set it in a 'corrupted'"
            " inalterability state.")

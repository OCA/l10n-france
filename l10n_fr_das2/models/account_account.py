# -*- coding: utf-8 -*-
# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    fr_das2 = fields.Selection('get_das2_types', string='DAS2')

    @api.model
    def get_das2_types(self):
        res = [
            ('fee', u'Honoraires et vacations'),
            ('commission', u'Commissions'),
            ('brokerage', u'Courtages'),
            ('discount', u'Ristournes'),
            ('attendance_fee', u'Jetons de présence'),
            ('copyright_royalties', u"Droits d'auteur"),
            ('licence_royalties', u"Droits d'inventeur"),
            ('other_income', u'Autre rémunérations'),
            ('allowance', u'Indemnités et remboursements'),
            ('withholding_tax', u'Retenue à la source'),
            ]
        return res

    @api.constrains('fr_das2', 'user_type_id')
    def das2_check(self):
        exp_acc_type = self.env.ref('account.data_account_type_expenses')
        for account in self:
            if account.fr_das2 and account.user_type_id != exp_acc_type:
                raise ValidationError(_(
                    "The DAS2 option cannot be activated on account '%s' "
                    "because it is not an expense account.")
                    % account.display_name)


class AccountAccountTemplate(models.Model):
    _inherit = 'account.account.template'

    fr_das2 = fields.Selection('get_das2_types', string='DAS2')

    @api.model
    def get_das2_types(self):
        return self.env['account.account'].get_das2_types()

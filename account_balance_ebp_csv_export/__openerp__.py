# -*- encoding: utf-8 -*-
##############################################################################
#
#    Account Balance EBP CSV export module for OpenERP
#    Copyright (C) 2014 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Account Balance EBP CSV export',
    'version': '0.1',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'description': """
Account Balance EBP CSV export
==============================

This module adds a button *EBP csv File* next to the *Print* button on the Trial Balance wizard. It has been developped to be able to export the trial balance to software dedicated to the *Liasse fiscale* (French fiscal declaration) that accept csv files from the popular EBP accounting software. This file has been tested with Teledec (https://www.teledec.fr/), which is a SaaS solution for the *Liasse fiscale* with support for EDI transmission.

This module has been developped by Alexis de Lattre from Akretion <alexis.delattre@akretion.com>.
    """,
    'author': 'Akretion',
    'website': 'http://www.akretion.com',
    'depends': ['report_aeroo', 'account_financial_report_webkit'],
    'data': [
        'report/report.xml',
        'wizard/trial_balance_wizard_view.xml'
    ],
    'installable': True,
    'active': False,
}

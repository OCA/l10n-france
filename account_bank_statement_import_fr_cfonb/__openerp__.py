# -*- encoding: utf-8 -*-
##############################################################################
#
#    account_bank_statement_import_fr_cfonb module for Odoo
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
    'name': 'Import French CFONB Bank Statements',
    'version': '0.1',
    'license': 'AGPL-3',
    'author': 'Akretion',
    'website': 'http://www.akretion.com',
    'summary': 'Import French CFONB files as Bank Statements in Odoo',
    'description': """
Module to import French bank statements in CFONB format
=======================================================

This module allows you to import the text-based French
CFONB files in Odoo as bank statements. It depends on
the module *account_bank_statement_import* which is
currently available in the master branch of Odoo (future
v9), but you can backport it to v8 with this patch:
http://people.via.ecp.fr/~alexis/account_bank_statement_import-80-backport.diff
and a backport should be available soon in OCA.

This module has been developped by Alexis de Lattre
from Akretion <alexis.delattre@akretion.com>
    """,
    'depends': ['account_bank_statement_import'],
    'data': [],
    'installable': True,
}

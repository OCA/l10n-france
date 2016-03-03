# -*- coding: utf-8 -*-
##############################################################################
#
#    l10n_fr_mis_reports module for Odoo
#    Copyright (C) 2015-2016 Akretion (http://www.akretion.com)
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
    'name': 'MIS reports for France',
    'version': '8.0.0.0.1',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'MIS Report templates for the French P&L and Balance Sheets',
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'http://www.akretion.com',
    'depends': ['mis_builder', 'l10n_fr'],
    'data': [
        'data/mis_report_pl.xml',
        'data/mis_report_pl_simplified.xml',
        'data/mis_report_bs.xml',
        'data/mis_report_bs_simplified.xml',
        ],
    'installable': True,
}

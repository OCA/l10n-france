# -*- encoding: utf-8 -*-
##############################################################################
#
#    Intrastat report for the Netherlands (ICP)
#
#    Based on lp:new-report-intrastat, 
#    Copyright (C) 2010-2011 Akretion (http://www.akretion.com). All Rights Reserved
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    Modifications Copyright (C) 2012 Therp BV <http://therp.nl>
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
    'name': 'Intrastat reporting (ICP) for the Netherlands',
    'version': '1.0',
    'category': 'Localisation/Report Intrastat',
    'license': 'AGPL-3',
    'description': """
Opgaaf IntraCommunautaire Prestaties (ICP)

Based on Akretion's Intrastat framework, this module provides an
intrastat report for the Netherlands. Only generating the required data
for a manual declaration is supported. Message communication with the
tax authority has not yet been implemented.

The intrastat base module requires the country field required on
partner addresses. Selected countries are marked for inclusion in this report.

Amounts for products and services are reported separately. You can mark
products internally as 'Accessory costs'. Invoiced amounts for such 
products will be listed under the 'service amount'.

To exclude specific lines from the report, you can mark specific taxes
as such. If such a tax is applied to the line, the line will not be
included in the reported amounts
""",
    'author': 'Therp BV',
    'website': 'https://launchpad.net/new-report-intrastat',
    'depends': ['intrastat_base'],
    'data': [
        'view/l10n_nl_intrastat.xml',
    ],
}


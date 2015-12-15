# -*- coding: utf-8 -*-
##############################################################################
#
#    L10n_FR intrastat service module for Odoo
#    Copyright (C) 2015 Akretion (http://www.akretion.com)
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


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        "UPDATE l10n_fr_intrastat_service_declaration "
        "SET year=to_number(substring(year_month from 1 for 4), '9999') ")

    cr.execute(
        "UPDATE l10n_fr_intrastat_service_declaration "
        "SET month=to_number(substring(year_month from 6 for 2), '99') ")

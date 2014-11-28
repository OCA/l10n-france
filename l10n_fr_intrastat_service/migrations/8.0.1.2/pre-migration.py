# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat service module for OpenERP
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

def migrate(cr, version):
    if not version:
        return

    cr.execute(
        'ALTER SEQUENCE "report_intrastat_service_line_id_seq" RENAME TO '
        '"l10n_fr_report_intrastat_service_line_id_seq"')

    cr.execute(
        'ALTER TABLE "report_intrastat_service_line" RENAME TO '
        '"l10n_fr_report_intrastat_service_line"')

    cr.execute(
        "UPDATE ir_model SET model='l10n.fr.report.intrastat.service.line' "
        "WHERE model='report.intrastat.service.line'")

    cr.execute(
        "UPDATE ir_model_fields SET relation='l10n.fr.report.intrastat.service.line' "
        "WHERE relation='report.intrastat.service.line'")

    cr.execute(
        'ALTER SEQUENCE "report_intrastat_service_id_seq" RENAME TO '
        '"l10n_fr_report_intrastat_service_id_seq"')

    cr.execute(
        'ALTER TABLE "report_intrastat_service" RENAME TO '
        '"l10n_fr_report_intrastat_service"')

    cr.execute(
        "UPDATE ir_model SET model='l10n.fr.report.intrastat.service' "
        "WHERE model='report.intrastat.service'")

    cr.execute(
        "UPDATE ir_model_fields SET relation='l10n.fr.report.intrastat.service' "
        "WHERE relation='report.intrastat.service'")

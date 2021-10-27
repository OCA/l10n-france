# -*- coding: utf-8 -*-
# Copyright 2019 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.report_xlsx_helper.report.abstract_report_xlsx \
    import AbstractReportXlsx
from odoo.report import report_sxw
from odoo import _


class IntrastatServiceDeclarationXlsx(AbstractReportXlsx):

    def _get_ws_params(self, wb, data, declaration):
        template = {
            'partner_vat': {
                'header': {
                    'type': 'string',
                    'value': _('Partner VAT'),
                },
                'line': {
                    'value': self._render("line.partner_vat or ''"),
                },
                'width': 20,
            },
            'amount': {
                'header': {
                    'type': 'string',
                    'value': _('Amount'),
                },
                'line': {
                    'type': 'number',
                    'value': self._render("line.amount_company_currency"),
                    'format': self.format_tcell_amount_right,
                },
                'width': 16,
            },
            'partner': {
                'header': {
                    'type': 'string',
                    'value': _('Partner'),
                },
                'line': {
                    'value':
                    self._render("line.partner_id.display_name or ''"),
                },
                'width': 40,
            },
            'invoice': {
                'header': {
                    'type': 'string',
                    'value': _('Invoice'),
                },
                'line': {
                    'value': self._render("line.invoice_id.number or ''"),
                },
                'width': 20,
            },
        }

        title = 'DES %s-%s' % (
            declaration.year, str(declaration.month).zfill(2))
        ws_params = {
            'ws_name': title,
            'generate_ws_method': '_intrastat_service_report',
            'title': title,
            'wanted_list': ['partner_vat', 'amount', 'partner', 'invoice'],
            'col_specs': template,
        }
        return [ws_params]

    def _intrastat_service_report(self, workbook, ws, ws_params, data, decl):
        ws.set_portrait()
        ws.fit_to_pages(1, 0)
        ws.set_header(self.xls_headers['standard'])
        ws.set_footer(self.xls_footers['standard'])

        self._set_column_width(ws, ws_params)

        row_pos = 0
        row_pos = self._write_ws_title(ws, row_pos, ws_params)
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=self.format_theader_yellow_left)
        ws.freeze_panes(row_pos, 0)

        for line in decl.declaration_line_ids:
            row_pos = self._write_line(
                ws, row_pos, ws_params, col_specs_section='line',
                render_space={'line': line},
                default_format=self.format_tcell_left)


IntrastatServiceDeclarationXlsx(
    'report.l10n.fr.intrastat.service.declaration.xlsx',
    'l10n.fr.intrastat.service.declaration',
    parser=report_sxw.rml_parse)

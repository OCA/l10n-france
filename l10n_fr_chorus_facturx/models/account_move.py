# Copyright 2017-2020 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _cii_trade_contact_department_name(self, partner):
        if partner.fr_chorus_service_id:
            return partner.name
        return super()._cii_trade_contact_department_name(partner)

    @api.model
    def _cii_trade_agreement_buyer_ref(self, partner):
        if partner.fr_chorus_service_id:
            return partner.fr_chorus_service_id.code
        return super()._cii_trade_agreement_buyer_ref(partner)

    def chorus_get_invoice(self, chorus_invoice_format):
        self.ensure_one()
        if chorus_invoice_format == "xml_cii":
            chorus_file_content = self.with_context(
                fr_chorus_cii16b=True
            ).generate_facturx_xml()[0]
        elif chorus_invoice_format == "pdf_factur-x":
            report = self.env.ref("account.account_invoices")
            if report.report_type in ["qweb-html", "qweb-pdf"]:
                chorus_file_content, filetype = report._render_qweb_pdf([self.id])
            else:
                res = report.render([self.id])
                if not res:
                    raise UserError(
                        _("Unsupported report type %s found.") % report.report_type
                    )
                chorus_file_content, filetype = res
            assert filetype == "pdf", "wrong filetype"
        else:
            chorus_file_content = super().chorus_get_invoice(chorus_invoice_format)
        return chorus_file_content

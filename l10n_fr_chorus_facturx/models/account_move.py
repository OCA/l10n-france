# Copyright 2017-2020 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from lxml import etree

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _cii_add_buyer_order_reference(self, trade_agreement, ns):
        self.ensure_one()
        if self.transmit_method_code == "fr-chorus":
            buyer_order_ref = etree.SubElement(
                trade_agreement, ns["ram"] + "BuyerOrderReferencedDocument"
            )
            buyer_order_id = etree.SubElement(
                buyer_order_ref, ns["ram"] + "IssuerAssignedID"
            )
            buyer_order_id.text = self._get_commitment_number()
        else:
            return super()._cii_add_buyer_order_reference(trade_agreement, ns)

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
            chorus_file_content, filetype = report._render([self.id])
            assert filetype == "pdf", "wrong filetype"
        else:
            chorus_file_content = super().chorus_get_invoice(chorus_invoice_format)
        return chorus_file_content

    def _prepare_facturx_attachments(self):
        res = super()._prepare_facturx_attachments()
        for attach in self.chorus_attachment_ids:
            res[attach.name] = {
                "filedata": attach.raw,
                "modification_datetime": attach.write_date,
                "creation_datetime": attach.create_date,
            }
        return res

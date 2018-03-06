# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models
import tarfile
import time
from io import BytesIO


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def generate_ubl_xml_string(self, version='2.1'):
        self.ensure_one()
        if self.transmit_method_code == 'fr-chorus':
            self = self.with_context(fr_chorus=True)
        return super(AccountInvoice, self).generate_ubl_xml_string(
            version=version)

    def _ubl_get_contract_document_reference_dict(self):
        self.ensure_one()
        cdr_dict = super(AccountInvoice, self).\
            _ubl_get_contract_document_reference_dict()
        if self.agreement_id:
            cdr_dict[u'Marché public'] = self.agreement_id.code
        return cdr_dict

    def prepare_chorus_deposer_flux_payload(self):
        # move more logic into the l10n_fr_chorus_account module ?
        # I'll wait for the Factur-X API to be published
        if self[0].company_id.fr_chorus_invoice_format == 'xml_ubl':
            syntaxe_flux = self.env['chorus.flow'].syntax_odoo2chorus()[
                'xml_ubl']
            if len(self) == 1:
                chorus_file_content = self.generate_ubl_xml_string()
                # Seems they don't want '/' in filenames
                filename =\
                    'UBL_chorus_facture_%s.xml' % self.number.replace('/', '-')
            else:
                # Generate tarball
                filename = 'UBL_chorus_lot_factures.tar.gz'
                tarfileobj = BytesIO()
                with tarfile.open(fileobj=tarfileobj, mode='w:gz') as tar:
                    for inv in self:
                        xml_string = inv.generate_ubl_xml_string()
                        xmlfileio = BytesIO(xml_string)
                        xmlfilename =\
                            'UBL_chorus_facture_%s.xml' % inv.number.replace(
                                '/', '-')
                        tarinfo = tarfile.TarInfo(name=xmlfilename)
                        tarinfo.size = len(xml_string)
                        tarinfo.mtime = int(time.time())
                        tar.addfile(tarinfo=tarinfo, fileobj=xmlfileio)
                    tar.close()
                tarfileobj.seek(0)
                chorus_file_content = tarfileobj.read()

            payload = {
                'fichierFlux': chorus_file_content.encode('base64'),
                'nomFichier': filename,
                'syntaxeFlux': syntaxe_flux,
                'avecSignature': False,
                }
            return payload
        return super(
            AccountInvoice, self).prepare_chorus_deposer_flux_payload()

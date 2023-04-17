# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import json
import logging
from datetime import datetime

import pytz
import requests

from odoo import _, fields, models, tools
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools.misc import format_datetime

logger = logging.getLogger(__name__)

TELEDEC_DATE_FORMAT = "%Y-%m-%d"
TIMEOUT = 20


class L10nFrAccountVatReturn(models.Model):
    _inherit = "l10n.fr.account.vat.return"

    teledec_sent_datetime = fields.Datetime(
        string="Teledec.fr Dispatch Date", readonly=True
    )

    def _prepare_json_teledec_headers(self, teledec_dict, title_id2code):
        self.ensure_one()
        company = self.company_id
        partner = company.partner_id
        legal_rep = company.fr_vat_teledec_legal_representative_id
        # They want datetime in Paris timezone
        utc_datetime_aware = pytz.utc.localize(datetime.utcnow())
        paris_tz = pytz.timezone("Europe/Paris")
        paris_datetime_aware = utc_datetime_aware.astimezone(paris_tz)
        timestamp = paris_datetime_aware.strftime("%Y-%m-%dT%H:%M:%S")
        action = self.env.ref("account.action_account_config")
        goto_msg = _("Go to configuration page")
        if not company.fr_vat_teledec_email:
            raise RedirectWarning(
                _("E-mail for Teledec.fr is not set on company '%s'.")
                % company.display_name,
                action.id,
                goto_msg,
            )
        if not company.fr_vat_teledec_legal_form:
            raise RedirectWarning(
                _("Company Legal Form is not set on company '%s'.")
                % company.display_name,
                action.id,
                goto_msg,
            )
        if not legal_rep:
            raise RedirectWarning(
                _("Legal Representative is not set on company '%s'.")
                % company.display_name,
                action.id,
                goto_msg,
            )
        if not legal_rep.email:
            raise UserError(
                _("E-mail missing on partner '%s'.") % legal_rep.display_name
            )
        if not legal_rep.title:
            raise UserError(
                _("Title (Mister or Madam) missing on partner '%s'.")
                % legal_rep.display_name
            )

        if legal_rep.title.id not in title_id2code:
            raise UserError(
                _("The title of partner '%s' must be Mister or Madam.")
                % legal_rep.display_name
            )
        if not legal_rep.function:
            raise UserError(
                _("Job position missing on partner '%s'.") % legal_rep.display_name
            )
        if not company.siret:
            raise UserError(_("SIRET not set on company '%s'.") % company.display_name)
        if not self.bank_account_id:
            raise UserError(
                _("The company bank account is not set on VAT return %s.")
                % self.display_name
            )
        if self.bank_account_id.acc_type != "iban":
            raise UserError(
                _("The company bank account %s is not an IBAN.")
                % self.bank_account_id.display_name
            )
        if not self.bank_account_id.bank_bic:
            raise UserError(
                _("BIC is missing on the company bank account %s.")
                % self.bank_account_id.display_name
            )
        if (
            not partner.city
            or not partner.zip
            or not partner.street
            or not partner.country_id
        ):
            raise UserError(
                _(
                    "The address of partner '%s' is incomplete: "
                    "it must have at least the street, zip, city and country."
                )
                % partner.display_name
            )
        # phone is not a required field
        phone = legal_rep.phone
        if not phone:
            phone = legal_rep.mobile
        if not phone:
            phone = partner.phone
        if not phone:
            phone = partner.mobile
        teledec_dict.update(
            {
                "auth": {
                    "email": company.fr_vat_teledec_email,  # teledec account ID
                    "timestamp": timestamp,
                    "partenaire": tools.config.get(
                        "teledec_invoicing_partner", "AKRETION"
                    ),
                },
                "identity": {
                    "siret": company.siret,  # we can write SIREN or SIRET here
                    "name": company.name,
                    "fullRegimeFiscal": "ISRN",  # ISRN or ISRS
                    "regimeFiscalTVA": "RN",  # in which case is RS ? CA12 ?
                    # yearEndxxx fields are ignored for VAT but required by Teledec
                    # so we always write 31/12 even if the FY doesn't end on 31/12
                    "yearEndMonth": 12,
                    "yearEndDay": 31,
                    "addressStreet": partner.street,
                    "addressComplement": partner.street2,
                    # "addressNeighborhood": "",
                    "addressPostalCode": partner.zip,
                    "addressCity": partner.city,
                    "addressCountry": partner.country_id.code,
                    "legalForm": company.fr_vat_teledec_legal_form,
                    "legalRepresentative": legal_rep.name,
                    "legalRepresentativeAs": legal_rep.function,
                    # 2 possible values: M or MME
                    "legalRepresentativeTitle": title_id2code[legal_rep.title.id],
                    "telephone": phone,
                    "email": legal_rep.email,
                    "BIC": self.bank_account_id.bank_bic,
                    "IBAN": self.bank_account_id.acc_number,
                },
            }
        )

    def _prepare_json_teledec_period(self, teledec_dict):
        company = self.company_id
        if not company.vat:
            raise UserError(
                _("VAT number not set on company '%s'.") % company.display_name
            )
        teledec_dict["period"] = {
            "begin": self.start_date.strftime(TELEDEC_DATE_FORMAT),
            "end": self.end_date.strftime(TELEDEC_DATE_FORMAT),
            "millesime": self.end_date.year,
            # suspension: write CSS for "cession d'activité"
            "suspension": False,
            "reference": "%s_%s" % (company.vat, self.name),  # optional field
        }

    def _prepare_json_teledec(self):
        self.ensure_one()
        title_id2code = {
            self.env.ref("base.res_partner_title_madam").id: "MME",
            self.env.ref("base.res_partner_title_mister").id: "M",
        }
        teledec_dict = {
            "3310CA3": {},
            "3310A": {},
        }
        self._prepare_json_teledec_headers(teledec_dict, title_id2code)
        self._prepare_json_teledec_period(teledec_dict)
        lines = self.line_ids.filtered(lambda x: not x.box_display_type)
        if not lines:
            raise UserError(
                _("There are no lines on VAT return %s.") % self.display_name
            )
        vat_reimbursement_box_id = (
            self.env["l10n.fr.account.vat.box"]
            ._box_from_single_box_type("vat_reimbursement")
            .id
        )
        credit_vat_reimbursement_amount = 0
        for line in lines:
            if line.box_edi_type in ("MOA", "QTY", "PCD"):
                teledec_dict[line.box_form_code][line.box_id.edi_code] = line.value
            elif line.box_edi_type == "CCI_TBX":
                teledec_dict[line.box_form_code][line.box_id.edi_code] = line.value_bool
            elif line.box_edi_type in ("FTX", "NAD"):
                teledec_dict[line.box_form_code][line.box_id.edi_code] = line.value_char
            else:
                raise UserError(
                    _(
                        "Cannot teletransmit box '%(box)s': box types "
                        "'%(box_edi_type)s' are not supported for the moment.",
                        box=line.box_id.display_name,
                        box_edi_type=line.box_edi_type,
                    )
                )
            if line.box_id.id == vat_reimbursement_box_id:
                credit_vat_reimbursement_amount = line.value
        if self.comment_dgfip:  # 5 lines of 512 chars max
            teledec_dict["3310CA3"]["BC"] = True  # mention expresse
            self._prepare_comment(self.comment_dgfip, "BA", teledec_dict["3310CA3"])
        if credit_vat_reimbursement_amount > 0:
            dict_3519 = self._prepare_3519(
                credit_vat_reimbursement_amount, title_id2code
            )
            teledec_dict["3519"] = dict_3519

        logger.debug("teledec_dict=%s", teledec_dict)
        return teledec_dict

    def _prepare_comment(self, comment, edi_code, formdict):
        # For comments 5 x 512
        assert comment
        start_char = 0
        i = 1
        while i <= 5:
            end_char = start_char + 512
            value_char = comment[start_char:end_char]
            if value_char:
                formdict["%s_4440_%d" % (edi_code, i)] = value_char
            else:
                break
            i += 1
            start_char += 512

    def _prepare_3519(self, amount, title_id2code):
        assert self.reimbursement_type in ("first", "end", "other")
        assert isinstance(amount, int)
        assert self.bank_account_id
        assert self.bank_account_id.acc_type == "iban"
        assert self.bank_account_id.bank_bic

        company = self.company_id
        legal_rep = company.fr_vat_teledec_legal_representative_id
        dict_3519 = {
            "AA_3192_1": self.company_id.name,
            "DD": True,  # Entreprise FR
            "DG_3164_1": company.city,
            "DG_3036_1": legal_rep.name,  # nom prénom
            "DG_3036_2": legal_rep.function,  # qualité
            "DG_3036_3": title_id2code[legal_rep.title.id],  # titre
            "DN": amount,
            "FK": True,  # à créditer au compte désigné
            "AA_3433_1": self.bank_account_id.bank_bic,
            "AA_3194_1": self.bank_account_id.acc_number,
        }
        if self.reimbursement_type == "first":
            dict_3519["DI"] = True  # Première demande
            dict_3519["DL"] = self.reimbursement_first_creation_date.strftime(
                TELEDEC_DATE_FORMAT
            )
        elif self.reimbursement_type == "end":
            dict_3519["DJ"] = True  # Cession, cessation, décès
            dict_3519["DM"] = self.reimbursement_end_date.strftime(TELEDEC_DATE_FORMAT)
        elif self.reimbursement_type == "other":
            dict_3519["DK"] = True  # Autres
        if self.reimbursement_comment_dgfip:
            self._prepare_comment(self.reimbursement_comment_dgfip, "FJ", dict_3519)
        return dict_3519

    def send_ca3_via_teledec(self):
        self.ensure_one()
        if self.teledec_sent_datetime:
            raise UserError(
                _(
                    "The VAT declaration '%(vat_return)s' has already been sent "
                    "on %(datetime)s.",
                    vat_return=self.display_name,
                    datetime=format_datetime(self.env, self.teledec_sent_datetime),
                )
            )
        assert self.state == "auto"
        if self.vat_periodicity == "12":
            raise UserError(
                _(
                    "Teletransmission via Teledec.fr is not yet supported for CA12 "
                    "(yearly VAT returns). At the moment, it only works for CA3 "
                    "(monthly or quarterly)."
                )
            )
        test_mode = self.company_id.fr_vat_teledec_test_mode
        prefix = test_mode and "http://stage" or "https://www"
        url = "%s.teledec.fr/service/declaration-marque-blanche" % prefix
        teledec_dict = self._prepare_json_teledec()
        teledec_str = json.dumps(teledec_dict)
        priv_key = tools.config.get("teledec_private_key")
        if not priv_key:
            raise UserError(
                _(
                    "Missing 'teledec_private_key' in the Odoo server configuration "
                    "file."
                )
            )
        hash_obj = hmac.new(
            priv_key.encode("utf-8"),
            msg=teledec_str.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        params = {"hash": hash_obj.hexdigest()}
        headers = {"Content-type": "application/json", "Accept": "application/json"}
        try:
            logger.info("Sending HTTP POST on %s with params=%s", url, params)
            res = requests.post(
                url, params=params, headers=headers, data=teledec_str, timeout=TIMEOUT
            )
        except Exception as e:
            raise UserError(
                _("Failed to send the request to Teledec.fr. Technical error: %s.") % e
            ) from e
        logger.debug("Teledec answer HTTP code %s texte %s", res.status_code, res.text)
        if res.status_code == 200:
            try:
                res_json = res.json()  # crashes here
            except Exception:
                raise UserError(
                    _(
                        "The query to the Teledec.fr webservice was successful, "
                        "but the answer of the webservice was not in the "
                        "expected format. You should contact Teledec.fr and "
                        "request them to setup your account with a "
                        "JSON answer."
                    )
                ) from None
            # to reproduice the crash, just change the login
            if res_json.get("status") != "ok":
                raise UserError(
                    _(
                        "The request sent to Teledec.fr got an answer '%(answer)s' "
                        "(it should have received 'ok'). Error message: '%(error)s'.",
                        answer=res_json.get("status"),
                        error=res_json.get("message", _("None")),
                    )
                ) from None
            self.write({"teledec_sent_datetime": fields.Datetime.now()})
            self.message_post(
                body=_(
                    "VAT return successfully sent to "
                    '<a href="https://teledec.fr/">Teledec.fr</a>.'
                )
            )
            self.auto2sent()
        else:
            raise UserError(
                _("The request sent to Teledec.fr got an HTTP error code %s.")
                % res.status_code
            )

# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import uuid

from odoo import _, fields, models
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class L10nFrAccountVatReturn(models.Model):
    _inherit = "l10n.fr.account.vat.return"

    selenium_attachment_id = fields.Many2one("ir.attachment")
    selenium_attachment_datas = fields.Binary(
        related="selenium_attachment_id.datas", string="Selenium File"
    )
    selenium_attachment_name = fields.Char(
        related="selenium_attachment_id.name", string="Selenium Filename"
    )

    def _delete_move_and_attachments(self):
        super()._delete_move_and_attachments()
        if self.selenium_attachment_id:
            self.selenium_attachment_id.unlink()

    def generate_selenium_file(self):
        self.ensure_one()
        name = "CA3-%s" % self.display_name
        if self.vat_periodicity != "1":
            raise UserError(
                _("Selenium export only support monthly CA3 returns for the moment.")
            )
        if self.line_ids.filtered(
            lambda x: x.box_form_code == "3310A" and not x.box_display_type
        ):
            raise UserError(_("Selenium cannot work when there are 3310-A lines."))
        month2label = {  # I don't want to fight with locales
            1: "Janvier",
            2: "Février",
            3: "Mars",
            4: "Avril",
            5: "Mai",
            6: "Juin",
            7: "Juillet",
            8: "Août",
            9: "Septembre",
            10: "Octobre",
            11: "Novembre",
            12: "Décembre",
        }
        period_name = "%s %s" % (
            month2label[self.start_date.month],
            self.start_date.year,
        )
        if not self.company_id.siret:
            raise UserError(
                _("Missing SIRET on company '%s'.") % self.company_id.display_name
            )
        # TODO: move Selenium file generation to a python lib ?
        siren = self.company_id.siret[:9]
        siren_with_spaces = " ".join([siren[:3], siren[3:6], siren[6:9]])
        test_uuid = str(uuid.uuid4())
        side_dict = {
            "id": str(uuid.uuid4()),
            "version": "2.0",
            "name": name,
            "url": "https://www.impots.gouv.fr",
            "tests": [
                {
                    "id": test_uuid,
                    "name": name,
                    "commands": [
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Slower speed to see pages",
                            "command": "setSpeed",
                            "target": "1000",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Open impots.gouv.fr/portail",
                            "command": "open",
                            "target": "/portail/",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Click on Votre espace professionnel",
                            "command": "click",
                            "target": "css=.identificationpro > span",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Click on TVA",
                            "command": "click",
                            "target": "linkText=TVA",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Check SIREN %s" % siren,
                            "command": "assertText",
                            "target": "xpath=//table[@class='selection']//tr[2]/td[2]/strong",
                            # xpath //table[@class='selection']/tr[2]/td[2]/strong doesn't work
                            # although it is what you have in the HTML of the page
                            # because the browser (?) auto-adds <tbody> between table and tr
                            "value": siren,
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Click on Déclarer",
                            "command": "click",
                            "target": "name=button.submitValider",
                            "opensWindow": True,
                            "windowHandleName": "new_vat_tab",
                            "windowTimeout": 2000,
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Identify new tab",
                            "command": "storeWindowHandle",
                            "target": "root",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Switch to new tab",
                            "command": "selectWindow",
                            "target": "handle=${new_vat_tab}",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Click on %s" % period_name,
                            "command": "click",
                            "target": "linkText=%s" % period_name,
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Higher speed for VAT form",
                            "command": "setSpeed",
                            "target": "0",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Check SIREN %s" % siren,
                            "command": "assertText",
                            "target": "xpath=//div[contains(.,'SIREN')]/span",
                            "value": siren_with_spaces,
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Check period %s" % period_name,
                            "command": "assertText",
                            "target": "xpath=//div[contains(.,'imposition')]/following::div",
                            "value": period_name,
                        },
                    ],
                }
            ],
            "suites": [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Default Suite",
                    "persistSession": False,
                    "parallel": False,
                    "timeout": 300,
                    "tests": [test_uuid],
                }
            ],
            "urls": ["https://www.impots.gouv.fr/"],
            "plugins": [],
        }

        push_box_ids = {}
        for pbox in self.env["l10n.fr.account.vat.box"].search(
            [("push_box_id", "!=", False)]
        ):
            push_box_ids[pbox.push_box_id.id] = True

        for line in self.line_ids:
            box = line.box_id
            if (
                not line.box_display_type
                and box.box_type != "due_vat"
                and box.id not in push_box_ids
            ):
                if not box.nref_code:
                    raise UserError(_("Missing NREF code on box '%s'." % box.name))
                # if box.edi_type != 'MOA':
                nref_code = box.nref_code
                value = line.value
                if box.edi_type == "MOA":
                    click_dict = {
                        "id": str(uuid.uuid4()),
                        "comment": "Select %s" % box.display_name,
                        "command": "click",
                        "target": "id=A%s_0" % nref_code,
                        "value": "",
                    }
                    side_dict["tests"][0]["commands"].append(click_dict)
                    type_dict = {
                        "id": str(uuid.uuid4()),
                        "comment": "Write %d in %s" % (value, box.display_name),
                        "command": "type",
                        "target": "id=A%s_0" % nref_code,
                        "value": "%d" % value,
                    }
                    side_dict["tests"][0]["commands"].append(type_dict)
                # elif box.edi_type == 'CCI_TBX' and value:
                #    click_dict = {
                #        "id": str(uuid.uuid4()),
                #        "comment": "Check box %s" % box.display_name,
                #        "command": "click",
                #        "target": "xpath=//input[@id='A%s_0']" % nref_code,
                #        "value": "",
                #        }
                #    side_dict['tests'][0]['commands'].append(click_dict)
                else:
                    raise UserError(
                        _(
                            "Only MOA fields can be exported to Selenium for the "
                            "moment. It is not the case of box '%s'."
                        )
                        % box.display_name
                    )

        side_str = json.dumps(side_dict, ensure_ascii=False)
        side_bytes = side_str.encode("utf-8")

        filename = "selenium_%s.side" % name
        attach = self.env["ir.attachment"].create(
            {
                "name": filename,
                "res_id": self.id,
                "res_model": self._name,
                "raw": side_bytes,
            }
        )
        self.write({"selenium_attachment_id": attach.id})
        action = {
            "name": _("Selenium IDE File"),
            "type": "ir.actions.act_url",
            "url": "web/content/?model=%s&id=%d&filename_field=selenium_attachment_name&"
            "field=selenium_attachment_datas&download=true&filename=%s"
            % (self._name, self.id, filename),
            "target": "new",
        }
        self.message_post(
            body=_(
                '<a href="https://www.selenium.dev/selenium-ide/" '
                'target="_blank">Selenium IDE</a> file generated.'
            )
        )
        return action

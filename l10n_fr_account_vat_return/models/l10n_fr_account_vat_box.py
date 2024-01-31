# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero

PUSH_RATE_PRECISION = 4


class L10nFrAccountVatBox(models.Model):
    _name = "l10n.fr.account.vat.box"
    _description = "France VAT Return (CA3) box"
    _order = "sequence, id"

    sequence = fields.Integer(default=10, readonly=True)
    active = fields.Boolean(default=True)
    display_type = fields.Selection(
        [
            ("section", "Section"),
            ("sub_section", "Sub-Section"),
        ],
        readonly=True,
    )
    code = fields.Char(readonly=True)
    name = fields.Char(string="Label", required=True)
    full_label = fields.Char(readonly=True)
    meaning_id = fields.Char(string="Meaningful ID", readonly=True)
    manual = fields.Boolean(readonly=True)
    negative = fields.Boolean(readonly=True)
    accounting_method = fields.Selection(
        [
            ("debit", "Debit"),
            ("credit", "Credit"),
        ],
        readonly=True,
    )
    due_vat_rate = fields.Integer(string="VAT Rate x100", readonly=True)
    due_vat_base_box_id = fields.Many2one(
        "l10n.fr.account.vat.box", string="Due VAT Base", readonly=True
    )
    form_code = fields.Selection(
        [
            ("3310CA3", "3310-CA3"),
            ("3310A", "3310-A"),
        ],
        string="Form",
        required=True,
        readonly=True,
    )
    edi_code = fields.Char(string="EDI Code", readonly=True)
    # edi_code can't be required because of sections
    edi_type = fields.Selection(
        [
            ("MOA", "Monetary (MOA)"),
            ("CCI_TBX", "Boolean (CCI/TBX)"),
            ("PCD", "Percentage (PCD)"),
            ("QTY", "Quantity (QTY)"),
            ("FTX", "Char (FTX)"),
            ("NAD", "Name and address (NAD)"),
        ],
        string="EDI Type",
        readonly=True,
    )
    nref_code = fields.Char(string="N-REF Code", readonly=True)
    print_page = fields.Selection(
        [
            ("1", "First Page"),
            ("2", "Second Page"),
            ("3", "Third Page"),
        ],
        string="Page",
        readonly=True,
    )
    print_x = fields.Integer("Print Position X", readonly=True)
    print_y = fields.Integer("Print Position Y", readonly=True)
    account_code = fields.Char(string="Generic Account Code")
    account_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        domain="[('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        help="If not set, Odoo will use the first account that starts with the "
        "Generic Account Code. If set, Odoo will ignore the Generic Account Code "
        "and use this account.",
    )
    push_sequence = fields.Integer(readonly=True)
    # 10: appendix lines
    # 20: totals cols appendix
    # 30 : Appendix to CA3
    # 40 : CA3 total TVA due + total TVA deduc
    # 100 : CA3 end : total à payer + crédit à reporter
    push_box_id = fields.Many2one("l10n.fr.account.vat.box", readonly=True)
    push_rate = fields.Float(digits=(16, PUSH_RATE_PRECISION), readonly=True)

    _sql_constraints = [
        ("sequence_unique", "unique(sequence)", "This sequence already exists."),
        (
            "code_form_unique",
            "unique(form_code, code)",
            "This code already exists for this form.",
        ),
        (
            "edi_code_form_unique",
            "unique(form_code, edi_code)",
            "This EDI code already exists for this form.",
        ),
        ("nref_code_unique", "unique(nref_code)", "This N-REF code already exists."),
        (
            "meaning_id_unique",
            "unique(meaning_id)",
            "This meaningful ID already exists.",
        ),
        (
            "due_vat_rate_positive",
            "CHECK(due_vat_rate >= 0)",
            "The Due VAT rate must be positive.",
        ),
        (
            "due_vat_rate_max",
            "CHECK(due_vat_rate < 10000)",
            "The Due VAT rate must be under 10000.",
        ),
        (
            "unique_page_x_y",
            "unique(print_page, print_x, print_y)",
            "There is already a box at this position!",
        ),
    ]

    @api.onchange("display_type")
    def display_type_change(self):
        if self.display_type:
            self.code = False
            self.accounting_method = False
            self.due_vat_rate = False
            self.due_vat_base_box_id = False
            self.edi_code = False
            self.edi_type = False
            self.nref_code = False
            self.print_page = False
            self.print_x = False
            self.print_y = False
            self.account_code = False
            self.account_id = False

    @api.constrains(
        "edi_type",
        "display_type",
        "due_vat_base_box_id",
        "meaning_id",
        "manual",
        "accounting_method",
        "account_code",
        "account_id",
        "push_box_id",
        "push_rate",
        "push_sequence",
        "negative",
    )
    def _check_box(self):  # noqa: C901
        for box in self:
            if box.display_type:
                if (
                    box.accounting_method
                    or not float_is_zero(box.due_vat_rate, precision_digits=2)
                    or box.due_vat_base_box_id
                    or box.manual
                    or box.edi_code
                    or box.edi_type
                    or box.nref_code
                    or box.print_page
                    or box.print_x
                    or box.print_y
                    or box.push_box_id
                    or box.negative
                ):
                    raise ValidationError(
                        _("The section or sub-section '%s' is not properly configured.")
                        % box.display_name
                    )
            else:
                if not box.edi_code:
                    raise ValidationError(
                        _("The box '%s' must have an EDI code.") % box.display_name
                    )
                if not box.edi_type:
                    raise ValidationError(
                        _("The box '%s' must have an EDI type.") % box.display_name
                    )
                if box.negative and box.edi_type != "MOA":
                    raise ValidationError(
                        _(
                            "The box '%s' is a negative box but its EDI Type "
                            "is not 'MOA'."
                        )
                        % box.display_name
                    )
                if (
                    not box.code
                    and box.form_code == "3310CA3"
                    and box.edi_type == "MOA"
                ):
                    # on 3310-A, total boxes don't have a code
                    raise ValidationError(
                        _("The box '%s' must have a code.") % box.display_name
                    )
                print_data = [box.print_page, box.print_x, box.print_y]
                if (
                    box.form_code == "3310CA3"
                    and box.active
                    and not all(print_data)
                    and box.code
                ):
                    raise ValidationError(
                        _("Missing print caracteristics on box '%s'.")
                        % box.display_name
                    )
                if box.meaning_id and box.meaning_id.startswith(
                    ("due_vat_regular", "due_vat_extracom_product")
                ):
                    if not box.due_vat_base_box_id:
                        raise ValidationError(
                            _(
                                "Missing Due VAT Base on box '%s' which is a Due VAT box."
                            )
                            % box.display_name
                        )
                    if box.accounting_method != "debit":
                        raise ValidationError(
                            _(
                                "Wrong accounting method on Due VAT box '%s': "
                                "it should be 'Debit'."
                            )
                            % box.display_name
                        )
                    if box.print_y != box.due_vat_base_box_id.print_y:
                        raise ValidationError(
                            _(
                                "Due VAT box '%(due_vat_box)s' has print Y "
                                "%(due_vat_box_print_y)s whereas "
                                "Base Due VAT box '%(due_vat_base_box)s' has print Y "
                                "%(due_vat_base_box_print_y)s. "
                                "They should be on the same line.",
                                due_vat_box=box.display_name,
                                due_vat_box_print_y=box.print_y,
                                due_vat_base_box=box.due_vat_base_box_id.display_name,
                                due_vat_base_box_print_y=box.due_vat_base_box_id.print_y,
                            )
                        )
                if (
                    box.meaning_id
                    and box.meaning_id.startswith("untaxed_op_")
                    and box.accounting_method
                ):
                    raise ValidationError(
                        _(
                            "Box '%s' should not have an accounting method "
                            "considering it's an untaxed operation."
                        )
                        % box.display_name
                    )
                if not box.accounting_method:
                    if box.account_code or box.account_id:
                        raise ValidationError(
                            _(
                                "Box '%s' doesn't have an accounting method, "
                                "so it should not have any accounting parameter."
                            )
                            % box.display_name
                        )
                if box.push_box_id:
                    if box.push_box_id.manual:
                        raise ValidationError(
                            _(
                                "Box '%(box)s' has a push box '%(push_box)s' "
                                "that is configured as manual.",
                                box=box.display_name,
                                push_box=box.push_box_id.display_name,
                            )
                        )
                    if not box.push_sequence:
                        raise ValidationError(
                            _("Box '%s' has a push box but is missing a push sequence.")
                            % box.display_name
                        )
                else:
                    if not float_is_zero(
                        box.push_rate, precision_digits=PUSH_RATE_PRECISION
                    ):
                        raise ValidationError(
                            _(
                                "Box '%s' doesn't have a push box, "
                                "so it's push rate should be 0."
                            )
                            % box.display_name
                        )
                    if box.push_sequence:
                        raise ValidationError(
                            _(
                                "Box '%s' doesn't have a push box, "
                                "so it's push sequence should be 0."
                            )
                            % box.display_name
                        )

    @api.depends("code", "name", "display_type")
    def name_get(self):
        res = []
        form2label = dict(
            self.fields_get("form_code", "selection")["form_code"]["selection"]
        )
        for box in self:
            name = "[%s]" % form2label.get(box.form_code)
            if not box.display_type:
                if box.code:
                    name += "(%s) %s" % (box.code, box.name)
                else:
                    name += box.name
            else:
                if box.code:
                    name += "%s. %s" % (box.code, box.name)
                else:
                    name += box.name
            res.append((box.id, name))
        return res

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        if args is None:
            args = []
        if name and operator == "ilike":
            recs = self.search([("code", "=", name)] + args, limit=limit)
            if recs:
                return recs.name_get()
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

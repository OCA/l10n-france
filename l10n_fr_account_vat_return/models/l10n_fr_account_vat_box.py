# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero

PUSH_RATE_PRECISION = 4


class L10nFrAccountVatBox(models.Model):
    _name = "l10n.fr.account.vat.box"
    _description = "France VAT Return (CA3) box"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    display_type = fields.Selection(
        [
            ("section", "Section"),
            ("sub_section", "Sub-Section"),
        ],
        string="Display Type",
    )
    code = fields.Char()
    name = fields.Char(string="Label", required=True)
    full_label = fields.Char(string="Full Label")
    box_type = fields.Selection(
        [
            ("taxed_op_france", "Taxed Operations - France"),
            (
                "taxed_op_autoliq_extracom",
                "Taxed Operations - Extracom Autoliquidation",
            ),
            (
                "taxed_op_autoliq_intracom_service",
                "Taxed Operations - Intracom Autoliquidation Services",
            ),
            (
                "taxed_op_autoliq_intracom_product",
                "Taxed Operations - Intracom Autoliquidation Products",
            ),
            ("untaxed_op_intracom_b2b", "Untaxed Operations - Intracom B2B"),
            ("untaxed_op_intracom_b2c", "Untaxed Operations - Intracom B2C"),
            ("untaxed_op_extracom", "Untaxed Operations - Extracom"),
            ("untaxed_op_france_exo", "Untaxed Operations - France Exonerated"),
            ("due_vat", "Due VAT Amount"),
            ("due_vat_base", "Due VAT Base"),
            ("due_vat_intracom_product", "Due VAT Intracom Products"),
            ("due_vat_monaco", "Due VAT Monaco"),
            ("due_vat_total", "Total Due VAT"),
            ("no_push_total_credit", "Not Pushed Total Credit"),
            ("no_push_total_debit", "Not Pushed Total Debit"),
            ("end_total_debit", "End Total Credit"),
            ("end_total_credit", "End Total Debit"),
            ("credit_deferment", "Credit Deferment"),
            ("deductible_vat_asset", "Deductible VAT Amount Asset"),
            ("deductible_vat_other", "Deductible VAT Amount Other"),
            ("deductible_vat_total", "Total Deductible VAT"),
            ("vat_reimbursement", "VAT Reimbursement"),
            ("manual", "Manual"),  # boxes that accountant can select at first step
        ],
        string="Type",
    )
    negative_switch_box_id = fields.Many2one(
        "l10n.fr.account.vat.box",
        string="Negative Switch Box",
        help="If the amount of this box is negative, its lines will be transfered "
        "to another box with a sign inversion.",
    )
    accounting_method = fields.Selection(
        [
            ("debit", "Debit"),
            ("credit", "Credit"),
        ],
        string="Accounting Method",
    )
    due_vat_rate = fields.Integer(string="VAT Rate x100")
    due_vat_base_box_id = fields.Many2one(
        "l10n.fr.account.vat.box",
        string="Due VAT Base",
        domain=[("box_type", "=", "due_vat_base")],
    )
    form_code = fields.Selection(
        [
            ("3310CA3", "3310-CA3"),
            ("3310A", "3310-A"),
        ],
        string="Form",
        required=True,
    )
    edi_code = fields.Char(string="EDI Code")
    # edi_code can't be required because of sections
    edi_type = fields.Selection(
        [
            ("MOA", "Monetary (MOA)"),
            ("CCI_TBX", "Boolean (CCI/TBX)"),
            ("PCD", "Percentage (PCD)"),
            ("QTY", "Quantity (QTY)"),
            ("FTX", "Char (FTX)"),
        ],
        string="EDI Type",
    )
    nref_code = fields.Char(string="N-REF Code")
    print_page = fields.Selection(
        [
            ("1", "First Page"),
            ("2", "Second Page"),
            ("3", "Third Page"),
        ],
        string="Page",
    )
    print_x = fields.Integer("Print Position X")
    print_y = fields.Integer("Print Position Y")
    account_code = fields.Char(string="Generic Account Code")
    account_id = fields.Many2one(
        "account.account",
        string="Account",
        company_dependent=True,
        domain="[('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        help="If not set, Odoo will use the first account that starts with the "
        "Generic Account Code. If set, Odoo will ignore the Generic Account Code "
        "and use this account.",
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        company_dependent=True,
        domain="[('company_id', 'in', (False, current_company_id))]",
    )
    push_sequence = fields.Integer()
    # 10: appendix lines
    # 20: totals cols appendix
    # 30 : Appendix to CA3
    # 40 : CA3 total TVA due + total TVA deduc
    # 100 : CA3 end : total à payer + crédit à reporter
    push_box_id = fields.Many2one(
        "l10n.fr.account.vat.box",
        string="Push Box",
        domain=[("box_type", "=", "manual")],
    )
    push_rate = fields.Float(digits=(16, PUSH_RATE_PRECISION), string="Push Rate")

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
            self.box_type = False
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
            self.analytic_account_id = False

    @api.constrains(
        "edi_type",
        "display_type",
        "due_vat_base_box_id",
        "box_type",
        "accounting_method",
        "account_code",
        "account_id",
        "analytic_account_id",
        "push_box_id",
        "push_rate",
        "push_sequence",
        "negative_switch_box_id",
    )
    def _check_box(self):  # noqa: C901
        for box in self:
            if box.display_type:
                if (
                    box.box_type
                    or box.accounting_method
                    or not float_is_zero(self.due_vat_rate, precision_digits=2)
                    or self.due_vat_base_box_id
                    or self.edi_code
                    or self.edi_type
                    or self.nref_code
                    or box.print_page
                    or box.print_x
                    or box.print_y
                    or box.push_box_id
                    or box.negative_switch_box_id
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
                if box.negative_switch_box_id and box.edi_type != "MOA":
                    raise ValidationError(
                        _(
                            "The box '%s' has a negative switch box but it's EDI Type "
                            "is not 'MOA'."
                        )
                        % box.display_name
                    )
                if (
                    box.negative_switch_box_id
                    and box.negative_switch_box_id.edi_type != "MOA"
                ):
                    raise ValidationError(
                        _(
                            "The box '%s' is the negative switch box of '%s' but it's "
                            "EDI Type is not 'MOA'."
                        )
                        % (box.negative_switch_box_id.display_name, box.display_name)
                    )
                if not box.code and box.form_code == "3310CA3":
                    # on 3310-A, total boxes don't have a code
                    raise ValidationError(
                        _("The box '%s' must have a code.") % box.display_name
                    )
                print_data = [box.print_page, box.print_x, box.print_y]
                any(print_data)
                if box.form_code == "3310CA3" and not all(print_data):
                    raise ValidationError(
                        _("Missing print caracteristics on box '%s'.")
                        % box.display_name
                    )
                if box.box_type == "due_vat":
                    if not box.due_vat_base_box_id:
                        raise ValidationError(
                            _(
                                "Missing Due VAT Base on box '%s' which is a Due VAT box."
                            )
                            % box.display_name
                        )
                    elif box.due_vat_base_box_id.box_type != "due_vat_base":
                        raise ValidationError(
                            _(
                                "The Due VAT box '%s' has '%s' configured as "
                                "Due VAT Base box, but it has a different type."
                            )
                            % (box.display_name, box.due_vat_base_box_id.display_name)
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
                                "Due VAT box '%s' has print Y %d whereas "
                                "Base Due VAT box '%s' has print Y %d. "
                                "They should be on the same line."
                            )
                            % (
                                box.display_name,
                                box.print_y,
                                box.due_vat_base_box_id.display_name,
                                box.due_vat_base_box_id.print_y,
                            )
                        )
                elif box.due_vat_base_box_id:
                    raise ValidationError(
                        _(
                            "The field 'Due VAT Base' is set for box '%s' "
                            "which is not a Due VAT box."
                        )
                        % box.display_name
                    )
                if (
                    box.box_type
                    and box.box_type.startswith("untaxed_op_")
                    and box.accounting_method
                ):
                    raise ValidationError(
                        _(
                            "Box '%s' should not have an accounting method "
                            "considering it's box type."
                        )
                        % box.display_name
                    )
                if not box.accounting_method:
                    if box.account_code or box.account_id or box.analytic_account_id:
                        raise ValidationError(
                            _(
                                "Box '%s' doesn't have an accounting method, "
                                "so it should not have any accounting parameter."
                            )
                            % box.display_name
                        )
                if box.push_box_id:
                    if box.push_box_id.box_type in ("manual", "no_push_total"):
                        raise ValidationError(
                            _(
                                "Box '%s' has a push box '%s' that is configured "
                                "as manual or not pushed total."
                            )
                            % (box.display_name, box.push_box_id.display_name)
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
                                "so it's push rate should be 0."
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

    @api.model
    def _box_from_single_box_type(self, box_type):
        box = self.search([("box_type", "=", box_type)])
        if len(box) != 1:
            boxtype2label = dict(
                self.fields_get("box_type", "selection")["box_type"]["selection"]
            )
            raise UserError(
                _(
                    "A single box with type '%s' should exists, "
                    "but there are %d box(es) of that type. This should never happen."
                )
                % (boxtype2label[box_type], len(box))
            )
        return box

# Copyright 2010-2022 Akretion France (http://www.akretion.com/)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# If you modify the line below, please also update intrastat_type_view.xml
# (form view of report.intrastat.type, field transaction_code
fiscal_only_tuple = ("25", "26", "31")


class IntrastatTransaction(models.Model):
    _inherit = "intrastat.transaction"

    fr_object_type = fields.Selection(
        [
            ("out_invoice", "Customer Invoice"),
            ("out_refund", "Customer Refund"),
            ("in_invoice", "Supplier Invoice"),
            ("none", "None"),
        ],
        string="Possible on",
        index=True,
        required=True,
    )
    # procedure_code => field 'code' from intrastat_product
    fr_transaction_code = fields.Selection(
        [
            ("", "-"),
            ("11", "11"),
            ("12", "12"),
            ("13", "13"),
            ("14", "14"),
            ("19", "19"),
            ("21", "21"),
            ("22", "22"),
            ("23", "23"),
            ("29", "29"),
            ("30", "30"),
            ("41", "41"),
            ("42", "42"),
            ("51", "51"),
            ("52", "52"),
            ("70", "70"),
            ("80", "80"),
            ("91", "91"),
            ("99", "99"),
        ],
        string="Transaction code",
        help="For the 'DEB' declaration to France's customs "
        "administration, you should enter the number 'nature de la "
        "transaction' here.",
    )
    fr_is_fiscal_only = fields.Boolean(
        string="Is fiscal only ?",
        help="Only fiscal data should be provided for this procedure code.",
    )
    fr_fiscal_value_multiplier = fields.Integer(
        string="Fiscal value multiplier",
        help="'0' for procedure codes 19 and 29, "
        "'-1' for procedure code 25, '1' for all the others. "
        "This multiplier is used to compute the total fiscal value of "
        "the declaration.",
    )
    # TODO : see with Luc if we can move it to intrastat_product
    fr_intrastat_product_type = fields.Selection(
        [
            ("arrivals", "Arrivals"),
            ("dispatches", "Dispatches"),
        ],
        string="Intrastat product type",
        help="Decides on which kind of Intrastat product report "
        "('Import' or 'Export') this Intrastat type can be selected.",
    )

    # replace the native SQL constraint of the intrastat_product module
    _sql_constraints = [
        (
            "intrastat_transaction_code_unique",
            "unique(code, fr_transaction_code, company_id)",
            "An Intrastat Transaction already exists for this company with the "
            "same code and the same procedure code.",
        )
    ]

    @api.constrains("code", "fr_transaction_code")
    def _code_check(self):
        fr_country = self.env.ref("base.fr")
        for trans in self:
            if (
                trans.company_id.country_id
                and trans.company_id.country_id == fr_country
            ):
                if (
                    trans.code not in fiscal_only_tuple
                    and not trans.fr_transaction_code
                ):
                    raise ValidationError(
                        _("You must enter a value for the transaction code.")
                    )
                if trans.code in fiscal_only_tuple and trans.fr_transaction_code:
                    raise ValidationError(
                        _(
                            "You should not set a transaction code when the "
                            "Code (i.e. Procedure Code) is '25', '26' or '31'."
                        )
                    )

    @api.onchange("code")
    def procedure_code_on_change(self):
        if self.code in fiscal_only_tuple:
            self.fr_transaction_code = False

    @api.depends("code", "description", "fr_transaction_code")
    def name_get(self):
        res = []
        for trans in self:
            name = trans.code
            if trans.fr_transaction_code:
                name += "/%s" % trans.fr_transaction_code
            if trans.description:
                name += " " + trans.description
            name = len(name) > 55 and name[:55] + "..." or name
            res.append((trans.id, name))
        return res

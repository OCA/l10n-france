To implement your own factor connector, see account_factoring_receivable_balance_bpce module.


At the minimum, you have to define this Subrogation code


.. code-block:: python

    class SubrogationReceipt(models.Model):
        _inherit = "subrogation.receipt"

        def _prepare_factor_file_myownfactor(self):
            self.ensure_one
            name = "myown_file.txt"
            return {
                "name": name,
                "res_id": self.id,
                "res_model": self._name,
                "datas": self._prepare_factor_file_data_myownfactor(),
            }

        def _prepare_factor_file_data_myownfactor(self):
            ...
            return base64.b64encode(data)

        def _get_partner_field(self):
            res = super()._get_partner_field()
            if self.factor_type == "myownfactor":
                return "myownfactor_factoring_balance"
            return res


this journal code


.. code-block:: python

    class AccountJournal(models.Model):
        _inherit = "account.journal"

        factor_type = fields.Selection(
            selection_add=[("myownfactor", "MyOwnFactor")], ondelete={"myownfactor": "set null"}
        )


this partner code


.. code-block:: python

    class ResPartner(models.Model):
        _inherit = "res.partner"

    myownfactor_factoring_balance = fields.Boolean(
        string="Use MyOwnFactor factoring balance",
        groups="account.group_account_invoice",
        company_dependent=True,
        help="Use MyOwnFactor factoring receivable balance external service",
    )


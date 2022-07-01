To implement your own factor connector, see account_factoring_receivable_balance_bpce module.


At the minimum, you have to define


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

        def _prepare_factor_file_myownfactor(self):
            ...
            return base64.b64encode(data)


Other settings in journal


.. code-block:: python

    class AccountJournal(models.Model):
        _inherit = "account.journal"

        factor_type = fields.Selection(
            selection_add=[("myownfactor", "MyOwnFactor")], ondelete={"myownfactor": "set null"}
        )


This small module adds support for partner matching based on SIRET or SIREN when importing a business document (invoice, customer order, etc), in Odoo. It depends on the module *base_business_document_import* from the `edi OCA project <https://github.com/OCA/edi>`_. This module is the base module for:

* *account_invoice_import* which imports supplier invoices as PDF or XML files (this module also requires some additionnal modules such as *account_invoice_import_invoice2data*, *account_invoice_import_ubl*, *account_invoice_import_facturx*, etc... to support specific invoice formats),

* *sale_invoice_import* which imports sale orders as CSV, XML or PDF files (this module also requires some additionnal modules such as *sale_invoice_import_csv* or *sale_invoice_import_ubl* to support specific order formats).

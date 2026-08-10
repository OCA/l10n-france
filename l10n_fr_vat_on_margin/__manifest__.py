# Copyright 2024 Moka
# @author Damien Horvat <damien@moka.cloud>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "France - TVA sur marge",
    "summary": "l10n_fr_vat_on_margin",
    "version": "16.0.1.0.3",
    "author": "Moka",
    "website": "https://moka.cloud",
    "license": "AGPL-3",
    "category": "Accounting",
    "depends": [
        "l10n_fr",
        "account",
        "sale_order_line_supplier_informations",
        "sale_purchase",
        "sale_margin",
        ],
    "data": [
        'security/ir.model.access.csv',
        "views/product_view.xml",
        'views/account_tax_views.xml',
        'views/sale_order_line_views.xml',
        'views/account_move_views.xml',
        'views/account_report_views.xml',
        'views/fiscal_position_views.xml',
        'views/purchase_order_views.xml',
        'views/sale_order_views.xml',
        'data/account_chart_template.xml',
        'data/account_tax_group.xml',
        'data/account_tax_template.xml',
        # 'data/account_fiscal_position.xml',
        'wizard/sale_order_fiscal_position_wizard.xml',
    ],
}

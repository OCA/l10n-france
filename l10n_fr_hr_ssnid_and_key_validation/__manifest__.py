# -*- coding: utf-8 -*-
# Copyright 2020 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{'name': 'France - Ssnid check',
 'version': '10.0.1.0.0',
 'author': 'Camptocamp,Odoo Community Association (OCA)',
 'license': 'AGPL-3',
 'category': 'French Localization',
 'depends': ['hr',
             ],
 'website': 'https://github.com/OCA/l10n-france',
 'data': ['views/hr_employee.xml',
          ],
 'installable': True,
 'external_dependencies': {'python': ['stdnum']}
 }

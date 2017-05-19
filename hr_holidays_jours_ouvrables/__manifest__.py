# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{'name': 'France - Jours Ouvrables',
 'version': '10.0.1.0.0',
 'author': 'Camptocamp,Odoo Community Association (OCA)',
 'license': 'AGPL-3',
 'category': 'French Localization',
 'depends': ['hr_holidays',
             'hr_public_holidays',  # OCA/hr
             'hr_holidays_compute_days',  # OCA/hr
             ],
 'website': 'https://www.camptocamp.com',
 'data': ['views/hr_holidays_status_views.xml',
          'views/res_company_views.xml',
          'security/ir.model.access.csv',
          ],
 'installable': True,
 }

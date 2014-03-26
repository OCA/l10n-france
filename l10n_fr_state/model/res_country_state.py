# -*- encoding: utf-8 -*-
################################################################################
#    See __openerp__.py file for Copyright and Licence Informations.
################################################################################

from openerp.osv import fields
from openerp.osv.orm import Model

class res_country_state(Model):
    _inherit = 'res.country.state'

    _columns = {
        'code': fields.char('State Code', size=4, required=True,
            help='The state code in max. four chars.',
            ),
    }

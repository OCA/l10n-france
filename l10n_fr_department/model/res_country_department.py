# -*- encoding: utf-8 -*-
################################################################################
#    See __openerp__.py file for Copyright and Licence Informations.
################################################################################

from openerp.osv import fields
from openerp.osv.orm import Model

class res_country_department(Model):
    _description="Department"
    _name = 'res.country.department'

    _columns = {
        'country_state_id': fields.many2one('res.country.state', 'State',
                required=True,
                help="State related of the current department",),
        'country_id': fields.related('country_state_id', 'country_id',
                type='many2one', relation='res.country', string='Country',
                help="Country of the related state",),
        'name': fields.char('Department Name', size=128, required=True,),
        'code': fields.char('Departement Code', size=5, required=True,
                help="The department code in max. five chars. "\
                "(ISO 3166-2 Codification)",),
    }


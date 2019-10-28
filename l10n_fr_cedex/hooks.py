# © 2019 Le Filament (https://le-filament.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def post_init_hook(cr, registry):
    """ Add street3 to address format """
    query = """
        UPDATE res_country
        SET address_format = replace(
        address_format,
        E'%(zip)s %(city)s\n',
        E'%(zip)s %(city)s %(cedex)s\n'
        )
        WHERE code IN ('FR', 'RE', 'GP', 'MQ', 'GF', 'YT', 'BL', 'MF', 'PM',
        'PF', 'NC', 'WF', 'MC', 'AD')
    """
    cr.execute(query)


def uninstall_hook(cr, registry):
    """ Remove street3 from address format """
    query = """
        UPDATE res_country
        SET address_format = replace(
        address_format,
        E' %(cedex)s',
        ''
        )
        WHERE code IN ('FR', 'RE', 'GP', 'MQ', 'GF', 'YT', 'BL', 'MF', 'PM',
        'PF', 'NC', 'WF', 'MC', 'AD')
    """
    cr.execute(query)

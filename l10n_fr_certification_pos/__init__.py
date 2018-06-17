# -*- coding: utf-8 -*-
from . import models

from openerp import api, SUPERUSER_ID


def _generate_pos_config_sequences(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    configs = env['pos.config'].search([])
    configs.generate_secure_sequence_if_required()

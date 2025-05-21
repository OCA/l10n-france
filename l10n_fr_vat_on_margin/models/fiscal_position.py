from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import frozendict
from odoo.tools.safe_eval import safe_eval

from collections import defaultdict
import math
import re


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    vat_on_margin = fields.Boolean(string='VAT on Margin', help='Check this box if the fiscal position applies to VAT on margin.')
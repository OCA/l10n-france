# Copyright 2024 Moka (https://moka.cloud).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

FR_CHART_TEMPLATE = 'l10n_fr.l10n_fr_pcg_chart_template'

# Tax group accounts, by the code of the account template they come from.
TAX_GROUP_ACCOUNTS = {
    'property_tax_payable_account_id': '445750',
    'property_tax_receivable_account_id': '445665',
}


def post_init_hook(cr, registry):
    """Give the margin scheme to companies that already run the French chart.

    Companies loading the chart from now on are served by Odoo itself, which
    generates every template attached to the chart template. Those that loaded
    it before this module was installed would otherwise get nothing, which is
    exactly the gap the previous base.main_company hardcoding papered over for
    one company only.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    chart = env.ref(FR_CHART_TEMPLATE, raise_if_not_found=False)
    if not chart:
        _logger.info("French chart template not found, nothing to generate.")
        return

    companies = env['res.company'].search([('chart_template_id', '=', chart.id)])
    for company in companies:
        _generate_for_company(env, chart, company)


def _generate_for_company(env, chart, company):
    account_by_code = _ensure_accounts(env, chart, company)
    _ensure_taxes(env, chart, company)
    _ensure_tax_group_accounts(env, company, account_by_code)


def _ensure_accounts(env, chart, company):
    """Create the margin scheme accounts this company is missing.

    Returns every account of the scheme the company owns, by code, whether it
    was just created or already there.
    """
    templates = env['account.account.template'].search([
        ('chart_template_id', '=', chart.id),
        ('code', 'in', _scheme_account_codes(env)),
    ])
    account_by_code = {}
    for template in templates:
        account = env['account.account'].search([
            ('code', '=', template.code),
            ('company_id', '=', company.id),
        ], limit=1)
        if not account:
            account = env['account.account'].create({
                'name': template.name,
                'code': template.code,
                'account_type': template.account_type,
                'reconcile': template.reconcile,
                'company_id': company.id,
            })
            _logger.info(
                "Created account %s for company %s.", template.code, company.name)
        account_by_code[template.code] = account
    return account_by_code


def _scheme_account_codes(env):
    codes = []
    for xmlid in (
        'account_template_706500', 'account_template_707500',
        'account_template_604500', 'account_template_607500',
        'account_template_445750', 'account_template_445665',
    ):
        template = env.ref(
            'l10n_fr_vat_on_margin.%s' % xmlid, raise_if_not_found=False)
        if template:
            codes.append(template.code)
    return codes


def _ensure_taxes(env, chart, company):
    """Generate the margin taxes this company is missing.

    Taxes are matched by name and usage rather than by xmlid: a database
    upgraded from the pre-template layout already holds them, detached from
    any module by the pre-migration, and generating them again would leave two
    identical taxes side by side.
    """
    templates = env['account.tax.template'].with_context(active_test=False).search([
        ('chart_template_id', '=', chart.id),
        ('vat_on_margin', '=', True),
    ])
    if not templates:
        return

    existing = []
    missing = env['account.tax.template']
    for template in templates:
        tax = env['account.tax'].with_context(active_test=False).search([
            ('name', '=', template.name),
            ('type_tax_use', '=', template.type_tax_use),
            ('company_id', '=', company.id),
        ], limit=1)
        if tax:
            existing.append((template, tax))
            # An upgraded database carries taxes that predate the custom
            # fields being copied from the template; realign them.
            tax.write({
                'vat_on_margin': template.vat_on_margin,
                'tax_calculation_method': template.tax_calculation_method,
            })
        else:
            missing |= template

    if missing:
        missing._generate_tax(
            company, accounts_exist=True, existing_template_to_tax=existing)
        _logger.info(
            "Generated %s margin taxes for company %s.", len(missing), company.name)


def _ensure_tax_group_accounts(env, company, account_by_code):
    """Point the margin tax group at the dedicated accounts of the scheme.

    The value is looked up in ir.property rather than read off the record: the
    chart sets a company-wide default for these fields, so every tax group
    answers with the generic VAT accounts. Reading the resolved value would
    report "already set" and leave the margin group on 445710/445660 instead
    of the 445750/445665 the scheme requires. Only a value belonging to this
    very group counts as a deliberate choice worth preserving.
    """
    group = env.ref(
        'l10n_fr_vat_on_margin.tax_group_margin_vat', raise_if_not_found=False)
    if not group:
        return
    res_id = 'account.tax.group,%s' % group.id
    for field_name, code in TAX_GROUP_ACCOUNTS.items():
        account = account_by_code.get(code)
        if not account:
            continue
        field = env['ir.model.fields']._get('account.tax.group', field_name)
        own_value = env['ir.property'].sudo().search([
            ('fields_id', '=', field.id),
            ('company_id', '=', company.id),
            ('res_id', '=', res_id),
        ], limit=1)
        if not own_value:
            group.with_company(company)[field_name] = account

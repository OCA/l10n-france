# Copyright 2021 Camptocamp
#   @author Silvio Gregorini <silvio.gregorini@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


def get_ecotax_cls(env, ecotaxe_type, search_domain=None, create_vals=None):
    ecotax_cls = _search_ecotax_cls(env, ecotaxe_type, search_domain)
    if not ecotax_cls:
        ecotax_cls = _create_ecotax_cls(env, ecotaxe_type, create_vals)
    return ecotax_cls


def _search_ecotax_cls(env, ecotaxe_type, search_domain=None):
    return env["account.ecotaxe.classification"].search(
        [("ecotaxe_type", "=", ecotaxe_type)] + list(search_domain or [])
    )


def _create_ecotax_cls(env, ecotaxe_type, create_vals=None):
    assert ecotaxe_type in ("fixed", "weight_based")
    if ecotaxe_type == "fixed":
        vals = {
            "name": "Fixed Ecotax",
            "ecotaxe_type": "fixed",
            "default_fixed_ecotaxe": 5.0,
            "ecotaxe_product_status": "M",
            "ecotaxe_supplier_status": "FAB",
        }
    else:
        vals = {
            "name": "Weight Based Ecotax",
            "ecotaxe_type": "weight_based",
            "ecotaxe_coef": 0.04,
            "ecotaxe_product_status": "P",
            "ecotaxe_supplier_status": "FAB",
        }
    create_vals = dict(create_vals or {})
    create_vals.pop("ecotaxe_type", None)
    vals.update(create_vals)
    return env["account.ecotaxe.classification"].create(vals)

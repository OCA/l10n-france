# Copyright 2021 Camptocamp
#   @author Silvio Gregorini <silvio.gregorini@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from random import choice

from odoo.tests.common import Form, tagged

from odoo.addons.product.tests.common import TestProductCommon

from .common import get_ecotax_cls


# Using TestProductCommon to access product.attribute already defined in there
@tagged("post_install", "-at_install")
class TestProductEcotaxe(TestProductCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # ECOTAXES
        dom = [("company_id", "=", cls.env.user.company_id.id)]
        vals = {"company_id": cls.env.user.company_id.id}
        # 1- Fixed ecotax
        cls.ecotax_fixed = get_ecotax_cls(cls.env, "fixed", dom, vals)
        # 2- Fixed ecotax
        cls.ecotax_weight = get_ecotax_cls(cls.env, "weight_based", dom, vals)

    @classmethod
    def _create_product(cls, ecotax_cls):
        with Form(
            cls.env["product.product"], "product.product_normal_form_view"
        ) as prod_form:
            prod_form.name = "Product"
            prod_form.ecotaxe_classification_id = ecotax_cls
        return prod_form.save()

    @classmethod
    def _create_single_variant_template(cls, ecotax_cls):
        with Form(
            cls.env["product.template"], "product.product_template_only_form_view"
        ) as tmpl_form:
            tmpl_form.name = "Single-variant Template"
            tmpl_form.ecotaxe_classification_id = ecotax_cls
        return tmpl_form.save()

    @classmethod
    def _create_multi_variant_template(cls, ecotax_cls, attributes):
        with Form(
            cls.env["product.template"], "product.product_template_only_form_view"
        ) as tmpl_form:
            tmpl_form.name = "Multi-variant Template"
            tmpl_form.ecotaxe_classification_id = ecotax_cls
            for attrib, values in attributes:
                with tmpl_form.attribute_line_ids.new() as attrib_line:
                    attrib_line.attribute_id = attrib
                    for val in values:
                        attrib_line.value_ids.add(val)
        return tmpl_form.save()

    def test_01_templates_and_products_creation(self):
        cls = choice([self.ecotax_fixed, self.ecotax_weight])

        # Create a template with 1 variant, check that its product has the
        # correct ecotax class
        tmpl_1_variant = self._create_single_variant_template(cls)
        self.assertTrue(
            tmpl_1_variant.product_variant_ids.ecotaxe_classification_id
            == tmpl_1_variant.product_variant_ids.ecotaxe_classification_id
            == cls
        )

        # Create a template with 3 variants, check that its products have all
        # the correct ecotax class
        tmpl_3_variant = self._create_multi_variant_template(
            cls,
            [
                (
                    self.prod_att_1,
                    self.prod_attr1_v1 | self.prod_attr1_v2 | self.prod_attr1_v3,
                )
            ],
        )
        self.assertTrue(
            tmpl_3_variant.product_variant_ids.ecotaxe_classification_id
            == tmpl_3_variant.ecotaxe_classification_id
            == cls
        )

        # Create a product, check that the template that has been implicitly
        # created has the same ecotax
        prod = self._create_product(cls)
        self.assertTrue(
            prod.ecotaxe_classification_id
            == prod.product_tmpl_id.ecotaxe_classification_id
            == cls
        )

    def test_02_single_variant_template(self):
        cls1 = choice([self.ecotax_fixed, self.ecotax_weight])
        cls2 = (self.ecotax_fixed | self.ecotax_weight) - cls1

        # Create a template with 1 variant and ecotax class ``cls1``
        tmpl = self._create_single_variant_template(cls1)
        prod = tmpl.product_variant_ids

        # Change product's ecotax classification to ``cls2``
        with Form(prod, "product.product_normal_form_view") as prod_form:
            prod_form.ecotaxe_classification_id = cls2
        prod = prod_form.save()

        # Check they have different ecotax classifications: template should
        # still have the old classification
        self.assertEqual(tmpl.ecotaxe_classification_id, cls1)
        self.assertEqual(prod.ecotaxe_classification_id, cls2)

    def test_03_multiple_variants_template(self):
        cls1 = choice([self.ecotax_fixed, self.ecotax_weight])
        cls2 = (self.ecotax_fixed | self.ecotax_weight) - cls1

        # Create a template with 3 variants
        tmpl = self._create_multi_variant_template(
            cls1,
            [
                (
                    self.prod_att_1,
                    self.prod_attr1_v1 | self.prod_attr1_v2 | self.prod_attr1_v3,
                )
            ],
        )
        prods = tmpl.product_variant_ids

        # Change a random product's ecotax classification
        with Form(
            choice(prods), "product.product_normal_form_view"
        ) as random_prod_form:
            random_prod_form.ecotaxe_classification_id = cls2
        random_prod = random_prod_form.save()
        other_prods = prods - random_prod

        # Check they have different ecotax classification: template and 2
        # products should still have the old classification, while
        # 3rd product's ecotax class must've changed
        self.assertTrue(
            other_prods.ecotaxe_classification_id
            == tmpl.ecotaxe_classification_id
            == cls1
        )
        self.assertEqual(random_prod.ecotaxe_classification_id, cls2)

    def test_04_prod_ecotaxe_amount(self):
        # Not using random classes here because we need to test amounts, so we
        # need predictable classification behaviours instead of randomness
        fixed_cls, weight_based_cls = self.ecotax_fixed, self.ecotax_weight

        # Create a template with 1 variant
        tmpl = self._create_single_variant_template(fixed_cls)
        prod = tmpl.product_variant_ids

        # Change product's ecotax to "weight-based", set its weight to 100
        weight_based_cls.ecotaxe_coef = 0.2
        prod.weight = 100
        prod.ecotaxe_classification_id = weight_based_cls

        # Change template manual value to 10
        tmpl.manual_fixed_ecotaxe = 10

        # Check ecotax on both
        self.assertEqual(prod.ecotaxe_amount, 20)
        self.assertEqual(tmpl.ecotaxe_amount, 10)

        # Revert back product's classification to "fixed", but set both
        # classification default amount and product manual amount to 0
        prod.manual_fixed_ecotaxe = 0
        fixed_cls.default_fixed_ecotaxe = 0
        prod.ecotaxe_classification_id = fixed_cls

        # Check that product and template have different ecotax amounts
        self.assertEqual(prod.ecotaxe_amount, 0)
        self.assertEqual(tmpl.ecotaxe_amount, 10)

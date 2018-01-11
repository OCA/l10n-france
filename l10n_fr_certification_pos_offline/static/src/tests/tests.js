odoo.define('l10n_fr_certification_pos_offline.Tour', function (require) {
    "use strict";

    var tour = require("web_tour.tour");

    function wait_pos_loading(){
        return [{
            content: 'waiting for loading to finish',
            trigger: '.o_main_content:has(.loader:hidden)',
        }];
    }

    function add_product_to_order(product_name) {
        return [{
            content: 'buy ' + product_name,
            trigger: '.product-list .product-name:contains("' + product_name + '")',
        }];
    }

    function generate_keypad_steps(amount_str, keypad_selector) {
        var steps = [], current_char = '';
        for (var i = 0; i < amount_str.length; ++i) {
            current_char = amount_str[i];
            steps.push({
                content: 'press ' + current_char + ' on payment keypad',
                trigger: keypad_selector + ' .input-button:contains("' + current_char + '"):visible'
            });
        }
        return steps;
    }

    function generate_payment_screen_keypad_steps(amount_str) {
        return generate_keypad_steps(amount_str, '.payment-numpad');
    }

    function goto_payment_screen_and_select_payment_method() {
        return [{
            content: "go to payment screen",
            trigger: '.button.pay',
        }, {
            content: "pay with cash",
            trigger: '.paymentmethod:contains("Cash")',
        }];
    }

    function finish_order() {
        return [{
            content: "validate the order",
            trigger: '.button.next:visible',
        }];
    }

    var steps = [];
    steps = steps.concat(wait_pos_loading());
    steps = steps.concat(add_product_to_order('Peaches'));
    steps = steps.concat(goto_payment_screen_and_select_payment_method());
    steps = steps.concat(generate_payment_screen_keypad_steps("5.10"));
    steps = steps.concat(finish_order());

    steps = steps.concat([{
        content: "verify that the Certification Number is present",
        trigger: '.pos-sale-ticket:contains("Certification Number")',
        run: function () {},
    }]);

    tour.register('l10n_fr_certification_pos_offline', {test: true, url: '/pos/web' }, steps);

});

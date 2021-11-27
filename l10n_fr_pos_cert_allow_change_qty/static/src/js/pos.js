odoo.define("l10n_fr_pos_cert_allow_change_qty.pos", function (require) {
    "use strict";

    var models = require("point_of_sale.models");

    models.PosModel = models.PosModel.extend({
        disallowLineQuantityChange() {
            return false;
        },
    });
});

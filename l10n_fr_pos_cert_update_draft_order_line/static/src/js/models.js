/*
    Copyright (C) 2023 - Today: GRAP (http://www.grap.coop)
    @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
*/

odoo.define("l10n_fr_pos_cert_update_draft_order_line.models", function (require) {
    "use strict";

    const Registries = require("point_of_sale.Registries");

    var {PosGlobalState} = require("point_of_sale.models");

    const OverloadPosGlobalState = (OriginalPosGlobalState) =>
        class extends OriginalPosGlobalState {
            disallowLineQuantityChange() {
                return false;
            }
        };

    Registries.Model.extend(PosGlobalState, OverloadPosGlobalState);

    return PosGlobalState;
});

/*
    Copyright 2026 Moka Tourisme (https://www.mokatourisme.fr/)
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/

import {PosStore} from "@point_of_sale/app/store/pos_store";
import {patch} from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        // The server answers the payment request immediately and talks to the
        // terminal in the background: its answer comes back here.
        this.data.connectWebSocket("FR_CAISSE_AP_IP_RESPONSE", (response) => {
            const method = this.models["pos.payment.method"].find(
                (pm) => pm.use_payment_terminal === "fr-caisse_ap_ip"
            );
            method?.payment_terminal?.handleTerminalResponse(response);
        });
    },
});

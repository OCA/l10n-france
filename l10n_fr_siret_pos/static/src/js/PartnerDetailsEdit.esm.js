/*
    Copyright (C) 2026-Today GRAP (http://www.grap.coop)
    @author Sylvain LE GAL
    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
*/

odoo.define("l10n_fr_siret_pos.PartnerDetailsEdit", function (require) {
    const {useState} = owl;
    const PartnerDetailsEdit = require("point_of_sale.PartnerDetailsEdit");
    const Registries = require("point_of_sale.Registries");

    const PosPartnerDetailsEdit = (OriginalPartnerDetailsEdit) =>
        class extends OriginalPartnerDetailsEdit {
            setup() {
                console.log("PosPartnerDetailsEdit");
                super.setup();
                this.changes = useState({
                    ...this.changes,
                    siren: this.props.partner.siren || null,
                    nic: this.props.partner.nic || null,
                });
            }
        };

    Registries.Component.extend(PartnerDetailsEdit, PosPartnerDetailsEdit);

    return PartnerDetailsEdit;
});

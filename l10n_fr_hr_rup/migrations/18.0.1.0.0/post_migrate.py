# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    cr.execute("""
        UPDATE hr_contract
        SET work_location_id = wl.id
        FROM hr_work_location as wl
        WHERE wl.name = hr_contract.work_location
            AND wl.address_id = hr_contract.address_id
            AND wl.company_id = hr_contract.company_id,
    """)

    #  create missing locations
    cr.execute("""
        INSERT INTO hr_work_location (
            name,
            address_id,
            company_id,
            active,
            create_uid,
            write_uid,
            create_date,
            write_date
        )
        SELECT DISTINCT
            c.work_location,
            COALESCE(e.address_id, comp.partner_id),
            c.company_id,
            TRUE,
            c.create_uid,
            c.write_uid,
            NOW(),
            NOW()
        FROM hr_contract c
        JOIN res_company comp ON c.company_id = comp.id
        LEFT JOIN hr_employee e ON c.employee_id = e.id
        WHERE c.work_location IS NOT NULL
          AND c.work_location != ''
          AND NOT EXISTS (
              SELECT 1 FROM hr_work_location hl
              WHERE hl.name = c.work_location
                AND hl.company_id = c.company_id
                AND hl.address_id = COALESCE(e.address_id, comp.partner_id)
          )
    """)

    cr.execute("""
        UPDATE hr_contract c
        SET work_location_id = hl.id
        FROM hr_employee e
        JOIN res_company comp ON e.company_id = comp.id
        JOIN hr_work_location hl ON hl.name = e.work_location
            AND hl.company_id = e.company_id
            AND hl.address_id = COALESCE(e.address_id, comp.partner_id)
        WHERE c.employee_id = e.id
          AND c.work_location IS NOT NULL
    """)

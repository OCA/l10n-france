from odoo.tests.common import TransactionCase


class TestFrFECBackground(TransactionCase):

    def setUp(self):
        super(TestFrFECBackground, self).setUp()
        self.fec_wizard = self.env['account.fr.fec'].create(
            {'date_from': '2020-01-01', 'date_to': '2020-02-29'})

    def test_001_csv_report_background(self):
        self.fec_wizard.generate_fec_file_in_background('csv', '|')
        jobs = self.env['queue.job'].search(
            [
                ('func_string', 'like', str(self.fec_wizard)),
                ('state', '=', 'pending'),
            ]
        )
        self.assertEquals(len(jobs), 2,
                          "Job for CSV Report is not created in background!")

    def test_002_txt_report_background(self):
        self.fec_wizard.generate_fec_file_in_background('txt', '\t')
        jobs = self.env['queue.job'].search(
            [
                ('func_string', 'like', str(self.fec_wizard)),
                ('state', '=', 'pending'),
            ]
        )
        self.assertEquals(len(jobs), 2,
                          "Job for TXT Report is not created in background!")

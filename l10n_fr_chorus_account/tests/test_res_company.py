# Copyright 2025 Omydoo (https://www.omydoo.fr)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestResCompanyChorus(TransactionCase):
    def test_get_token_expired_clears_cache(self):
        """Test that _get_token clears ormcache when token is expired."""
        company = self.env.company
        fake_token = {
            "access_token": "test_token_123",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid",
        }
        expired_date = datetime.utcnow() - timedelta(seconds=10)
        valid_date = datetime.utcnow() + timedelta(seconds=3600)
        call_count = {"n": 0}

        def mock_get_new_token(self_model, oauth_id, oauth_secret, qualif):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # First call returns expired token
                return (fake_token, expired_date)
            # Second call (after cache clear) returns valid token
            return (fake_token, valid_date)

        api_params = {
            "oauth_id": "test_id",
            "oauth_secret": "test_secret",
            "qualif": False,
        }

        with patch.object(type(company), "_get_new_token", mock_get_new_token):
            token = company._get_token(api_params)

        self.assertEqual(token, fake_token)
        # _get_new_token must have been called twice:
        # once with expired result, then again after cache clear
        self.assertEqual(call_count["n"], 2)

    def test_get_token_valid_no_cache_clear(self):
        """Test that _get_token does not clear cache when token is valid."""
        company = self.env.company
        fake_token = {
            "access_token": "test_token_456",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid",
        }
        valid_date = datetime.utcnow() + timedelta(seconds=3600)

        def mock_get_new_token(self_model, oauth_id, oauth_secret, qualif):
            return (fake_token, valid_date)

        api_params = {
            "oauth_id": "test_id",
            "oauth_secret": "test_secret",
            "qualif": False,
        }

        with patch.object(type(company), "_get_new_token", mock_get_new_token):
            token = company._get_token(api_params)

        self.assertEqual(token, fake_token)

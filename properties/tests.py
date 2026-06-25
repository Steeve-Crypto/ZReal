from decimal import Decimal
from hashlib import sha256
import tempfile
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings

from properties.models import Property, PropertyDocument, PropertyInvestment, TokenizationOperation
from zcash_integration.zcash_client import ZcashClient, ZcashToolOutputError


def make_user(username, role, password="pass"):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password=password)
    user.profile.role = role
    user.profile.save()
    return user


def make_property(owner, **overrides):
    data = {
        "owner": owner,
        "title": "Test Property",
        "address": "123 Test St",
        "latitude": "51.505000",
        "longitude": "-0.090000",
        "size_sqm": 120,
        "estimated_value": Decimal("500000.00"),
        "total_shares": 10000,
    }
    data.update(overrides)
    return Property.objects.create(**data)


class ZcashClientOutputTest(SimpleTestCase):
    def test_invalid_tool_json_fails_safely(self):
        with self.assertRaises(ZcashToolOutputError):
            ZcashClient()._parse_tool_output("not-json")

    def test_confirmed_output_requires_asset_id(self):
        with self.assertRaises(ZcashToolOutputError):
            ZcashClient()._parse_tool_output('{"status":"confirmed","txid":"tx123"}')


class DocumentUploadTest(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media_dir.cleanup)
        self.user = make_user("issuer_docs", "issuer")
        self.property = make_property(self.user)
        self.client = Client()
        self.client.login(username="issuer_docs", password="pass")

    @patch("properties.views.pdfplumber")
    def test_upload_document_view_stores_hash_and_structured_data(self, mock_pdfplumber):
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Owner: Recorded Owner\nSize: 120 sqm\nAddress: Recorded Property Address"
        mock_page.extract_tables.return_value = []
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf

        file_bytes = b"%PDF-1.4 test document"
        uploaded_pdf = SimpleUploadedFile("uploaded_property_document.pdf", file_bytes, content_type="application/pdf")

        response = self.client.post(
            f"/properties/{self.property.pk}/upload-document/",
            {"document": uploaded_pdf, "document_type": "Deed"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("extracted_data", data)

        doc = PropertyDocument.objects.get(id=data["document_id"])
        self.assertEqual(doc.file_sha256, sha256(file_bytes).hexdigest())
        self.assertEqual(doc.processing_status, "completed")

    def test_investor_cannot_upload_document_to_issuer_property(self):
        investor = make_user("investor_docs", "investor")
        self.client.force_login(investor)
        uploaded_pdf = SimpleUploadedFile("uploaded_property_document.pdf", b"%PDF-1.4", content_type="application/pdf")

        response = self.client.post(
            f"/properties/{self.property.pk}/upload-document/",
            {"document": uploaded_pdf, "document_type": "Deed"},
        )

        self.assertEqual(response.status_code, 403)


class ZsaIssuanceViewTest(TestCase):
    def setUp(self):
        self.user = make_user("issuer", "issuer")
        self.property = make_property(self.user, title="Tokenization Test", address="456 Token Ave")
        self.client = Client()
        self.client.login(username="issuer", password="pass")

    @patch("properties.views.ZcashClient")
    def test_successful_mocked_zsa_creates_operation_with_safe_metadata(self, mock_client_class):
        PropertyDocument.objects.create(
            property=self.property,
            file="property_documents/deed.pdf",
            document_type="Deed",
            file_sha256="a" * 64,
            extracted_text="Full legal text must not be copied into tokenization metadata.",
            extracted_data={
                "detected_address": "456 Token Ave",
                "detected_size": "120",
                "detected_owner": "Sensitive Owner Name",
            },
            processing_status="completed",
        )
        mock_client = MagicMock()
        mock_client.issue_zsa.return_value = {
            "status": "confirmed",
            "operation_id": "real-operation-id-from-mock",
            "txid": "real-tool-txid-from-mock",
            "asset_id": "real-tool-asset-id-from-mock",
            "backend": "zcash_tx_tool",
        }
        mock_client_class.return_value = mock_client

        response = self.client.post(
            f"/properties/{self.property.pk}/issue-zsa/",
            {"issuer_zaddr": "ztestsapling1testaddress"},
        )

        self.assertEqual(response.status_code, 302)
        self.property.refresh_from_db()
        operation = TokenizationOperation.objects.get(property=self.property)
        self.assertEqual(operation.status, "confirmed")
        self.assertEqual(operation.asset_id, "real-tool-asset-id-from-mock")
        self.assertEqual(operation.metadata["documents"][0]["file_sha256"], "a" * 64)
        self.assertNotIn("Full legal text", str(operation.metadata))
        self.assertNotIn("Sensitive Owner Name", str(operation.metadata))
        self.assertEqual(self.property.status, "tokenized")
        self.assertEqual(self.property.zcash_txid, "real-tool-txid-from-mock")
        self.assertEqual(self.property.zsa_asset_id, "real-tool-asset-id-from-mock")

    @override_settings(ZCASH_TX_TOOL_PATH="")
    @patch("zcash_integration.zcash_client.shutil.which", return_value=None)
    def test_missing_zsa_configuration_records_failed_operation(self, _which):
        response = self.client.post(
            f"/properties/{self.property.pk}/issue-zsa/",
            {"issuer_zaddr": "ztestsapling1testaddress"},
        )

        self.assertEqual(response.status_code, 302)
        operation = TokenizationOperation.objects.get(property=self.property)
        self.assertEqual(operation.status, "failed")
        self.assertIn("ZCASH_TX_TOOL_PATH", operation.error)
        self.property.refresh_from_db()
        self.assertEqual(self.property.tokenization_status, "failed")

    @patch("properties.views.ZcashClient")
    def test_status_refresh_updates_pending_operation(self, mock_client_class):
        TokenizationOperation.objects.create(
            property=self.property,
            issuer=self.user,
            issuer_zaddr="ztestsapling1testaddress",
            asset_symbol="ZREAL-PROP-1",
            total_shares=10000,
            backend="zcash_tx_tool",
            status="pending",
            operation_id="op-123",
        )
        self.property.tokenization_status = "pending"
        self.property.zcash_operation_id = "op-123"
        self.property.save()

        mock_client = MagicMock()
        mock_client.refresh_zsa_status.return_value = {
            "status": "confirmed",
            "operation_id": "op-123",
            "txid": "tx-123",
            "asset_id": "asset-123",
            "backend": "zcash_tx_tool",
        }
        mock_client_class.return_value = mock_client

        response = self.client.post(f"/properties/{self.property.pk}/refresh-zsa-status/")

        self.assertEqual(response.status_code, 302)
        self.property.refresh_from_db()
        self.assertEqual(self.property.tokenization_status, "confirmed")
        self.assertEqual(self.property.zsa_asset_id, "asset-123")

    def test_investor_cannot_issue_issuer_property(self):
        investor = make_user("investor_issue", "investor")
        self.client.force_login(investor)
        response = self.client.post(
            f"/properties/{self.property.pk}/issue-zsa/",
            {"issuer_zaddr": "ztestsapling1testaddress"},
        )
        self.assertEqual(response.status_code, 403)


class ZsaConfigurationEndpointTest(TestCase):
    def setUp(self):
        self.issuer = make_user("issuer_config", "issuer")
        self.client = Client()
        self.client.login(username="issuer_config", password="pass")

    @override_settings(ZCASH_TX_TOOL_PATH="", ZCASH_RPC_URL="")
    @patch("zcash_integration.zcash_client.shutil.which", return_value=None)
    def test_zsa_configuration_endpoint_reports_missing_state(self, _which):
        response = self.client.get("/zcash/zsa-config/validate/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["ready"])
        self.assertIn("ZCASH_RPC_URL", data["missing"])
        self.assertIn("ZCASH_TX_TOOL_PATH or zcash_tx_tool on PATH", data["missing"])

    def test_zsa_configuration_endpoint_reports_ready_state(self):
        with tempfile.NamedTemporaryFile() as tool, override_settings(
            ZCASH_RPC_URL="http://rpcuser:rpcpassword@127.0.0.1:18232",
            ZCASH_TX_TOOL_PATH=tool.name,
            ZSA_ISSUANCE_BACKEND="zcash_tx_tool",
            ZCASH_NETWORK="testnet",
            ZCASH_ZSA_ISSUE_COMMAND="{tool} create --from {issuer_zaddr} --asset-symbol {asset_symbol} --total-shares {total_shares}",
            ZCASH_ZSA_STATUS_COMMAND="{tool} status --operation-id {operation_id}",
        ):
            response = self.client.get("/zcash/zsa-config/validate/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ready"])
        self.assertEqual(data["missing"], [])
        self.assertTrue(data["tool_path_exists"])

    def test_investor_cannot_validate_zsa_configuration(self):
        investor = make_user("investor_config", "investor")
        self.client.force_login(investor)

        response = self.client.get("/zcash/zsa-config/validate/")

        self.assertEqual(response.status_code, 403)

    @override_settings(ZCASH_TX_TOOL_PATH="", ZCASH_RPC_URL="")
    @patch("zcash_integration.zcash_client.shutil.which", return_value=None)
    def test_issuer_dashboard_shows_missing_zsa_configuration(self, _which):
        response = self.client.get("/issuer/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ZSA Configuration")
        self.assertContains(response, "Not Ready")
        self.assertContains(response, "ZCASH_RPC_URL")


class SetupStatusTest(TestCase):
    def test_setup_status_is_staff_only(self):
        issuer = make_user("issuer_setup", "issuer")
        client = Client()
        client.login(username="issuer_setup", password="pass")

        response = client.get("/setup/status/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_secret_value",
        STRIPE_ISSUER_PRICE_ID="price_secret_value",
        ZCASH_RPC_URL="http://rpcuser:rpcpassword@127.0.0.1:18232",
        ZCASH_TX_TOOL_PATH="C:\\zsa\\zcash_tx_tool.exe",
    )
    def test_setup_status_does_not_leak_secret_values(self):
        staff = make_user("staff_setup", "issuer")
        staff.is_staff = True
        staff.save()
        client = Client()
        client.login(username="staff_setup", password="pass")

        response = client.get("/setup/status/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Local Setup Status")
        self.assertContains(response, "STRIPE_SECRET_KEY and STRIPE_ISSUER_PRICE_ID")
        self.assertNotContains(response, "sk_test_secret_value")
        self.assertNotContains(response, "price_secret_value")
        self.assertNotContains(response, "rpcpassword")


class TokenizationOperationDetailTest(TestCase):
    def test_issuer_can_view_operation_detail_without_raw_response(self):
        issuer = make_user("issuer_operation", "issuer")
        prop = make_property(issuer)
        operation = TokenizationOperation.objects.create(
            property=prop,
            issuer=issuer,
            issuer_zaddr="ztestsapling1testaddress123456789",
            asset_symbol="ZREAL-PROP-1",
            total_shares=10000,
            backend="zcash_tx_tool",
            status="failed",
            operation_id="op-123",
            error="Backend not configured",
            metadata={"schema": "zreal.tokenization.v1"},
            response={"private_debug": "staff only"},
        )
        client = Client()
        client.login(username="issuer_operation", password="pass")

        response = client.get(f"/tokenization/operations/{operation.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "op-123")
        self.assertContains(response, "ztestsap...456789")
        self.assertContains(response, "Backend not configured")
        self.assertNotContains(response, "private_debug")

    def test_other_issuer_cannot_view_operation_detail(self):
        issuer = make_user("issuer_operation_owner", "issuer")
        other = make_user("issuer_operation_other", "issuer")
        prop = make_property(issuer)
        operation = TokenizationOperation.objects.create(
            property=prop,
            issuer=issuer,
            issuer_zaddr="ztestsapling1testaddress123456789",
            asset_symbol="ZREAL-PROP-1",
            total_shares=10000,
            backend="zcash_tx_tool",
            status="pending",
        )
        client = Client()
        client.login(username="issuer_operation_other", password="pass")

        response = client.get(f"/tokenization/operations/{operation.pk}/")

        self.assertEqual(response.status_code, 404)


class InvestorPortfolioTest(TestCase):
    def test_empty_investor_dashboard_shows_empty_state(self):
        investor = make_user("investor_empty", "investor")
        client = Client()
        client.login(username="investor_empty", password="pass")

        response = client.get("/investor/portfolio/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No investments yet.")
        self.assertNotContains(response, "$2.84M")

    def test_investor_dashboard_uses_real_holdings(self):
        issuer = make_user("issuer_holdings", "issuer")
        investor = make_user("investor_holdings", "investor")
        prop = make_property(issuer, title="Real Holding", estimated_value=Decimal("100000.00"), total_shares=100)
        PropertyInvestment.objects.create(investor=investor, property=prop, shares_owned=10)
        client = Client()
        client.login(username="investor_holdings", password="pass")

        response = client.get("/investor/portfolio/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Real Holding")
        self.assertContains(response, "$10,000.00")

    def test_investor_browse_shows_only_tokenized_or_active_properties(self):
        issuer = make_user("issuer_browse", "issuer")
        draft = make_property(issuer, title="Draft Property", status="draft")
        tokenized = make_property(
            issuer,
            title="Tokenized Property",
            status="tokenized",
            tokenization_status="confirmed",
            zsa_asset_id="real-asset-id",
        )

        response = Client().get("/properties/browse/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, tokenized.title)
        self.assertNotContains(response, draft.title)

    def test_investor_browse_empty_state(self):
        response = Client().get("/properties/browse/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No tokenized properties are available yet.")

    def test_public_property_map_hides_draft_properties(self):
        issuer = make_user("issuer_map_public", "issuer")
        draft = make_property(issuer, title="Draft Map Property", status="draft")
        tokenized = make_property(
            issuer,
            title="Tokenized Map Property",
            status="tokenized",
            tokenization_status="confirmed",
            zsa_asset_id="real-map-asset-id",
        )

        response = Client().get("/properties/map/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="property-map"')
        self.assertContains(response, 'id="property-map-data"')
        self.assertContains(response, "leaflet.js")
        self.assertContains(response, "property_map.js")
        self.assertContains(response, "zreal-map-page")
        self.assertContains(response, "glass")
        self.assertContains(response, tokenized.title)
        self.assertNotContains(response, draft.title)

    def test_issuer_property_map_shows_own_draft_property(self):
        issuer = make_user("issuer_map_private", "issuer")
        draft = make_property(issuer, title="Issuer Draft Map Property", status="draft")
        client = Client()
        client.login(username="issuer_map_private", password="pass")

        response = client.get("/properties/map/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, draft.title)
        self.assertContains(response, "Issuer-only draft")

    def test_property_map_empty_state_when_no_public_properties(self):
        response = Client().get("/properties/map/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="property-map"')
        self.assertContains(response, "No tokenized properties are available on the public map yet.")
        self.assertContains(response, "zreal-map-card")

    def test_investor_property_map_hides_draft_properties(self):
        issuer = make_user("issuer_map_for_investor", "issuer")
        investor = make_user("investor_map_private", "investor")
        draft = make_property(issuer, title="Investor Hidden Draft", status="draft")
        client = Client()
        client.login(username="investor_map_private", password="pass")

        response = client.get("/properties/map/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No tokenized properties are available on the public map yet.")
        self.assertNotContains(response, draft.title)


class BillingConfigTest(TestCase):
    @override_settings(STRIPE_SECRET_KEY="", STRIPE_ISSUER_PRICE_ID="")
    def test_missing_stripe_configuration_returns_clear_error(self):
        issuer = make_user("issuer_billing", "issuer")
        client = Client()
        client.login(username="issuer_billing", password="pass")

        response = client.post("/billing/create-checkout-session/")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Stripe is not configured", response.json()["error"])


class ProductApiTest(TestCase):
    def test_issuer_dashboard_api_returns_real_property_metrics(self):
        issuer = make_user("api_issuer_dashboard", "issuer")
        make_property(issuer, title="Issuer API Property", estimated_value=Decimal("250000.00"))
        client = Client()
        client.login(username="api_issuer_dashboard", password="pass")

        response = client.get("/api/dashboard/issuer/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["metrics"]["property_count"], 1)
        self.assertEqual(data["metrics"]["total_estimated_value"], "250000")
        self.assertEqual(data["properties"][0]["title"], "Issuer API Property")

    def test_investor_dashboard_api_returns_real_holdings(self):
        issuer = make_user("api_holdings_issuer", "issuer")
        investor = make_user("api_holdings_investor", "investor")
        prop = make_property(issuer, title="API Holding", estimated_value=Decimal("100000.00"), total_shares=100)
        PropertyInvestment.objects.create(investor=investor, property=prop, shares_owned=25)
        client = Client()
        client.login(username="api_holdings_investor", password="pass")

        response = client.get("/api/dashboard/investor/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["metrics"]["investment_count"], 1)
        self.assertEqual(data["holdings"][0]["property"]["title"], "API Holding")
        self.assertEqual(data["holdings"][0]["estimated_position_value"], "25000.00")

    def test_property_api_hides_drafts_from_public_and_investors(self):
        issuer = make_user("api_visibility_issuer", "issuer")
        investor = make_user("api_visibility_investor", "investor")
        draft = make_property(issuer, title="Hidden API Draft", status="draft")
        tokenized = make_property(issuer, title="Visible API Property", status="tokenized", tokenization_status="confirmed")

        public_response = Client().get("/api/properties/")
        self.assertEqual(public_response.status_code, 200)
        self.assertContains(public_response, tokenized.title)
        self.assertNotContains(public_response, draft.title)

        investor_client = Client()
        investor_client.login(username="api_visibility_investor", password="pass")
        investor_response = investor_client.get("/api/properties/")
        self.assertEqual(investor_response.status_code, 200)
        self.assertContains(investor_response, tokenized.title)
        self.assertNotContains(investor_response, draft.title)

    def test_issuer_property_api_shows_own_drafts(self):
        issuer = make_user("api_own_draft_issuer", "issuer")
        draft = make_property(issuer, title="Issuer API Draft", status="draft")
        client = Client()
        client.login(username="api_own_draft_issuer", password="pass")

        response = client.get("/api/properties/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, draft.title)

    def test_document_api_is_ownership_protected(self):
        issuer = make_user("api_doc_issuer", "issuer")
        other = make_user("api_doc_other", "issuer")
        prop = make_property(issuer)
        client = Client()
        client.login(username="api_doc_other", password="pass")

        response = client.get(f"/api/properties/{prop.pk}/documents/")

        self.assertEqual(response.status_code, 404)

    @override_settings(ZCASH_TX_TOOL_PATH="", ZCASH_RPC_URL="")
    @patch("zcash_integration.zcash_client.shutil.which", return_value=None)
    def test_zsa_config_api_reports_missing_without_secrets(self, _which):
        issuer = make_user("api_zsa_config_issuer", "issuer")
        client = Client()
        client.login(username="api_zsa_config_issuer", password="pass")

        response = client.get("/api/zsa/config/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["ready"])
        self.assertIn("ZCASH_RPC_URL", data["missing"])
        self.assertNotIn("password", str(data).lower())

    @override_settings(ZCASH_TX_TOOL_PATH="", ZCASH_RPC_URL="")
    @patch("zcash_integration.zcash_client.shutil.which", return_value=None)
    def test_tokenization_api_missing_config_records_failed_operation(self, _which):
        issuer = make_user("api_tokenize_issuer", "issuer")
        prop = make_property(issuer)
        client = Client()
        client.login(username="api_tokenize_issuer", password="pass")

        response = client.post(
            f"/api/properties/{prop.pk}/tokenize/",
            data={"issuer_zaddr": "ztestsapling1testaddress"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "failed")
        self.assertIn("ZCASH_TX_TOOL_PATH", data["error"])
        self.assertEqual(TokenizationOperation.objects.filter(property=prop).count(), 1)

    def test_tokenization_operation_api_hides_raw_response_for_non_staff(self):
        issuer = make_user("api_operation_issuer", "issuer")
        prop = make_property(issuer)
        operation = TokenizationOperation.objects.create(
            property=prop,
            issuer=issuer,
            issuer_zaddr="ztestsapling1testaddress123456789",
            asset_symbol="ZREAL-PROP-1",
            total_shares=prop.total_shares,
            backend="zcash_tx_tool",
            status="failed",
            operation_id="op-api-1",
            response={"backend_debug": "staff-only"},
        )
        client = Client()
        client.login(username="api_operation_issuer", password="pass")

        response = client.get(f"/api/tokenization/operations/{operation.pk}/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["operation_id"], "op-api-1")
        self.assertFalse(data["can_view_raw_response"])
        self.assertNotIn("raw_response", data)

    def test_setup_status_api_is_staff_only_and_secret_safe(self):
        staff = make_user("api_setup_staff", "issuer")
        staff.is_staff = True
        staff.save()
        client = Client()
        client.login(username="api_setup_staff", password="pass")

        with override_settings(STRIPE_SECRET_KEY="sk_secret_value"):
            response = client.get("/api/setup/status/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("sk_secret_value", str(response.json()))

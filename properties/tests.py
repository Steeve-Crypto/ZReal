from decimal import Decimal
from hashlib import sha256
import tempfile
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings

from properties.models import Property, PropertyDocument, PropertyEnrichment, PropertyInvestment, TokenizationOperation
from zcash_integration.zcash_client import ZcashClient, ZcashConfigurationError, ZcashToolOutputError


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


def make_completed_document(prop, **overrides):
    data = {
        "property": prop,
        "file": "property_documents/deed.pdf",
        "document_type": "Deed",
        "file_sha256": "a" * 64,
        "extracted_data": {"detected_address": prop.address, "detected_size": str(prop.size_sqm)},
        "processing_status": "completed",
    }
    data.update(overrides)
    return PropertyDocument.objects.create(**data)


class ZcashClientOutputTest(SimpleTestCase):
    def test_invalid_tool_json_fails_safely(self):
        with self.assertRaises(ZcashToolOutputError):
            ZcashClient()._parse_tool_output("not-json")

    def test_confirmed_output_requires_asset_id(self):
        with self.assertRaises(ZcashToolOutputError):
            ZcashClient()._parse_tool_output('{"status":"confirmed","txid":"tx123"}')

    @override_settings(
        ZCASH_RPC_URL="http://rpcuser:super-secret-password@127.0.0.1:18232",
        ZCASH_TX_TOOL_PATH="C:/tools/zcash_tx_tool.exe",
        ZCASH_ZSA_ISSUE_COMMAND="{tool} issue --from {issuer_zaddr} --asset-symbol {asset_symbol} --total-shares {total_shares}",
        ZCASH_ZSA_STATUS_COMMAND="{tool} status --operation-id {operation_id}",
    )
    def test_configuration_report_is_explicit_and_secret_safe(self):
        report = ZcashClient().configuration_report()

        self.assertIn("required", report)
        self.assertIn("optional", report)
        self.assertIn("validation_rules", report)
        self.assertIn("ZCASH_RPC_URL", report["required"])
        self.assertNotIn("super-secret-password", str(report))

    @override_settings(ZCASH_RPC_URL="http://rpcuser:super-secret-password@127.0.0.1:18232")
    def test_safe_error_message_redacts_rpc_secrets(self):
        message = ZcashClient().safe_error_message(RuntimeError("failed http://rpcuser:super-secret-password@127.0.0.1:18232"))

        self.assertNotIn("super-secret-password", message)
        self.assertIn("[redacted]", message)


class HealthEndpointTest(SimpleTestCase):
    def test_health_endpoint_without_trailing_slash_returns_ok(self):
        response = Client().get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_endpoint_with_trailing_slash_returns_ok(self):
        response = Client().get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


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
        make_completed_document(
            self.property,
            extracted_text="Full legal text must not be copied into tokenization metadata.",
            extracted_data={
                "detected_address": "456 Token Ave",
                "detected_size": "120",
                "detected_owner": "Sensitive Owner Name",
            },
        )
        mock_client = MagicMock()
        mock_client.configuration_report.return_value = {
            "ready": True,
            "configured": True,
            "missing": [],
            "warnings": [],
            "backend": "zcash_tx_tool",
            "method": "zcash_tx_tool",
            "safe_display": {},
        }
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
    def test_missing_zsa_configuration_blocks_before_operation(self, _which):
        make_completed_document(self.property)
        response = self.client.post(
            f"/properties/{self.property.pk}/issue-zsa/",
            {"issuer_zaddr": "ztestsapling1testaddress"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(TokenizationOperation.objects.filter(property=self.property).exists())
        self.property.refresh_from_db()
        self.assertEqual(self.property.tokenization_status, "not_started")

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
        self.property.status = "tokenization_pending"
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
        self.assertContains(response, "Setup Required")
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
        self.assertContains(response, "Tokenization setup is incomplete.")
        self.assertNotContains(response, "Backend not configured")
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
        self.assertContains(response, "No holdings yet.")
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
        self.assertIn("Billing is not configured", response.json()["error"])


class ProductApiTest(TestCase):
    def test_csrf_endpoint_returns_token(self):
        response = Client().get("/api/csrf/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrfToken", response.json())

    def test_property_create_api_requires_issuer_and_creates_property(self):
        issuer = make_user("api_create_issuer", "issuer")
        client = Client()
        client.login(username="api_create_issuer", password="pass")

        response = client.post(
            "/api/properties/new/",
            data={
                "title": "API Created Property",
                "description": "",
                "address": "API Address",
                "latitude": "",
                "longitude": "",
                "size_sqm": "100",
                "bedrooms": "",
                "bathrooms": "",
                "estimated_value": "",
                "total_shares": "1000",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["property"]["title"], "API Created Property")
        self.assertEqual(response.json()["notifications"][0]["message"], "Property draft created.")
        self.assertTrue(Property.objects.filter(owner=issuer, title="API Created Property").exists())

    def test_property_can_be_created_with_address_only(self):
        issuer = make_user("api_address_only_issuer", "issuer")
        client = Client()
        client.login(username="api_address_only_issuer", password="pass")

        response = client.post(
            "/api/properties/new/",
            data={"address": "100 Address First Way"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        prop = Property.objects.get(owner=issuer)
        self.assertEqual(prop.address, "100 Address First Way")
        self.assertEqual(prop.title, "100 Address First Way")
        self.assertIsNone(prop.size_sqm)
        self.assertEqual(prop.total_shares, 10000)

    @override_settings(PROPERTY_DATA_PROVIDER="mock", PROPERTY_DATA_ENABLE_LIVE_CALLS=False)
    def test_address_resolution_populates_enrichment_from_mock_provider(self):
        issuer = make_user("api_enrich_issuer", "issuer")
        prop = make_property(issuer, address="1600 Pennsylvania Ave")
        client = Client()
        client.login(username="api_enrich_issuer", password="pass")

        response = client.post(
            f"/api/properties/{prop.pk}/enrich/",
            data={"address": prop.address},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["enrichment"]["status"], "enriched")
        self.assertEqual(data["enrichment"]["provider"], "mock")
        self.assertEqual(data["enrichment"]["latitude"], "38.897700")
        self.assertEqual(data["property"]["enrichment"]["normalized_address"], "1600 Pennsylvania Ave")

    @override_settings(PROPERTY_DATA_PROVIDER="mock", PROPERTY_DATA_ENABLE_LIVE_CALLS=False)
    def test_ambiguous_address_resolution_requires_review(self):
        make_user("api_ambiguous_resolve_issuer", "issuer")
        client = Client()
        client.login(username="api_ambiguous_resolve_issuer", password="pass")

        response = client.post(
            "/api/properties/resolve-address/",
            data={"address": "ambiguous fixture address"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "needs_review")
        self.assertGreater(len(data["candidates"]), 1)

    @override_settings(PROPERTY_DATA_PROVIDER="mock", PROPERTY_DATA_ENABLE_LIVE_CALLS=False)
    def test_low_confidence_match_needs_review_and_blocks_readiness(self):
        issuer = make_user("api_low_conf_issuer", "issuer")
        prop = make_property(issuer, address="ambiguous fixture address")
        make_completed_document(prop)
        client = Client()
        client.login(username="api_low_conf_issuer", password="pass")

        response = client.post(f"/api/properties/{prop.pk}/enrich/", data={}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["enrichment"]["status"], "needs_review")
        readiness = client.get(f"/api/properties/{prop.pk}/readiness/").json()
        self.assertFalse(readiness["ready_for_tokenization"])
        self.assertIn("Autofilled property data must be reviewed and confirmed before tokenization.", readiness["blocking_issues"])

    @override_settings(PROPERTY_DATA_PROVIDER="mock", PROPERTY_DATA_ENABLE_LIVE_CALLS=False)
    @patch("properties.api.ZcashClient")
    def test_confirming_enrichment_updates_readiness_evidence(self, mock_client_class):
        issuer = make_user("api_confirm_enrich_issuer", "issuer")
        prop = make_property(issuer, address="ambiguous fixture address")
        make_completed_document(prop)
        mock_client = MagicMock()
        mock_client.configuration_report.return_value = {
            "ready": True,
            "configured": True,
            "missing": [],
            "warnings": [],
            "backend": "zcash_tx_tool",
            "method": "zcash_tx_tool",
            "safe_display": {},
        }
        mock_client_class.return_value = mock_client
        client = Client()
        client.login(username="api_confirm_enrich_issuer", password="pass")
        client.post(f"/api/properties/{prop.pk}/enrich/", data={}, content_type="application/json")

        response = client.post(f"/api/properties/{prop.pk}/confirm-enrichment/", data={}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        prop.refresh_from_db()
        self.assertEqual(prop.enrichment.status, "enriched")
        self.assertIsNotNone(prop.enrichment.confirmed_at)
        readiness = response.json()["property"]["readiness"]
        self.assertTrue(next(check for check in readiness["checks"] if check["key"] == "property_data_reviewed")["ok"])

    @override_settings(PROPERTY_DATA_PROVIDER="regrid", PROPERTY_DATA_REGRID_API_KEY="", PROPERTY_DATA_ENABLE_LIVE_CALLS=False)
    def test_missing_provider_key_returns_warning_not_crash(self):
        issuer = make_user("api_missing_key_issuer", "issuer")
        prop = make_property(issuer)
        client = Client()
        client.login(username="api_missing_key_issuer", password="pass")

        response = client.post(f"/api/properties/{prop.pk}/enrich/", data={}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["enrichment"]["status"], "failed")
        self.assertEqual(response.json()["enrichment"]["warnings"][0], "Address provider is not configured.")

    @override_settings(PROPERTY_DATA_PROVIDER="unknown_provider", PROPERTY_DATA_ENABLE_LIVE_CALLS=False)
    def test_unsupported_provider_returns_clean_warning_not_crash(self):
        issuer = make_user("api_unsupported_provider_issuer", "issuer")
        prop = make_property(issuer)
        client = Client()
        client.login(username="api_unsupported_provider_issuer", password="pass")

        response = client.post(f"/api/properties/{prop.pk}/enrich/", data={}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["enrichment"]["status"], "failed")
        self.assertEqual(response.json()["enrichment"]["warnings"][0], "Address provider is not supported.")

    @override_settings(PROPERTY_DATA_PROVIDER="census", PROPERTY_DATA_ENABLE_LIVE_CALLS=False)
    @patch("properties.enrichment.urlopen")
    def test_ci_does_not_make_live_external_property_data_calls(self, mock_urlopen):
        issuer = make_user("api_no_live_issuer", "issuer")
        prop = make_property(issuer)
        client = Client()
        client.login(username="api_no_live_issuer", password="pass")

        response = client.post(f"/api/properties/{prop.pk}/enrich/", data={}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["enrichment"]["status"], "failed")
        mock_urlopen.assert_not_called()

    @override_settings(PROPERTY_DATA_PROVIDER="mock", PROPERTY_DATA_ENABLE_LIVE_CALLS=False)
    def test_archived_property_cannot_be_enriched(self):
        issuer = make_user("api_archived_enrich_issuer", "issuer")
        prop = make_property(issuer, status="archived")
        client = Client()
        client.login(username="api_archived_enrich_issuer", password="pass")

        response = client.post(f"/api/properties/{prop.pk}/enrich/", data={}, content_type="application/json")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "invalid_lifecycle_state")
        self.assertFalse(PropertyEnrichment.objects.filter(property=prop).exists())

    @override_settings(PROPERTY_DATA_PROVIDER="mock", PROPERTY_DATA_ENABLE_LIVE_CALLS=False)
    def test_tokenized_active_and_pending_properties_cannot_be_enriched_or_edited(self):
        issuer = make_user("api_locked_enrich_issuer", "issuer")
        client = Client()
        client.login(username="api_locked_enrich_issuer", password="pass")

        for status in ["tokenization_pending", "tokenized", "active"]:
            prop = make_property(issuer, title=f"Locked {status}", status=status)
            enrich_response = client.post(f"/api/properties/{prop.pk}/enrich/", data={}, content_type="application/json")
            edit_response = client.patch(
                f"/api/properties/{prop.pk}/edit/",
                data={"title": "Changed", "address": prop.address},
                content_type="application/json",
            )
            self.assertEqual(enrich_response.status_code, 409)
            self.assertEqual(edit_response.status_code, 409)

    def test_property_edit_api_requires_owner(self):
        issuer = make_user("api_edit_issuer", "issuer")
        other = make_user("api_edit_other", "issuer")
        prop = make_property(issuer, title="Before Edit")
        client = Client()
        client.login(username="api_edit_other", password="pass")

        response = client.patch(
            f"/api/properties/{prop.pk}/edit/",
            data={
                "title": "After Edit",
                "description": prop.description,
                "address": prop.address,
                "latitude": str(prop.latitude),
                "longitude": str(prop.longitude),
                "size_sqm": str(prop.size_sqm),
                "bedrooms": "",
                "bathrooms": "",
                "estimated_value": str(prop.estimated_value),
                "total_shares": str(prop.total_shares),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        prop.refresh_from_db()
        self.assertEqual(prop.title, "Before Edit")

    def test_property_edit_api_updates_owner_property(self):
        issuer = make_user("api_edit_owner", "issuer")
        prop = make_property(issuer, title="Before Owner Edit")
        client = Client()
        client.login(username="api_edit_owner", password="pass")

        response = client.patch(
            f"/api/properties/{prop.pk}/edit/",
            data={
                "title": "After Owner Edit",
                "description": prop.description,
                "address": prop.address,
                "latitude": str(prop.latitude),
                "longitude": str(prop.longitude),
                "size_sqm": str(prop.size_sqm),
                "bedrooms": "",
                "bathrooms": "",
                "estimated_value": str(prop.estimated_value),
                "total_shares": str(prop.total_shares),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        prop.refresh_from_db()
        self.assertEqual(prop.title, "After Owner Edit")
        self.assertEqual(response.json()["property"]["title"], "After Owner Edit")

    @patch("properties.api.pdfplumber")
    def test_document_upload_api_stores_hash_and_safe_metadata(self, mock_pdfplumber):
        media_dir = tempfile.TemporaryDirectory()
        self.addCleanup(media_dir.cleanup)
        issuer = make_user("api_upload_issuer", "issuer")
        prop = make_property(issuer)
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Address: API Upload Address\nSize: 88 sqm\nOwner: Recorded Owner"
        mock_page.extract_tables.return_value = []
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        client = Client()
        client.login(username="api_upload_issuer", password="pass")

        with override_settings(MEDIA_ROOT=media_dir.name):
            uploaded = SimpleUploadedFile("property_upload.pdf", b"%PDF-1.4 api", content_type="application/pdf")
            response = client.post(
                f"/api/properties/{prop.pk}/documents/upload/",
                {"document": uploaded, "document_type": "Title"},
            )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["document"]["document_type"], "Title")
        self.assertEqual(data["document"]["processing_status"], "completed")
        self.assertIn("document_hash", data["document"])
        self.assertIn("detected_address", data["document"]["safe_extracted_metadata"])
        prop.refresh_from_db()
        self.assertIn(prop.status, {"documents_uploaded", "ready_for_review"})

    @patch("properties.api.pdfplumber")
    def test_document_upload_api_failure_returns_safe_message(self, mock_pdfplumber):
        media_dir = tempfile.TemporaryDirectory()
        self.addCleanup(media_dir.cleanup)
        issuer = make_user("api_upload_failure_issuer", "issuer")
        prop = make_property(issuer)
        mock_pdfplumber.open.side_effect = RuntimeError("parser exploded with token super-secret")
        client = Client()
        client.login(username="api_upload_failure_issuer", password="pass")

        with override_settings(MEDIA_ROOT=media_dir.name):
            uploaded = SimpleUploadedFile("property_upload.pdf", b"%PDF-1.4 api", content_type="application/pdf")
            response = client.post(
                f"/api/properties/{prop.pk}/documents/upload/",
                {"document": uploaded, "document_type": "Title"},
            )

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data["error"], "Document processing could not be completed. Please try again or contact support.")
        self.assertNotIn("super-secret", str(data))
        self.assertEqual(data["document"]["processing_status"], "failed")

    @override_settings(ZCASH_TX_TOOL_PATH="", ZCASH_RPC_URL="")
    @patch("zcash_integration.zcash_client.shutil.which", return_value=None)
    def test_property_readiness_api_reports_blockers(self, _which):
        issuer = make_user("api_readiness_issuer", "issuer")
        prop = make_property(issuer, estimated_value=None)
        client = Client()
        client.login(username="api_readiness_issuer", password="pass")

        response = client.get(f"/api/properties/{prop.pk}/readiness/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["ready_for_tokenization"])
        self.assertIn("blocking_issues", data)
        self.assertIn("Tokenization setup is incomplete. Contact an administrator or complete setup before issuance.", data["blocking_issues"])

    def test_archived_property_cannot_be_edited(self):
        issuer = make_user("api_archived_issuer", "issuer")
        prop = make_property(issuer, status="archived")
        client = Client()
        client.login(username="api_archived_issuer", password="pass")

        response = client.patch(
            f"/api/properties/{prop.pk}/edit/",
            data={
                "title": "Archived Edit",
                "description": prop.description,
                "address": prop.address,
                "latitude": str(prop.latitude),
                "longitude": str(prop.longitude),
                "size_sqm": str(prop.size_sqm),
                "bedrooms": "",
                "bathrooms": "",
                "estimated_value": str(prop.estimated_value),
                "total_shares": str(prop.total_shares),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "property_archived")

    def test_property_cannot_activate_before_tokenization(self):
        issuer = make_user("api_activate_blocked_issuer", "issuer")
        prop = make_property(issuer, status="ready_for_tokenization")
        client = Client()
        client.login(username="api_activate_blocked_issuer", password="pass")

        response = client.post(f"/api/properties/{prop.pk}/activate/")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "not_activatable")

    def test_tokenized_property_can_activate(self):
        issuer = make_user("api_activate_issuer", "issuer")
        prop = make_property(issuer, status="tokenized", zsa_asset_id="real-asset-id")
        client = Client()
        client.login(username="api_activate_issuer", password="pass")

        response = client.post(f"/api/properties/{prop.pk}/activate/")

        self.assertEqual(response.status_code, 200)
        prop.refresh_from_db()
        self.assertEqual(prop.status, "active")
        self.assertEqual(response.json()["property"]["status"], "active")

    def test_notifications_are_session_backed_and_drainable(self):
        issuer = make_user("api_notify_issuer", "issuer")
        client = Client()
        client.login(username="api_notify_issuer", password="pass")

        create_response = client.post(
            "/api/properties/new/",
            data={
                "title": "Notification Property",
                "description": "",
                "address": "Notify Address",
                "latitude": "",
                "longitude": "",
                "size_sqm": "100",
                "bedrooms": "",
                "bathrooms": "",
                "estimated_value": "",
                "total_shares": "1000",
            },
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)

        drain_response = client.get("/api/notifications/")
        self.assertEqual(drain_response.status_code, 200)
        self.assertEqual(drain_response.json()["notifications"][0]["message"], "Property draft created.")
        second_drain = client.get("/api/notifications/")
        self.assertEqual(second_drain.json()["notifications"], [])

    def test_property_detail_includes_tokenization_history(self):
        issuer = make_user("api_history_issuer", "issuer")
        prop = make_property(issuer)
        TokenizationOperation.objects.create(
            property=prop,
            issuer=issuer,
            issuer_zaddr="ztestsapling1testaddress123456789",
            asset_symbol="ZREAL-PROP-HISTORY",
            total_shares=prop.total_shares,
            backend="zcash_tx_tool",
            status="failed",
            error="backend unavailable",
        )
        client = Client()
        client.login(username="api_history_issuer", password="pass")

        response = client.get(f"/api/properties/{prop.pk}/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["tokenization_operations"][0]["status"], "failed")
        self.assertEqual(data["latest_tokenization_operation"]["status"], "failed")

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
        self.assertIn("action_groups", data)

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
        self.assertNotIn("rpcpassword", str(data).lower())
        self.assertNotIn("super-secret", str(data).lower())

    @override_settings(ZCASH_TX_TOOL_PATH="", ZCASH_RPC_URL="")
    @patch("zcash_integration.zcash_client.shutil.which", return_value=None)
    def test_tokenization_api_missing_config_blocks_without_operation(self, _which):
        issuer = make_user("api_tokenize_issuer", "issuer")
        prop = make_property(issuer)
        make_completed_document(prop)
        client = Client()
        client.login(username="api_tokenize_issuer", password="pass")

        response = client.post(
            f"/api/properties/{prop.pk}/tokenize/",
            data={"issuer_zaddr": "ztestsapling1testaddress"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        data = response.json()
        self.assertEqual(data["code"], "not_ready_for_tokenization")
        self.assertFalse(data["readiness"]["ready_for_tokenization"])
        self.assertEqual(TokenizationOperation.objects.filter(property=prop).count(), 0)

    @patch("properties.api.ZcashClient")
    def test_tokenization_api_invalid_config_blocks_without_operation(self, mock_client_class):
        issuer = make_user("api_tokenize_invalid_issuer", "issuer")
        prop = make_property(issuer)
        make_completed_document(prop)
        mock_client = MagicMock()
        mock_client.configuration_report.return_value = {
            "ready": True,
            "configured": True,
            "missing": [],
            "warnings": [],
            "backend": "zcash_tx_tool",
            "method": "zcash_tx_tool",
            "safe_display": {},
        }
        mock_client.validate_issue_configuration.side_effect = ZcashConfigurationError(
            "RPC failure with password=super-secret"
        )
        mock_client.safe_error_message.side_effect = lambda exc: str(exc).replace("super-secret", "[redacted]")
        mock_client_class.return_value = mock_client
        client = Client()
        client.login(username="api_tokenize_invalid_issuer", password="pass")

        response = client.post(
            f"/api/properties/{prop.pk}/tokenize/",
            data={"issuer_zaddr": "ztestsapling1testaddress"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        data = response.json()
        self.assertEqual(data["code"], "invalid_zsa_configuration")
        self.assertIsNone(data["operation"])
        self.assertNotIn("super-secret", str(data))
        self.assertEqual(TokenizationOperation.objects.filter(property=prop).count(), 0)

    @patch("properties.api.ZcashClient")
    def test_successful_mocked_tokenization_api_returns_operation(self, mock_client_class):
        issuer = make_user("api_tokenize_success_issuer", "issuer")
        prop = make_property(issuer)
        make_completed_document(prop)
        mock_client = MagicMock()
        mock_client.configuration_report.return_value = {
            "ready": True,
            "configured": True,
            "missing": [],
            "warnings": [],
            "backend": "zcash_tx_tool",
            "method": "zcash_tx_tool",
            "safe_display": {},
        }
        mock_client.issue_zsa.return_value = {
            "status": "confirmed",
            "operation_id": "real-api-operation",
            "txid": "real-api-txid",
            "asset_id": "real-api-asset",
            "backend": "zcash_tx_tool",
        }
        mock_client_class.return_value = mock_client
        client = Client()
        client.login(username="api_tokenize_success_issuer", password="pass")

        response = client.post(
            f"/api/properties/{prop.pk}/tokenize/",
            data={"issuer_zaddr": "ztestsapling1testaddress"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["operation"]["status"], "confirmed")
        self.assertEqual(data["operation"]["operation_id"], "real-api-operation")
        self.assertEqual(data["operation"]["asset_id"], "real-api-asset")
        prop.refresh_from_db()
        self.assertEqual(prop.status, "tokenized")

    @patch("properties.api.ZcashClient")
    def test_pending_tokenization_does_not_mark_property_tokenized(self, mock_client_class):
        issuer = make_user("api_tokenize_pending_issuer", "issuer")
        prop = make_property(issuer)
        make_completed_document(prop)
        mock_client = MagicMock()
        mock_client.configuration_report.return_value = {
            "ready": True,
            "configured": True,
            "missing": [],
            "warnings": [],
            "backend": "zcash_tx_tool",
            "method": "zcash_tx_tool",
            "safe_display": {},
        }
        mock_client.issue_zsa.return_value = {
            "status": "pending",
            "operation_id": "real-pending-operation",
            "backend": "zcash_tx_tool",
        }
        mock_client_class.return_value = mock_client
        client = Client()
        client.login(username="api_tokenize_pending_issuer", password="pass")

        response = client.post(
            f"/api/properties/{prop.pk}/tokenize/",
            data={"issuer_zaddr": "ztestsapling1testaddress"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        prop.refresh_from_db()
        operation = TokenizationOperation.objects.get(property=prop)
        self.assertEqual(operation.status, "pending")
        self.assertEqual(prop.status, "tokenization_pending")
        self.assertFalse(prop.zsa_asset_id)
        self.assertIsNone(prop.tokenized_at)

    @patch("properties.api.ZcashClient")
    def test_tool_runtime_failure_records_failed_operation_safely(self, mock_client_class):
        issuer = make_user("api_tokenize_fail_issuer", "issuer")
        prop = make_property(issuer)
        make_completed_document(prop)
        mock_client = MagicMock()
        mock_client.configuration_report.return_value = {
            "ready": True,
            "configured": True,
            "missing": [],
            "warnings": [],
            "backend": "zcash_tx_tool",
            "method": "zcash_tx_tool",
            "safe_display": {},
        }
        mock_client.issue_zsa.side_effect = RuntimeError("tool failed with token super-secret")
        mock_client.safe_error_message.side_effect = lambda exc: str(exc).replace("super-secret", "[redacted]")
        mock_client_class.return_value = mock_client
        client = Client()
        client.login(username="api_tokenize_fail_issuer", password="pass")

        response = client.post(
            f"/api/properties/{prop.pk}/tokenize/",
            data={"issuer_zaddr": "ztestsapling1testaddress"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("super-secret", str(response.json()))
        operation = TokenizationOperation.objects.get(property=prop)
        self.assertEqual(operation.status, "failed")
        self.assertNotIn("super-secret", operation.error)
        prop.refresh_from_db()
        self.assertEqual(prop.status, "ready_for_tokenization")
        self.assertEqual(prop.tokenization_status, "failed")

    def test_repeated_tokenization_blocked_in_forbidden_states(self):
        issuer = make_user("api_tokenize_repeat_issuer", "issuer")
        client = Client()
        client.login(username="api_tokenize_repeat_issuer", password="pass")

        for status in ["tokenization_pending", "tokenized", "active", "suspended", "archived"]:
            prop = make_property(issuer, title=f"Blocked {status}", status=status)
            make_completed_document(prop)
            response = client.post(
                f"/api/properties/{prop.pk}/tokenize/",
                data={"issuer_zaddr": "ztestsapling1testaddress"},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()["code"], "invalid_lifecycle_state")
            self.assertFalse(TokenizationOperation.objects.filter(property=prop).exists())

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

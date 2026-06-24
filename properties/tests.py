"""
Basic critical tests for ZReal.

Run with:
    python manage.py test properties
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone
from io import StringIO
from unittest.mock import patch, MagicMock

from properties.models import Property, PropertyDocument, ZSAConfig


class ZSAConfigTest(TestCase):
    """Test ZSAConfig model and strategy switching."""

    def test_get_current_strategy_creates_default(self):
        """Should create default config on first access."""
        self.assertEqual(ZSAConfig.objects.count(), 0)
        strategy = ZSAConfig.get_current_strategy()
        self.assertEqual(strategy, 'auto')
        self.assertEqual(ZSAConfig.objects.count(), 1)

    def test_strategy_change(self):
        """Admin can change strategy."""
        config = ZSAConfig.objects.create(strategy='rich_memo')
        self.assertEqual(ZSAConfig.get_current_strategy(), 'rich_memo')

        config.strategy = 'zcash_tx_tool'
        config.save()
        self.assertEqual(ZSAConfig.get_current_strategy(), 'zcash_tx_tool')


class ReprocessZsaMetadataCommandTest(TestCase):
    """Test the management command."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.property = Property.objects.create(
            owner=self.user,
            title="Test Property",
            address="123 Test St",
            zsa_asset_id="test-txid-123",
            status='tokenized'
        )

    def test_command_dry_run(self):
        """Dry run should not modify data."""
        out = StringIO()
        call_command('reprocess_zsa_metadata', '--dry-run', stdout=out)
        output = out.getvalue()
        self.assertIn('Would update', output)
        # Property should still have empty zsa_issuance_method
        self.property.refresh_from_db()
        self.assertEqual(self.property.zsa_issuance_method, '')

    def test_command_updates_property(self):
        """Normal run should populate new fields."""
        out = StringIO()
        call_command('reprocess_zsa_metadata', stdout=out)
        self.property.refresh_from_db()
        self.assertEqual(self.property.zsa_issuance_method, 'rich_memo')
        self.assertIsNotNone(self.property.zsa_issued_at)


class DocumentUploadTest(TestCase):
    """Basic test for Legal Shield document processing."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.property = Property.objects.create(
            owner=self.user,
            title="Test Property",
            address="123 Test St"
        )
        self.client = Client()
        self.client.login(username='testuser', password='pass')

    @patch('properties.views.pdfplumber')
    def test_upload_document_view(self, mock_pdfplumber):
        """Should process upload and return structured data."""
        # Mock pdfplumber behavior
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Owner: John Doe\nSize: 120 sqm\nAddress: 123 Main St"
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf

        # Create a fake PDF file
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_pdf = SimpleUploadedFile(
            "test_deed.pdf",
            b"%PDF-1.4 fake content",
            content_type="application/pdf"
        )

        response = self.client.post(
            f'/properties/{self.property.pk}/upload-document/',
            {
                'document': fake_pdf,
                'document_type': 'Deed'
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('extracted_data', data)


class ZsaIssuanceViewTest(TestCase):
    """Basic test for ZSA issuance endpoint (with mocking)."""

    def setUp(self):
        self.user = User.objects.create_user(username='issuer', password='pass')
        self.property = Property.objects.create(
            owner=self.user,
            title="Tokenization Test",
            address="456 Token Ave",
            total_shares=10000
        )
        self.client = Client()
        self.client.login(username='issuer', password='pass')

    @patch('properties.views.ZcashClient')
    def test_issue_zsa_view(self, mock_client_class):
        """Should call ZcashClient and update property."""
        mock_client = MagicMock()
        mock_client.create_zsa_issuance_tx.return_value = {
            "success": True,
            "txid": "mock-zsa-tx-98765",
            "issuance_method": "rich_memo",
            "memo_data": {"action": "zsa_issuance", "property_id": self.property.pk},
        }
        mock_client_class.return_value = mock_client

        response = self.client.post(
            f'/properties/{self.property.pk}/issue-zsa/',
            {'issuer_zaddr': 'ztestsapling1testaddress'}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('property_updated'))
        self.assertEqual(data.get('stored_zsa_method'), 'rich_memo')

        self.property.refresh_from_db()
        self.assertEqual(self.property.status, 'tokenizing')
        self.assertEqual(self.property.zsa_asset_id, 'mock-zsa-tx-98765')
        self.assertEqual(self.property.zsa_issuance_method, 'rich_memo')

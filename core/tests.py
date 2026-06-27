from django.contrib.auth.models import User
from django.test import Client, TestCase
from pathlib import Path


class AuthTemplateTest(TestCase):
    def test_login_renders_zreal_auth_ui_without_default_allauth_menu(self):
        response = Client().get("/accounts/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "auth-card")
        self.assertContains(response, "ZReal")
        self.assertContains(response, "Return to ZReal")
        self.assertNotContains(response, "Django session")
        self.assertNotContains(response, "product frontend")
        self.assertNotContains(response, "Menu:")
        self.assertNotContains(response, "<li><a href=\"/accounts/login/\">Sign In</a></li>", html=True)

    def test_customer_frontend_source_avoids_internal_copy(self):
        project_root = Path(__file__).resolve().parents[1]
        files = list((project_root / "frontend" / "app").rglob("*.tsx"))
        files.extend((project_root / "frontend" / "components").rglob("*.tsx"))
        denied = [
            "Django login",
            "Django session",
            "Django backend",
            "backend is not configured",
            "Database-backed",
            "No fake",
            "fake txids",
            "activity feed filler",
            "product frontend",
            "through the API",
            "JSON.stringify(err.data)",
            "Login URL:",
        ]
        allowed_files = {
            project_root / "frontend" / "app" / "setup" / "status" / "page.tsx",
        }
        violations = []
        for path in files:
            if path in allowed_files:
                continue
            text = path.read_text(encoding="utf-8")
            for phrase in denied:
                if phrase in text:
                    violations.append(f"{path.relative_to(project_root)}: {phrase}")
        self.assertEqual(violations, [])

    def test_signup_renders_zreal_auth_ui_without_default_allauth_menu(self):
        response = Client().get("/accounts/signup/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "auth-card")
        self.assertContains(response, "Create your account")
        self.assertNotContains(response, "Menu:")

    def test_setup_status_page_requires_staff(self):
        client = Client()
        User.objects.create_user(username="setup_nonstaff", email="setup_nonstaff@example.com", password="pass")
        client.login(username="setup_nonstaff", password="pass")

        response = client.get("/setup/status/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_login_preserves_next_parameter(self):
        response = Client().get("/accounts/login/?next=/issuer/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="next" value="/issuer/dashboard/"')

    def test_unauthenticated_dashboard_redirects_to_styled_login_with_next(self):
        response = Client().get("/dashboard/")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/accounts/login/"))
        self.assertIn("next=/dashboard/", response["Location"])

    def test_password_reset_renders_zreal_auth_ui(self):
        response = Client().get("/accounts/password/reset/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "auth-card")
        self.assertContains(response, "Reset password")
        self.assertNotContains(response, "Menu:")

    def test_logout_renders_zreal_auth_ui(self):
        client = Client()
        User.objects.create_user(username="auth_logout", email="auth_logout@example.com", password="pass")
        client.login(username="auth_logout", password="pass")

        response = client.get("/accounts/logout/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "auth-card")
        self.assertContains(response, "Sign out")
        self.assertNotContains(response, "Menu:")

from django.test import TestCase


class LoginSmokeTest(TestCase):
    def test_login_page_loads(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)

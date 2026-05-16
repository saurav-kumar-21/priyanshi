from django.test import Client, TestCase, override_settings


class DynamicCSRFMiddlewareTests(TestCase):
    @override_settings(DEBUG=True, ALLOW_DYNAMIC_CSRF_ORIGINS=True)
    def test_admin_login_allows_local_preview_origin_with_random_port(self):
        client = Client(
            enforce_csrf_checks=True,
            HTTP_HOST='localhost:8000',
            HTTP_ORIGIN='http://127.0.0.1:65401',
        )

        login_page = client.get('/admin-panel/login/')
        self.assertEqual(login_page.status_code, 200)
        self.assertIn('csrftoken', login_page.cookies)

        response = client.post(
            '/admin-panel/login/',
            {
                'email': 'preview@example.com',
                'password': 'not-the-right-password',
                'csrfmiddlewaretoken': login_page.cookies['csrftoken'].value,
            },
            HTTP_REFERER='http://localhost:8000/admin-panel/login/',
        )

        self.assertEqual(response.status_code, 200)

# tests/test_basic.py

import unittest

from base import BaseTestCase
from application import app


class FlaskTestCase(BaseTestCase):

        # Ensure that Flask was set up correctly
    def test_index(self):
        tester = app.test_client(self)
        response = tester.get('/', content_type='html/text')
        self.assertEqual(response.status_code, 200)

    # Ensure that the login page loads correctly
    # def test_mode_page_loads(self):
    #     tester = app.test_client(self)
    #     response = tester.get('/modes', follow_redirects=True)
    #     self.assertIn(b'Please log in', response.data)

        # Ensure that the login page loads correctly
    # def test_login_page_loads(self):
    #     response = self.client.get('/login')
    #     self.assertIn(b'Please login', response.data)

        # Ensure login behaves correctly with incorrect credentials
    # def test_incorrect_login(self):
    #     response = self.client.post(
    #         '/login',
    #         data=dict(username="wrong", password="wrong"),
    #         follow_redirects=True
    #     )
    #     self.assertIn(b'Invalid username or password.', response.data)


if __name__ == '__main__':
    unittest.main()

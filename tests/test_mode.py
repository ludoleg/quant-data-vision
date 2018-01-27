# tests/test_blog.py

import unittest

from base import BaseTestCase


class ModeTests(BaseTestCase):
    # Ensure a logged in user can add a new post
    def test_mode(self):
        with self.client:
            response = self.client.post(
                '/modes',
                follow_redirects=True
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Please login', response.data)

    def test_user_is_redirected(self):
        with self.client:
            response = self.client.post(
                '/login',
                data=dict(username="user2", password="user2"),
                follow_redirects=True
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'No mode available',
                          response.data)

    def test_user_can_see_mode(self):
        with self.client:
            self.client.post(
                '/login',
                data=dict(username="user1", password="user1"),
                follow_redirects=True
            )
            response = self.client.post(
                '/modes',
                follow_redirects=True
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Analysis Modes',
                          response.data)

    def test_user_can_create_mode(self):
        with self.client:
            self.client.post(
                '/login',
                data=dict(username="user1", password="user1"),
                follow_redirects=True
            )
            response = self.client.get(
                '/modes/create')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Create Mode',
                          response.data)

    def test_no_mode(self):
        with self.client:
            self.client.post(
                '/login',
                data=dict(username="user2", password="user2"),
                follow_redirects=True
            )
            response = self.client.get(
                '/')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'No mode available',
                          response.data)


if __name__ == '__main__':
    unittest.main()

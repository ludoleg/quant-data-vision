# tests/test_blog.py

import unittest

from base import BaseTestCase
from StringIO import StringIO


class ModeTests(BaseTestCase):
    # Ensure a logged in user can add a new post
    def test_mode(self):
        with self.client:
            response = self.client.post(
                '/modes',
                follow_redirects=True
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Sign in', response.data)

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

    def test_user_anonymous(self):
        data = {}
        with open('Cumberland2.csv', 'rb') as f:
            data['rockdatafile'] = (f, f.name)
            with self.client:
                response = self.client.post(
                    '/process', buffered=True,
                    content_type='multipart/form-data',
                    data=data, follow_redirects=True
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Cumberland2', response.data)
                self.assertIn(b'AMCSD', response.data)
                self.assertIn(b'Database: rockforming', response.data)

    def test_process_logged(self):
        data = {}
        with open('Cumberland2.csv', 'rb') as f:
            data['rockdatafile'] = (f, f.name)
            with self.client:
                self.client.post(
                    '/login',
                    data=dict(username="user1", password="user1"),
                    follow_redirects=True
                )
                response = self.client.post(
                    '/process', buffered=True,
                    content_type='multipart/form-data',
                    data=data, follow_redirects=True
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Cumberland2', response.data)
                self.assertIn(b'AMCSD', response.data)
                self.assertIn(b'Database: pigment', response.data)

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

    def test_user_active_mode(self):
        with self.client:
            self.client.post(
                '/login',
                data=dict(username="user1", password="user1"),
                follow_redirects=True
            )
            response = self.client.get(
                '/activeMode')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Active Mode',
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

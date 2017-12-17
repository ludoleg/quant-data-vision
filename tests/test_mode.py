# tests/test_blog.py

import unittest

from base import BaseTestCase


class ModeCreationTests(BaseTestCase):

    # Ensure a logged in user can add a new post
    def test_user_can_post_mode(self):
        with self.client:
            response = self.client.post(
                '/modes',
                data=dict(username="admin", password="admin"),
                follow_redirects=True
            )
            self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()

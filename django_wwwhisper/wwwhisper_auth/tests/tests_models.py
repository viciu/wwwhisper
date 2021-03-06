# coding=utf-8

# wwwhisper - web access control.
# Copyright (C) 2012 Jan Wrobel <wrr@mixedbit.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.forms import ValidationError
from django.test import TestCase
from wwwhisper_auth import models
from wwwhisper_auth.models import CreationException

FAKE_UUID = '41be0192-0fcc-4a9c-935d-69243b75533c'
TEST_USER_EMAIL = 'foo@bar.com'
TEST_LOCATION = '/pub/kika'

class CollectionTestCase(TestCase):
    def setUp(self):
        self.locations_collection = models.LocationsCollection()
        self.users_collection = models.UsersCollection()

class UsersCollectionTest(CollectionTestCase):
    def test_create_user(self):
        user = self.users_collection.create_item(TEST_USER_EMAIL)
        self.assertTrue(TEST_USER_EMAIL, user.email)

    def test_find_user(self):
        user1 = self.users_collection.create_item(TEST_USER_EMAIL)
        user2 = self.users_collection.find_item(user1.uuid)
        self.assertIsNotNone(user2)
        self.assertEqual(user1, user2)

    def test_find_user_by_email(self):
        self.assertIsNone(
            self.users_collection.find_item_by_email(TEST_USER_EMAIL))
        user1 = self.users_collection.create_item(TEST_USER_EMAIL)
        user2 = self.users_collection.find_item_by_email(TEST_USER_EMAIL)
        self.assertIsNotNone(user2)
        self.assertEqual(user1, user2)

    def test_find_user_by_email_is_case_insensitive(self):
        user1 = self.users_collection.create_item('foo@bar.com')
        user2 = self.users_collection.find_item_by_email('FOo@bar.com')
        self.assertIsNotNone(user2)
        self.assertEqual(user1, user2)

    def test_delete_user(self):
        user = self.users_collection.create_item(TEST_USER_EMAIL)
        self.assertIsNotNone(self.users_collection.find_item(user.uuid))
        self.assertTrue(self.users_collection.delete_item(user.uuid))
        self.assertIsNone(self.users_collection.find_item(user.uuid))

    def test_create_user_twice(self):
        self.users_collection.create_item(TEST_USER_EMAIL)
        self.assertRaisesRegexp(CreationException,
                                'User already exists',
                                self.users_collection.create_item,
                                TEST_USER_EMAIL)

        # Make sure user lookup is case insensitive.
        self.users_collection.create_item('uSeR@bar.com')
        self.assertRaisesRegexp(CreationException,
                                'User already exists',
                                self.users_collection.create_item,
                                'UsEr@bar.com')

    def test_delete_user_twice(self):
        user = self.users_collection.create_item(TEST_USER_EMAIL)
        self.assertTrue(self.users_collection.delete_item(user.uuid))
        self.assertFalse(self.users_collection.delete_item(user.uuid))

    def test_get_all_users(self):
        user1 = self.users_collection.create_item('foo@example.com')
        user2 = self.users_collection.create_item('bar@example.com')
        self.assertItemsEqual(['foo@example.com', 'bar@example.com'],
                              [u.email for u in self.users_collection.all()])
        self.users_collection.delete_item(user1.uuid)
        self.assertItemsEqual(['bar@example.com'],
                              [u.email for u in self.users_collection.all()])

    def test_get_all_users_when_empty(self):
        self.assertListEqual([], list(self.users_collection.all()))


    def test_email_validation(self):
        """Test strings taken from BrowserId tests."""
        self.assertIsNotNone(self.users_collection.create_item('x@y.z'))
        self.assertIsNotNone(self.users_collection.create_item('x@y.z.w'))
        self.assertIsNotNone(self.users_collection.create_item('x.v@y.z.w'))
        self.assertIsNotNone(self.users_collection.create_item('x_v@y.z.w'))

        self.assertRaisesRegexp(CreationException,
                                'Invalid email format',
                                self.users_collection.create_item,
                                'x')
        self.assertRaisesRegexp(CreationException,
                                'Invalid email format',
                                self.users_collection.create_item,
                                'x@y')
        self.assertRaisesRegexp(CreationException,
                                'Invalid email format',
                                self.users_collection.create_item,
                                '@y.z')
        self.assertRaisesRegexp(CreationException,
                                'Invalid email format',
                                self.users_collection.create_item,
                                'z@y.z@y.z')
        self.assertRaisesRegexp(CreationException,
                                'Invalid email format',
                                self.users_collection.create_item,
                                '')

    def test_email_normalization(self):
        self.assertEqual('x@y.z',
                         self.users_collection.create_item('x@y.z').email)

        self.assertEqual('abc@y.z',
                         self.users_collection.create_item('aBc@y.z').email)

class LocationsCollectionTest(CollectionTestCase):
    def test_create_location(self):
        location = self.locations_collection.create_item(TEST_LOCATION)
        self.assertTrue(TEST_LOCATION, location.path)

    def test_find_location(self):
        location1 = self.locations_collection.create_item(TEST_LOCATION)
        location2 = self.locations_collection.find_item(location1.uuid)
        self.assertIsNotNone(location2)
        self.assertEqual(location1.path, location2.path)
        self.assertEqual(location1.uuid, location2.uuid)

    def test_delete_location(self):
        location = self.locations_collection.create_item(TEST_LOCATION)
        self.assertIsNotNone(self.locations_collection.find_item(location.uuid))
        self.assertTrue(self.locations_collection.delete_item(location.uuid))
        self.assertIsNone(self.locations_collection.find_item(location.uuid))

    def test_create_location_twice(self):
        self.locations_collection.create_item(TEST_LOCATION)
        self.assertRaisesRegexp(CreationException,
                                'Location already exists',
                                self.locations_collection.create_item,
                                TEST_LOCATION)

    def test_delete_location_twice(self):
        location = self.locations_collection.create_item(TEST_LOCATION)
        self.assertTrue(self.locations_collection.delete_item(location.uuid))
        self.assertFalse(self.locations_collection.delete_item(location.uuid))

    def test_get_all_locations(self):
        location1 = self.locations_collection.create_item('/foo')
        location2 = self.locations_collection.create_item('/foo/bar')
        self.assertItemsEqual(['/foo/bar', '/foo'],
                              [l.path for l
                               in self.locations_collection.all()])
        self.locations_collection.delete_item(location1.uuid)
        self.assertItemsEqual(['/foo/bar'],
                              [l.path for l
                               in self.locations_collection.all()])

    def test_get_all_locations_when_empty(self):
        self.assertListEqual([], list(self.locations_collection.all()))

    def test_grant_access(self):
        user = self.users_collection.create_item(TEST_USER_EMAIL)
        location = self.locations_collection.create_item(TEST_LOCATION)
        self.assertFalse(location.can_access(user.uuid))
        (perm, created) = location.grant_access(user.uuid)
        self.assertTrue(created)
        self.assertIsNotNone(perm)
        self.assertTrue(location.can_access(user.uuid))

    def test_grant_access_for_not_existing_user(self):
        location = self.locations_collection.create_item(TEST_LOCATION)
        self.assertRaisesRegexp(LookupError,
                                'User not found',
                                location.grant_access,
                                FAKE_UUID)

    def test_grant_access_if_already_granted(self):
        location = self.locations_collection.create_item(TEST_LOCATION)
        user = self.users_collection.create_item(TEST_USER_EMAIL)
        (permission1, created1) = location.grant_access(user.uuid)
        self.assertTrue(created1)
        (permission2, created2) = location.grant_access(user.uuid)
        self.assertFalse(created2)
        self.assertEqual(permission1, permission2)
        self.assertEqual(TEST_USER_EMAIL, permission1.user.email)
        self.assertTrue(location.can_access(user.uuid))

    def test_grant_access_to_deleted_location(self):
        user = self.users_collection.create_item(TEST_USER_EMAIL)
        location = self.locations_collection.create_item(TEST_LOCATION)
        self.assertTrue(self.locations_collection.delete_item(location.uuid))
        self.assertRaises(ValidationError,
                          location.grant_access,
                          user.uuid)

    def test_revoke_access(self):
        user = self.users_collection.create_item(TEST_USER_EMAIL)
        location = self.locations_collection.create_item(TEST_LOCATION)
        location.grant_access(user.uuid)
        self.assertTrue(location.can_access(user.uuid))
        location.revoke_access(user.uuid)
        self.assertFalse(location.can_access(user.uuid))

    def test_revoke_not_granted_access(self):
        location = self.locations_collection.create_item(TEST_LOCATION)
        user = self.users_collection.create_item(TEST_USER_EMAIL)
        self.assertRaisesRegexp(LookupError,
                                'User can not access location.',
                                location.revoke_access,
                                user.uuid)

    def test_revoke_access_to_deleted_location(self):
        user = self.users_collection.create_item(TEST_USER_EMAIL)
        location = self.locations_collection.create_item(TEST_LOCATION)
        location.grant_access(user.uuid)
        self.assertTrue(self.locations_collection.delete_item(location.uuid))
        self.assertRaisesRegexp(LookupError,
                                'User can not access location.',
                                location.revoke_access,
                                user.uuid)

    def test_deleting_user_revokes_access(self):
        user = self.users_collection.create_item(TEST_USER_EMAIL)
        location = self.locations_collection.create_item(TEST_LOCATION)
        self.assertFalse(location.can_access(user.uuid))
        location.grant_access(user.uuid)
        self.assertTrue(location.can_access(user.uuid))
        self.users_collection.delete_item(user.uuid)
        self.assertFalse(location.can_access(user.uuid))

    def test_deleting_location_revokes_access(self):
        user = self.users_collection.create_item(TEST_USER_EMAIL)
        location = self.locations_collection.create_item(TEST_LOCATION)
        self.assertFalse(location.can_access(user.uuid))
        location.grant_access(user.uuid)
        self.assertTrue(location.can_access(user.uuid))
        self.locations_collection.delete_item(location.uuid)
        self.assertFalse(location.can_access(user.uuid))

    def test_revoke_access_for_not_existing_user(self):
        location = self.locations_collection.create_item(TEST_LOCATION)
        self.assertRaisesRegexp(LookupError,
                                'User not found',
                                location.revoke_access,
                                FAKE_UUID)

    def test_find_location(self):
        collection = self.locations_collection
        location = collection.create_item('/foo/bar')
        self.assertEqual(location, collection.find_location('/foo/bar'))
        self.assertEqual(location, collection.find_location('/foo/bar/'))
        self.assertEqual(location, collection.find_location('/foo/bar/b'))
        self.assertEqual(location, collection.find_location('/foo/bar/baz'))
        self.assertEqual(
            location, collection.find_location('/foo/bar/baz/bar/'))

        self.assertIsNone(collection.find_location('/foo/ba'))
        self.assertIsNone(collection.find_location('/foo/barr'))
        self.assertIsNone(collection.find_location('/foo/foo/bar'))

    def test_more_specific_location_takes_precedence_over_generic(self):
        collection = self.locations_collection
        location1 = collection.create_item('/foo/bar')
        user = self.users_collection.create_item('foo@example.com')
        location1.grant_access(user.uuid)

        location2 = collection.create_item('/foo/bar/baz')
        self.assertEqual(location1, collection.find_location('/foo/bar'))
        self.assertEqual(location1, collection.find_location('/foo/bar/ba'))
        self.assertEqual(location1, collection.find_location('/foo/bar/bazz'))

        self.assertEqual(location2, collection.find_location('/foo/bar/baz'))
        self.assertEqual(location2, collection.find_location('/foo/bar/baz/'))
        self.assertEqual(
            location2, collection.find_location('/foo/bar/baz/bam'))
        self.assertFalse(location2.can_access(user.uuid))

    def test_trailing_slash_respected(self):
        location = self.locations_collection.create_item('/foo/bar/')
        self.assertIsNone(self.locations_collection.find_location('/foo/bar'))

    def test_grant_access_to_root(self):
        location = self.locations_collection.create_item('/')
        user = self.users_collection.create_item('foo@example.com')
        location.grant_access(user.uuid)

        self.assertEqual(location,
                         self.locations_collection.find_location('/'))
        self.assertEqual(location,
                         self.locations_collection.find_location('/f'))
        self.assertEqual(
            location, self.locations_collection.find_location ('/foo/bar/baz'))

    def test_grant_open_access(self):
        user = self.users_collection.create_item(TEST_USER_EMAIL)
        location = self.locations_collection.create_item(TEST_LOCATION)
        self.assertFalse(location.can_access(user.uuid))
        location.grant_open_access()
        self.assertTrue(location.can_access(user.uuid))
        location.revoke_open_access()
        self.assertFalse(location.can_access(user.uuid))

    def test_get_allowed_users(self):
        location1 = self.locations_collection.create_item('/foo/bar')
        location2 = self.locations_collection.create_item('/foo/baz')

        user1 = self.users_collection.create_item('foo@example.com')
        user2 = self.users_collection.create_item('bar@example.com')
        user3 = self.users_collection.create_item('baz@example.com')

        location1.grant_access(user1.uuid)
        location1.grant_access(user2.uuid)
        location2.grant_access(user3.uuid)

        self.assertItemsEqual(['foo@example.com', 'bar@example.com'],
                              [u.email for u in location1.allowed_users()])
        self.assertItemsEqual(['baz@example.com'],
                              [u.email for u in location2.allowed_users()])

        location1.revoke_access(user1.uuid)
        self.assertItemsEqual(['bar@example.com'],
                              [u.email for u in location1.allowed_users()])

    def test_get_allowed_users_when_empty(self):
        location = self.locations_collection.create_item(TEST_LOCATION)
        self.assertEqual([], location.allowed_users())

    def test_location_path_validation(self):
        self.assertRaisesRegexp(CreationException,
                                'should be absolute and normalized',
                                self.locations_collection.create_item,
                                '/foo/../bar')
        self.assertRaisesRegexp(CreationException,
                                'should not contain parameters',
                                self.locations_collection.create_item,
                                '/foo;bar')
        self.assertRaisesRegexp(CreationException,
                                'should not contain query',
                                self.locations_collection.create_item,
                                '/foo?s=bar')
        self.assertRaisesRegexp(CreationException,
                                'should not contain fragment',
                                self.locations_collection.create_item,
                                '/foo#bar')
        self.assertRaisesRegexp(CreationException,
                                'should contain only ascii',
                                self.locations_collection.create_item,
                                u'/żbik')

    def create_location(self, path):
        return self.locations_collection.create_item(path)

    """Path passed to create_location is expected to be saved verbatim."""
    def test_location_path_not_encoded(self):
        self.assertEqual('/foo%20bar', self.create_location('/foo%20bar').path)
        self.assertEqual('/foo~', self.create_location('/foo~').path)
        self.assertEqual('/foo/bar!@7*',
                         self.create_location('/foo/bar!@7*').path)


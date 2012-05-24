from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from urlparse import urlparse

import posixpath
import re
import string
import urllib
import uuid


# TODO: can this warning be fatal initialization error?
def site_url():
    return getattr(settings, 'SITE_URL',
                   'WARNING: SITE_URL is not set')

def full_url(absolute_path):
    return site_url() + absolute_path

def urn_from_uuid(uuid):
    return 'urn:uuid:' + uuid

# TODO: make it a member?
def add_common_attributes(item, attributes_dict):
    attributes_dict['self'] = full_url(item.get_absolute_url())
    if hasattr(item, 'uuid'):
        attributes_dict['id'] = urn_from_uuid(item.uuid)
    return attributes_dict

# TODO: remove duplication.
def _add(model_class, **kwargs):
    obj, created = model_class.objects.get_or_create(**kwargs)
    return created

def _del(model_class, **kwargs):
    object_to_del = model_class.objects.filter(**kwargs)
    assert object_to_del.count() <= 1
    if object_to_del.count() == 0:
        return False
    object_to_del.delete()
    return True

# TODO: remove duplication.
def _find(model_class, **kwargs):
    item = model_class.objects.filter(**kwargs)
    count = item.count()
    assert count <= 1
    if count == 0:
        return None
    return item.get()

class ValidatedModel(models.Model):
    def save(self, *args, **kwargs):
        self.full_clean()
        return super(ValidatedModel, self).save(*args, **kwargs)

    class Meta:
        # Do not create a DB table for ValidatedModel.
        abstract = True

# TODO: just location?
class HttpLocation(ValidatedModel):
    path = models.CharField(max_length=2000, null=False, primary_key=True)
    uuid = models.CharField(max_length=36, null=False, db_index=True,
                            editable=False)
    def __unicode__(self):
        return "%s" % (self.path)

    def attributes_dict(self):
        return add_common_attributes(self, {
                'path': self.path,
                'allowedUsers': self.allowed_users(),
                })

    def grant_access(self, user_uuid):
        user = _find(User, username=user_uuid)
        if user is None:
            raise LookupError('User not found')
        try:
            obj = HttpPermission.objects.get(
                http_location_id=self.path, user_id=user.id)
            return (obj, False)
        except HttpPermission.DoesNotExist:
            obj = HttpPermission.objects.create(
                http_location_id=self.path, user_id=user.id)
            obj.save()
            return (obj, True)

    def revoke_access(self, user_uuid):
        user = _find(User, username=user_uuid)
        if user is None:
            raise LookupError('User not found.')
        if not _del(HttpPermission, http_location_id=self.path,
                    user_id=user.id):
            raise LookupError('User can not access location.')


    def get_permission(self, user_uuid):
        user = _find(User, username=user_uuid)
        if user is None:
            raise LookupError('User not found.')

        item = HttpPermission.objects.filter(http_location_id=self.path,
                                             user_id=user.id)
        assert item.count() <= 1
        if item.count() == 0:
            raise LookupError('User can not access location.')
        return item.get()

    def allowed_users(self):
        return [permission.user.attributes_dict() for permission in
                HttpPermission.objects.filter(http_location=self.path)]

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = str(uuid.uuid4())
        return super(HttpLocation, self).save(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
        return ('wwwhisper_location', (), {'uuid' : self.uuid})

# TODO: rename to allowed_user?
class HttpPermission(ValidatedModel):
    http_location = models.ForeignKey(HttpLocation)
    user = models.ForeignKey(User)

    def __unicode__(self):
        return "%s, %s" % (self.http_location, self.user.email)

    def attributes_dict(self):
        return add_common_attributes(
            self, {'user': self.user.attributes_dict()})

    @models.permalink
    def get_absolute_url(self):
        return ('wwwhisper_allowed_user', (),
                {'location_uuid' : self.http_location.uuid,
                 'user_uuid': self.user.uuid})


# TODO: remove this:
class UserProfile(models.Model):
    user = models.OneToOneField(User)
#    uuid = models.CharField(max_length=36, null=False, primary_key=True,
#                            editable=False)

    def save(self, *args, **kwargs):
#        if not self.uuid:
#            self.uuid = uuid.uuid4()
        return super(UserProfile, self).save(*args, **kwargs)


User.uuid = property(lambda(self): self.username)

# TODO: get_attributes_dict for symmetry with get_absolute_url?
User.attributes_dict = lambda(self): \
    add_common_attributes(self, {'email': self.email})

def create_user_extras(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_extras, sender=User)


# models.

class InvalidPath(ValueError):
    pass

class CreationException(Exception):
    pass;


def _add(model_class, **kwargs):
    obj, created = model_class.objects.get_or_create(**kwargs)
    return created

def _del(model_class, **kwargs):
    object_to_del = model_class.objects.filter(**kwargs)
    assert object_to_del.count() <= 1
    if object_to_del.count() == 0:
        return False
    object_to_del.delete()
    return True

def _find2(model_class, **kwargs):
    item = model_class.objects.filter(**kwargs)
    count = item.count()
    assert count <= 1
    if count == 0:
        return None
    return item.get()

def _all(model_class, field):
    return [obj.__dict__[field] for obj in model_class.objects.all()]

def add_location(path):
    return _add(HttpLocation, path=path)

def del_location(path):
    return _del(HttpLocation, path=path)

def find_location(path):
    return _find(HttpLocation, path=path)

def locations():
    return _all(HttpLocation, 'path')

def encode_path(path):
    parsed_url = urlparse(path)
    not_expected = []
    if parsed_url.scheme != '':
        not_expected.append("scheme: '%s'" % parsed_url.scheme)
    if parsed_url.netloc != '':
        not_expected.append("domain: '%s'" % parsed_url.netloc)
    if parsed_url.params != '':
        not_expected.append("parameters: '%s'" % parsed_url.params)
    if parsed_url.query != '':
        not_expected.append("query: '%s'" % parsed_url.query)
    if parsed_url.fragment != '':
        not_expected.append("fragment: '%s'" % parsed_url.fragment)
    if parsed_url.port != None:
        not_expected.append("port: '%d'" % parsed_url.port)
    if parsed_url.username != None:
        not_expected.append("username: '%s'" % parsed_url.username)
    if len(not_expected):
        raise InvalidPath('Invalid path, not expected: %s.'
                          % string.join(not_expected, ', '))
    stripped_path = parsed_url.path.strip()
    if stripped_path == '':
        raise InvalidPath('Path should not be empty.')

    normalized_path =  posixpath.normpath(stripped_path)
    if (normalized_path != stripped_path and
        normalized_path + '/' != stripped_path):
        raise InvalidPath(
            "Path should be normalized (without /../ or /./ or //)")
    #TODO: test if this makes sense:
    try:
        encoded_path = stripped_path.encode('utf-8', 'strict')
    except UnicodeError, er:
        raise InvalidPath('Invalid path encoding %s' % str(er))
    return urllib.quote(encoded_path, '/~')

def grant_access(email, location_path):
    if not find_location(location_path):
        raise LookupError('Location does not exist')
    add_user(email)
    user_id = User.objects.get(email=email).id
    return _add(HttpPermission, http_location_id=location_path, user_id=user_id)


def revoke_access(email, location_path):
    if not find_location(location_path):
        raise LookupError('Location does not exist')
    return _del(HttpPermission, user__email=email, http_location=location_path)

# TODO: should this work only for defined locations or check parent locations?
# TODO: moved to models.py
def allowed_emails(path):
    return [permission.user.email for permission in
            HttpPermission.objects.filter(http_location=path)]

# TODO: How to handle trailing '/'? Maybe remove it prior to adding path to db?
def can_access(email, path):
    path_len = len(path)
    longest_match = ''
    longest_match_len = -1

    for probed_path in locations():
        probed_path_len = len(probed_path)
        stripped_probed_path = probed_path.rstrip('/')
        stripped_probed_path_len = len(stripped_probed_path)
        if (path.startswith(stripped_probed_path) and
            probed_path_len > longest_match_len and
            (stripped_probed_path_len == path_len
             or path[stripped_probed_path_len] == '/')):
            longest_match_len = probed_path_len
            longest_match = probed_path
    return longest_match_len != -1 and \
        _find(HttpPermission, user__email=email, http_location=longest_match)

def add_user(email):
    if find_user(email):
        return False
    User.objects.create(username=uuid.uuid4(), email=email, is_active=True)
    return True;

def del_user(email):
    return _del(User, email=email)

def find_user(email):
    return _find(User, email=email)

# def find_user_with_uuid(uid):
#     return _find(User, uid=uid)

# TODO: capital letters in email are not accepted
def is_email_valid(email):
    """Validates email with regexp defined by BrowserId:
    browserid/browserid/static/dialog/resources/validation.js
    """
    return re.match(
        "^[\w.!#$%&'*+\-/=?\^`{|}~]+@[a-z0-9-]+(\.[a-z0-9-]+)+$",
        email) != None

class UsersCollection(object):
    collection_name = 'users'
    item_name = 'user'

    def create_item(self, email):
        if not is_email_valid(email):
            raise CreationException('Invalid email format.')
        if find_user(email):
            raise CreationException('User already exists.')
        user = User.objects.create(
            username=str(uuid.uuid4()), email=email)
        return user

    def all(self):
        return User.objects.all()

    def get(self, uuid):
        item = User.objects.filter(username=uuid)
        assert item.count() <= 1
        if item.count() == 0:
            return None
        return item.get()

    # should this rather be .get().delete()
    def delete(self, uuid):
        return _del(User, username=uuid)


class LocationsCollection(object):
    collection_name = 'locations'
    item_name = 'location'

    def create_item(self, path):
        try:
            encoded_path = encode_path(path)
        except InvalidPath, ex:
            raise CreationException(ex)
        if find_location(encoded_path):
            raise CreationException('Location already exists.')
        location = HttpLocation.objects.create(path=encoded_path)
        location.save()
        return location

    def all(self):
        return HttpLocation.objects.all()

    def get(self, uuid):
        item = HttpLocation.objects.filter(uuid=uuid)
        assert item.count() <= 1
        if item.count() == 0:
            return None
        return item.get()

    def delete(self, uuid):
        return _del(HttpLocation, uuid=uuid)

# Create your views here.

from django.conf import settings
from django.contrib.auth.models import User
from django.views.generic import View
from django.core import serializers
from django.http import HttpResponse
from functools import wraps

import wwwhisper_auth.acl as acl
import json
#TODO: style guide. Cammel names or names with '_'?

#TODO: acladmin ->admin?

def getResourceList():
    return [ {
            'path': path,
            'allowedUsers': acl.allowed_emails(path)
            } for path in acl.locations()]

def model2json(csrf_token):
    site_url = getattr(settings, 'SITE_URL',
                       'WARNING: SITE_URL is not set')
    return json.dumps({
            'resourcesRoot': site_url,
            'csrfToken': csrf_token,
            'resources': getResourceList(),
            'contacts': acl.emails()
            })

def success(message=None):
    if message:
        return HttpResponse(message, status=200)
    return HttpResponse(status=200)


def error(message):
    # TODO: change status.
    return HttpResponse(message, status=400)

def methodNotAllowed():
    return HttpResponse(status=405)

def csrf_token_valid(token, session_key):
    return token == session_key


class Model(View):
    def get(self, request):
        data = model2json(request.session.session_key)
        print "model: " + str(data) + " session: " \
            + request.session.session_key
        return HttpResponse(data, mimetype="application/json")

class RestView(View):
    def dispatch(self, request):
        request_args = json.loads(request.raw_post_data)
        csrf_token = request_args.pop('csrfToken', None)
        if csrf_token == None:
            return error('CSRF protection token missing')
        if not csrf_token_valid(csrf_token, request.session.session_key):
            return error('Invalid CSRF protection token')

        if request.method.lower() in self.http_method_names:
            handler = getattr(
                self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed

        # TODO: maybe do not pass request?
        return handler(request, **request_args)

# TODO: rename resource -> location
class Resource(RestView):
    def put(self, request, path):
        print "Add location " + path
        try:
            result = acl.encode_path(path)
        except acl.InvalidPath, ex:
            return error(str(ex))
        location_added = acl.add_location(result)
        if not location_added:
            return error(result + ' already exists')
        # TODO: should each put return result for symetry?
        # TODO: should this be returned as json object?
        return success(result)

    def delete(self, request, path):
        print "Remove location " + path
        location_deleted = acl.del_location(path)
        if not location_deleted:
            return error(path + ' does not exist')
        return success()

# TODO rename contact
class Contact(RestView):
    def put(self, request, email):
        print "Add contact " + email
        if not acl.is_email_valid(email):
            return error('Invalid email format')
        user_added = acl.add_user(email)
        if not user_added:
            return error(email + ' already on contact list')
        return success()

    def delete(self, request, email):
        print "Remove contact " + email
        user_deleted = acl.del_user(email)
        if not user_deleted:
            return error(email + ' is not on contact list')
        return success()

class Permission(RestView):
    def put(self, request, email, path):
        print "Grant permission to " + path + " for " + email
        if not acl.grant_access(email, path):
            return error('User already can access path.')
        return success()

    def delete(self, request, email, path):
        print "Revoke permission to " + path + " for " + email
        access_revoked = acl.revoke_access(email, path)
        if not access_revoked:
            return error('User already can not access path.')
        return success()


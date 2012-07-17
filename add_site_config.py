#!./virtualenv/bin/python

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

"""Configures wwwhisper for a given site.

Creates site-specific Django settings files. Creates configuration
file for supervisor (http://supervisord.org/), which allows to
start wwwhisper application under the control of the supervisor
deamon. Initializes database with access control list.
"""

import getopt
import os
import sys
import random
import subprocess

from urlparse import urlparse

SITES_DIR = 'sites'
DJANGO_CONFIG_DIR = 'django'
DJANGO_CONFIG_FILE = 'site_settings.py'
SUPERVISOR_CONFIG_DIR = 'supervisor'
SUPERVISOR_CONFIG_FILE= 'site.conf'
DB_DIR = 'db'
DB_NAME = 'acl_db'

WWWHISPER_USER = 'wwwhisper'
WWWHISPER_GROUP = 'www-data'

def err_quit(errmsg):
    """Prints an error message and quits."""
    print >> sys.stderr, errmsg
    sys.exit(1)

def usage():
    print """

Generates site-specific configuration files and initializes wwwhisper database.
Usage:

  %(prog)s
      -s, --site_url A URL of a site to protect in a form
            scheme://domain(:port). Scheme can be https (recomended) or http.
            Port defaults to 443 for https and 80 for http.
      -a, --admin_email An email of a user that will be allowed to access
            wwwhisper admin interface after wwwhisper is configured.
            More such users can be added via the admin interface.
""" % {'prog': sys.argv[0]}
    sys.exit(1)

def generate_secret_key():
    """Generates a secret key with cryptographically secure generator.

    Displays a warning and generates a key that does not parse if the
    system does not provide a secure generator.
    """
    try:
        secure_generator = random.SystemRandom()
        allowed_chars='abcdefghijklmnopqrstuvwxyz'\
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'\
            '!@#$%^&*(-_=+'
        key_length = 50
        # This gives log2((26+26+10+14)**50) == 312 bits of entropy
        return ''.join(
            [secure_generator.choice(allowed_chars) for i in range(key_length)])
    except NotImplementedError:
        # The system does not support generation of secure random
        # numbers. Return something that raises parsing error and
        # points the user to a place where secret key needs to be
        # filled manually.
        message = ('Your system does not allow to automatically '
                   'generate secure secret keys.')
        print >> sys.stderr, ('WARNING: You need to edit configuration file '
                              'manually. ' + message)
        return ('\'---' + message + ' Replace this text with a long, '
                'unpredictable secret string (at least 50 characters).')


def write_to_file(dir_path, file_name, file_content):
    """Writes a string to a file with a given name in a given directory.

    If the file does not exist it is created. Dies on error.
    """
    file_path = os.path.join(dir_path, file_name)
    try:
        with open(file_path, 'w') as destination:
            destination.write(file_content)
    except IOError as ex:
        err_quit('Failed to create file %s: %s.' % (file_path, ex))

def create_django_config_file(site_url, admin_email, django_config_path,
                              db_path):
    """Creates a site specific Django configuration file.

    Settings that are common for all sites reside in the
    wwwhisper_service module.
    """

    settings = """# Don't share this with anybody.
SECRET_KEY = '%s'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '%s',
    }
}

SITE_URL = '%s'
WWWHISPER_ADMINS = ['%s']
""" % (generate_secret_key(),
       os.path.join(db_path, DB_NAME),
       site_url,
       admin_email)
    write_to_file(django_config_path, '__init__.py', '')
    write_to_file(django_config_path, DJANGO_CONFIG_FILE, settings)

def create_supervisor_config_file(
    site_dir_name, root_path, site_config_path, supervisor_config_path):
    """Creates site-specific supervisor config file.

    The file allows to start the wwwhisper application for the site.
    """
    settings = """[program:wwwhisper-%s]
command=%s/run_wwwhisper_for_site.sh -d %s
user=%s
group=%s
autorestart=true
stopwaitsecs=16
stopsignal=INT
stopasgroup=true
""" % (site_dir_name, root_path, site_config_path, WWWHISPER_USER,
       WWWHISPER_GROUP)
    write_to_file(
        supervisor_config_path, SUPERVISOR_CONFIG_FILE, settings)

def parse_url(url):
    """Parses and validates a URL.

    URL needs to have scheme://domain:port format, scheme and domain
    are mandatory, port is optional. If the URL is valid, returns it
    with all characters converted to lower case. Dies if the URL is
    invalid.
    """

    err_prefix = 'Invalid site address - '
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme.lower()
    if scheme == '' or scheme not in ('https', 'http'):
        err_quit(err_prefix + 'scheme missing. '
                 'URL schould start with https:// (recommended) or http://')
    if parsed_url.hostname is None:
        err_quit(err_prefix + 'domain name missing.'
                 'URL should include full domain name (like https://foo.org).')
    if parsed_url.path  != '':
        err_quit(err_prefix + 'URL should not include resource path '
                 '(/foo/bar).')
    if parsed_url.params  != '':
        err_quit(err_prefix + 'URL should not include parameters (;foo=bar).')
    if parsed_url.query  != '':
        err_quit(err_prefix + 'URL should not include query (?foo=bar).')
    if parsed_url.fragment  != '':
        err_quit(err_prefix + 'URL should not include query (#foo).')
    if parsed_url.username != None:
        err_quit(err_prefix + 'URL should not include username (foo@).')

    hostname = parsed_url.hostname.lower()
    port = parsed_url.port
    if port is not None:
        return scheme + '://' + hostname + ':' + str(port)
    else:
        return scheme + '://' + hostname

def url2dirname(url):
    """Converts a site URL to a directory name.

    The directory will be used to store configuration for the site.
    """
    # '/' is forbidden in file names, ':' is not handled properply by nginx.
    return url.replace('://', '.').replace(':', '.')

def main():
    site_url = None
    admin_email = None
    root_path = os.path.dirname(os.path.abspath(sys.argv[0]))

    try:
        optlist, _ = getopt.gnu_getopt(sys.argv[1:],
                                       's:a:h',
                                       ['site_url=', 'admin_email=', 'help'])
    except getopt.GetoptError, ex:
        print 'Arguments parsing error: ', ex,
        usage()

    for opt, arg in optlist:
        if opt in ('-h', '--help'):
            usage()
        elif opt in ('-s', '--site_url'):
            site_url = arg
        elif opt in ('-a', '--admin_email'):
            admin_email = arg
        else:
            assert False, 'unhandled option'


    if site_url is None:
        err_quit('--site_url is missing.')
    if admin_email is None:
        err_quit('--admin_email is missing.')

    site_url = parse_url(site_url)
    site_dir_name = url2dirname(site_url)

    # TODO: dir->path
    site_config_path = os.path.join(root_path, SITES_DIR, site_dir_name)
    django_config_path = os.path.join(site_config_path, DJANGO_CONFIG_DIR)
    db_path = os.path.join(site_config_path, DB_DIR)
    supervisor_config_path = os.path.join(
        site_config_path, SUPERVISOR_CONFIG_DIR)
    try:
        os.umask(067)
        os.makedirs(site_config_path, 0710)
        os.umask(077)
        os.makedirs(django_config_path)
        os.makedirs(db_path)
        os.makedirs(supervisor_config_path)
    except OSError as ex:
        err_quit('Failed to initialize configuration directory %s: %s.'
                 % (site_config_path, ex))

    create_django_config_file(
        site_url, admin_email, django_config_path, db_path)

    create_supervisor_config_file(
        site_dir_name, root_path, site_config_path, supervisor_config_path)

    manage_path = os.path.join(root_path, 'django_wwwhisper', 'manage.py')
    # Use Python from the virtual environment to run syncdb.
    exit_status = subprocess.call(
        ['./virtualenv/bin/python', manage_path, 'syncdb',
         '--pythonpath=' + django_config_path])
    if exit_status != 0:
        err_quit('Failed to initialize wwwhisper database.');

    print 'Site configuration successfully created.'

if __name__ == '__main__':
    main()
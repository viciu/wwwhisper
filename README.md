[wwwhisper will be released mid-August 2012]

wwwhisper simplifies sharing of Web resources that are not intended
for everyone. It is a generic access control layer for nginx HTTP
server that allows to specify which resources can be accessed by
which visitors.

* wwwhisper grants access to HTTP resources based on users' email
  addresses, which enables sharing with almost every Internet user.
  [Persona](http://persona.org) is used to prove that a visitor owns
  an allowed email, no site-specific password is needed. Persona UI
  makes authentication process really smooth.

* wwwhisper is application independent. It can be used for anything
  that nginx serves - dynamic content, static files, content generated
  by back-end servers. No support from applications or back-ends is needed.

* wwwhisper provides a REST-like API for granting and revoking access
  and an admin web application that gives a convenient UI for
  manipulating permissions. Access to the admin API is protected by
  wwwhisper, this allows to easily authenticate, add and remove admin
  users.



Technical details
-----------------

wwwhisper is a service implemented in Django that runs along nginx
and that enables following actions:

1. Authentication and authorization: login a user, get an email of
the currently logged in user, logout the user, check if
the user is authorized to access a given location.

2. Admin operations: add/remove a user with a given email, grant a
user access to a given path, revoke access, allow not-authenticated
access to a given path.

wwwhisper utilizes auth-request nginx module created by Maxim Dounin.
The module allows to specify which locations require authorization.
Each time a request is made to a protected location, the auth-request
module sends a sub-request to the wwwhisper process to determine if
the original request should be allowed. The sub-request carries a path
and all headers of the original request (including cookies).
wwwhisper responds to the sub-request in one of three possible ways:

1. If a user is not authenticated (authentication cookie not set or
   invalid), HTTP status code 401 is returned. HTTP server intercepts
   this code and returns a login page to the user.

2. If a user is authenticated and is authorized to access the
   requested resource (user's email is on a list of allowed users),
   sub-request returns HTTP status code 200. HTTP server intercepts
   this code and allows the original request.

3. If a user is authenticated but is not authorized to access the
   requested resource, sub-request returns HTTP status code 403, which
   is returned to the user.

The login page, which is presented to not authenticated users, asks
the user to sign-in with Persona. Sign-in process returns a
cryptographically-secure assertion that is sent to the wwwhisper and
that allows to determine a verified email address of the user. The
assertion does not carry user's password and is valid only for the
current domain, because of this, a malicious site can not use the
assertion to authenticate with other sites. After extracting the email
from the assertion, wwwhisper determines if any resources are shared
with the user. If yes, a session cookie is set and the user is
successfully logged in. If no resources are shared, a 403 error is
returned to the user and a session cookie is not set.

nginx sub_filter module is used to insert a small iframe at the bottom
of every protected html document. The iframe contains the user's email
address and a 'sign out' button.


Installation
------------

Following steps demonstrate how to setup nginx with wwwhisper on
Debian-derivative Linux distribution (including Ubuntu). The steps
should be easy to adjust to work on other POSIX systems.


Final remarks
-----------------

1. Make sure content you are protecting can not be accessed through
some other channels. If you are using a multiuser server, set
correct file permissions for protected static files and
communication sockets. If nginx is delegating requests to backend
servers, make sure the backends are not externally accessible.

2. Use SSL for anything important. You can get a free [SSL certificate
   for personal use](https://cert.startcom.org/).
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Web-application views for the schooltool.app objects.

$Id$
"""

import datetime
import re
from schooltool.browser import View, Template, StaticFile
from schooltool.browser import notFoundPage
from schooltool.browser import absoluteURL
from schooltool.browser.auth import PublicAccess, AuthenticatedAccess
from schooltool.browser.auth import ManagerAccess, globalTicketService
from schooltool.browser.model import PersonView, GroupView
from schooltool.component import getPath
from schooltool.interfaces import IApplication, IApplicationObjectContainer
from schooltool.interfaces import IPerson, AuthenticationError
from schooltool.translation import ugettext as _

__metaclass__ = type


# Time limit for session expiration
session_time_limit = datetime.timedelta(hours=5)

# Person username / group name validation
# XXX Perhaps this constraint is a bit too strict.
valid_name = re.compile("^[a-zA-Z0-9.,'()]+$")

class RootView(View):
    """View for the web application root.

    Presents a login page.  Redirects to a person's information page after
    a successful login.

    Sublocations found at / are

        schooltool.css      the stylesheet
        logout              logout page (accessing it logs you out)
        start               a person's start page
        persons/id          person information pages
        groups/id           group information pages

    """

    __used_for__ = IApplication

    authorization = PublicAccess

    template = Template("www/login.pt")

    error = False
    username = ''

    def do_POST(self, request):
        username = request.args['username'][0]
        password = request.args['password'][0]
        try:
            user = request.site.authenticate(self.context, username, password)
        except AuthenticationError:
            self.error = True
            self.username = username
            return self.do_GET(request)
        else:
            ticket = globalTicketService.newTicket((username, password),
                                                   session_time_limit)
            request.addCookie('auth', ticket)
            if 'url' in request.args:
                url = request.args['url'][0]
            else:
                url = '/start'
            return self.redirect(url, request)

    def _traverse(self, name, request):
        if name == 'persons':
            return PersonContainerView(self.context['persons'])
        if name == 'groups':
            return GroupContainerView(self.context['groups'])
        elif name == 'schooltool.css':
            return StaticFile('www/schooltool.css', 'text/css')
        elif name == 'logo.png':
            return StaticFile('www/logo.png', 'image/png')
        elif name == 'logout':
            return LogoutView(self.context)
        elif name == 'start':
            return StartView(request.authenticated_user)
        raise KeyError(name)


class LogoutView(View):
    """View for /logout.

    Accessing this URL causes the authenticated user to be logged out and
    redirected back to the login page.
    """

    __used_for__ = IApplication

    authorization = PublicAccess

    def do_GET(self, request):
        auth_cookie = request.getCookie('auth')
        globalTicketService.expire(auth_cookie)
        return self.redirect('/', request)


class StartView(View):
    """Start page (/start).

    This is where the user is redirected after logging in.  The start page
    displays common actions.
    """

    __used_for__ = IPerson

    authorization = AuthenticatedAccess

    template = Template("www/start.pt")

    def person_url(self):
        return absoluteURL(self.request, self.context)


class PersonContainerView(View):
    """View for /persons.

    Accessing this location returns a 404 Not Found response.

    Traversing /persons with a person's id returns the person information page
    for that person.
    """

    __used_for__ = IApplicationObjectContainer

    authorization = PublicAccess

    do_GET = staticmethod(notFoundPage)

    def _traverse(self, name, request):
        if name == 'add.html':
            return PersonAddView(self.context)
        else:
            return PersonView(self.context[name])


class PersonAddView(View):
    """A view for adding persons."""

    __used_for__ = IApplicationObjectContainer

    authorization = ManagerAccess

    template = Template('www/person_add.pt')

    prev_username = ''
    error = None

    def do_POST(self, request):
        username = request.args['username'][0]
        password = request.args['password'][0]
        verify_password = request.args['verify_password'][0]

        if not valid_name.match(username):
            self.error = _('Invalid username')
            return self.do_GET(request)

        self.prev_username = username
        if password != verify_password:
            self.error = _('Passwords do not match')
            return self.do_GET(request)

        # XXX Do we really want to allow empty passwords?
        # XXX Should we care about Unicode vs. UTF-8 passwords?

        person = self.context.new(username, title=username)
        person.setPassword(password)

        # We could say 'Person created', but we want consistency
        # (AKA wart-compatibility).
        request.appLog(_("Object created: %s") % getPath(person))
        url = absoluteURL(request, person) + '/edit.html'
        return self.redirect(url, request)


class GroupContainerView(View):
    """View for /groups.

    Accessing this location returns a 404 Not Found response.

    Traversing /groups with a group's id returns the group information page
    for that group.
    """

    __used_for__ = IApplicationObjectContainer

    authorization = PublicAccess

    do_GET = staticmethod(notFoundPage)

    def _traverse(self, name, request):
        if name == 'add.html':
            return GroupAddView(self.context)
        else:
            return GroupView(self.context[name])


class GroupAddView(View):
    """A view for adding a new group."""

    __used_for__ = IApplicationObjectContainer

    authorization = ManagerAccess

    template = Template('www/group_add.pt')

    error = ""

    def do_POST(self, request):
        groupname = request.args['groupname'][0]

        if not valid_name.match(groupname):
            self.error = _("Invalid group name")
            return self.do_GET(request)

        group = self.context.new(groupname, title=groupname)
        request.appLog(_("Object created: %s") % getPath(group))

        url = absoluteURL(request, group) + '/edit.html'
        return self.redirect(url, request)

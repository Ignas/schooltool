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
The views for the schooltool content objects.

$Id$
"""

import re
import datetime
from zope.interface import moduleProvides
from zope.pagetemplate.pagetemplatefile import PageTemplateFile
from twisted.web.resource import Resource
from schooltool.interfaces import IModuleSetup
from schooltool.component import getView

__metaclass__ = type


moduleProvides(IModuleSetup)


#
# Helpers
#

def absoluteURL(request, path):
    """Returns the absulute URL of the object adddressed with path"""
    if not path.startswith('/'):
        raise ValueError("Path must be absolute")
    return 'http://%s%s' % (request.getRequestHostname(), path)


def parse_datetime(s):
    """Parses ISO 8601 date/time values.

    Only a small subset of ISO 8601 is accepted:

      YYYY-MM-DD HH:MM:SS
      YYYY-MM-DD HH:MM:SS.ssssss
      YYYY-MM-DDTHH:MM:SS
      YYYY-MM-DDTHH:MM:SS.ssssss

    Returns a datetime.datetime object without a time zone.
    """
    m = re.match("(\d+)-(\d+)-(\d+)[ T](\d+):(\d+):(\d+)([.](\d+))?$", s)
    if not m:
        raise ValueError("Bad datetime: %s" % s)
    ssssss = m.groups()[7]
    if ssssss:
        ssssss = int((ssssss + "00000")[:6])
    else:
        ssssss = 0
    y, m, d, hh, mm, ss = map(int, m.groups()[:6])
    return datetime.datetime(y, m, d, hh, mm, ss, ssssss)


#
# Page templates
#

class Template(PageTemplateFile):
    """Page template file.

    Character set for rendered pages can be set by changing the 'charset'
    attribute.  You should not change the default (UTF-8) without a good
    reason.  If the page template contains characters not representable
    in the output charset, a UnicodeError will be raised when rendering.
    """

    def __init__(self, filename, content_type='text/html', charset='UTF-8',
                       _prefix=None):
        _prefix = self.get_path_from_prefix(_prefix)
        PageTemplateFile.__init__(self, filename, _prefix)
        self.content_type = content_type
        self.charset = charset

    def __call__(self, request, **kw):
        """Renders the page template.

        Any keyword arguments passed to this function will be accessible
        in the page template namespace.
        """
        request.setHeader('Content-Type',
                          '%s; charset=%s' % (self.content_type, self.charset))
        context = self.pt_getContext()
        context['request'] = request
        context.update(kw)
        return self.pt_render(context).encode(self.charset)


#
# HTTP view infrastructure
#

class ErrorView(Resource):
    """View for an error.

    Rendering this view will set the appropriate HTTP status code and reason.
    """

    __super = Resource
    __super_init = __super.__init__

    isLeaf = True

    template = Template('www/error.pt')

    def __init__(self, code, reason):
        self.__super_init()
        self.code = code
        self.reason = reason

    def render(self, request):
        request.setResponseCode(self.code, self.reason)
        return self.template(request, code=self.code, reason=self.reason)


class NotFoundView(ErrorView):
    """View for a not found error.

    This view should be used for HTTP status code 404.
    """

    __super = ErrorView
    __super_init = __super.__init__

    template = Template('www/notfound.pt')

    def __init__(self, code=404, reason='Not Found'):
        self.__super_init(code, reason)


def errorPage(request, code, reason):
    """Renders a simple error page and sets the HTTP status code and reason."""
    return ErrorView(code, reason).render(request)


def notFoundPage(request):
    """Renders a simple 'not found' error page."""
    return NotFoundView().render(request)


def textErrorPage(request, message, code=400, reason=None):
    """Renders a simple error page and sets the HTTP status code and reason."""
    request.setResponseCode(code, reason)
    request.setHeader('Content-Type', 'text/plain')
    return str(message)


class View(Resource):
    """View for a content component.

    A View is a kind of a Resource in twisted.web sense, but it is
    really just a view for the actual resource, which is a content
    component.

    Rendering and traversal happens in a separate worker thread.  It
    is incorrect to call request.write or request.finish, or other
    non-thread-safe methods.  You can read more in Twisted
    documentation section about threading.

    Subclasses could provide the following methods and attributes:

        template    Attribute that contains a Template instance for rendering.
        _traverse   Method that should return a view for a contained object
                    or raise a KeyError.
        do_FOO      Method that processes HTTP requests FOO for various values
                    of FOO.  Its signature should match render.

    """

    __super = Resource
    __super_init = __super.__init__

    def __init__(self, context):
        self.__super_init()
        self.context = context

    def getChild(self, name, request):
        if name == '': # trailing slash in the URL
            if request.path == '/':
                return self
            else:
                return NotFoundView()
        try:
            return self._traverse(name, request)
        except KeyError:
            return NotFoundView()

    def _traverse(self, name, request):
        raise KeyError(name)

    def render(self, request):
        handler = getattr(self, 'do_%s' % request.method, None)
        if handler is not None:
            body = handler(request)
            assert isinstance(body, str), \
                   "do_%s did not return a string" % request.method
            return body
        else:
            request.setHeader('Allow', ', '.join(self.allowedMethods()))
            return errorPage(request, 405, "Method Not Allowed")

    def allowedMethods(self):
        """Lists all allowed methods."""
        return [name[3:] for name in dir(self)
                         if name.startswith('do_')
                             and name[3:].isalpha()
                             and name[3:].isupper()]

    def do_GET(self, request):
        return self.template(request, view=self, context=self.context)

    def do_HEAD(self, request):
        body = self.do_GET(request)
        request.setHeader('Content-Length', len(body))
        return ""


class ItemTraverseView(View):
    """A view that supports traversing with __getitem__."""

    def _traverse(self, name, request):
        return getView(self.context[name])


class TraversableView(View):
    """A view that supports traversing of ITraversable contexts."""

    def _traverse(self, name, request):
        return getView(self.context.traverse(name))


class XMLPseudoParser:
    """XXX This is a temporary stub for validating XML parsing."""

    def extractKeyword(self, text, key):
        """Extracts values of key="value" format from a string.

        Throws a KeyError if key is not found.
        """
        pat = re.compile(r'\b%s="([^"]*)"' % key)
        match = pat.search(text)
        if match:
            return match.group(1)
        else:
            raise KeyError("%r not in text" % (key,))


def setUp():
    """See IModuleSetup."""
    import schooltool.views.app
    import schooltool.views.model
    import schooltool.views.facet
    import schooltool.views.utility
    import schooltool.views.eventlog
    schooltool.views.app.setUp()
    schooltool.views.model.setUp()
    schooltool.views.facet.setUp()
    schooltool.views.utility.setUp()
    schooltool.views.eventlog.setUp()


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
The views for the schooltool.model objects.

$Id$
"""

from zope.interface import moduleProvides
from zope.app.traversing.api import getPath

from schooltool.interfaces import IModuleSetup
from schooltool.interfaces import IGroup, IPerson, IResource, INote
from schooltool.interfaces import IApplicationObject
from schooltool.uris import URIMember, URIGroup
from schooltool.component import registerView
from schooltool.component import getRelatedObjects
from schooltool.component import FacetManager
from schooltool.rest import View, Template
from schooltool.rest import notFoundPage
from schooltool.rest import absolutePath
from schooltool.rest.relationship import RelationshipsView
from schooltool.rest.facet import FacetManagementView
from schooltool.rest.timetable import TimetableTraverseView
from schooltool.rest.timetable import CompositeTimetableTraverseView
from schooltool.rest.cal import CalendarView, CalendarReadView, BookingView
from schooltool.rest.absence import RollCallView, AbsenceManagementView
from schooltool.rest.acl import ACLView
from schooltool.rest.auth import PublicAccess, PrivateAccess
from schooltool.translation import ugettext as _

__metaclass__ = type


moduleProvides(IModuleSetup)


class ApplicationObjectTraverserView(View):
    """A view that supports traversing to facets and relationships etc."""

    def href(self):
        return absolutePath(self.request, self.context)

    def _traverse(self, name, request):
        if name == 'facets':
            return FacetManagementView(FacetManager(self.context))
        elif name == 'relationships':
            return RelationshipsView(self.context)
        elif name == 'calendar':
            return CalendarView(self.context.calendar)
        elif name == 'timetable-calendar':
            return CalendarReadView(self.context.makeTimetableCalendar())
        elif name == 'timetables':
            return TimetableTraverseView(self.context)
        elif name == 'composite-timetables':
            return CompositeTimetableTraverseView(self.context)
        raise KeyError(name)


class ApplicationObjectDeleteMixin:
    """A mixin that implements HTTP DELETE for application objects."""

    def do_DELETE(self, request):
        """Delete self.context from the system."""
        delete_app_object(self.context, request.appLog)
        request.setHeader('Content-Type', 'text/plain')
        return _("Object deleted.")


class GroupView(ApplicationObjectTraverserView, ApplicationObjectDeleteMixin):
    """A view for a group."""

    template = Template("www/group.pt", content_type="text/xml")
    authorization = PublicAccess

    def _traverse(self, name, request):
        if name == 'rollcall':
            return RollCallView(self.context)
        elif name == 'tree':
            return TreeView(self.context)
        elif name == 'acl':
            return ACLView(self.context.acl)
        return ApplicationObjectTraverserView._traverse(self, name, request)

    def listItems(self):
        for item in getRelatedObjects(self.context, URIMember):
            yield {'title': item.title,
                   'href': absolutePath(self.request, item)}


class TreeView(View):
    """A view that shows the group tree in XML."""

    template = Template('www/tree.pt', content_type='text/xml')
    node_template = Template('www/tree_node.pt',
                             content_type=None, charset=None)
    authorization = PublicAccess

    def generate(self, node):
        children = [child for child in getRelatedObjects(node, URIMember)
                    if IGroup.providedBy(child)]
        res = self.node_template(self.request, title=node.title,
                             href=absolutePath(self.request, node),
                             children=children, generate=self.generate)
        return res.strip().replace('\n', '\n  ')


class PersonView(ApplicationObjectTraverserView, ApplicationObjectDeleteMixin):
    """A view for a Person."""

    template = Template("www/person.pt", content_type="text/xml")
    authorization = PublicAccess

    def _traverse(self, name, request):
        if name == 'absences':
            return AbsenceManagementView(self.context)
        if name == 'password':
            return PersonPasswordView(self.context)
        if name == 'notes':
            return NotesView(self.context)
        return ApplicationObjectTraverserView._traverse(self, name, request)

    def getGroups(self):
        return [{'title': group.title,
                 'href': absolutePath(self.request, group)}
                for group in getRelatedObjects(self.context, URIGroup)]


class PersonPasswordView(View):
    """A view on the password of a Person."""

    do_GET = staticmethod(notFoundPage)
    authorization = PrivateAccess

    def do_PUT(self, request):
        password = request.content.read()
        password = password.strip()
        self.context.setPassword(password)
        request.appLog(_("Password changed for %s (%s)") %
                       (self.context.title, getPath(self.context)))
        request.setHeader('Content-Type', 'text/plain')
        return _("Password changed")

    def do_DELETE(self, request):
        self.context.setPassword(None)
        request.appLog(_("Account disabled for %s (%s)") %
                       (self.context.title, getPath(self.context)))
        request.setHeader('Content-Type', 'text/plain')
        return _("Account disabled")


class ResourceView(ApplicationObjectTraverserView,
                   ApplicationObjectDeleteMixin):
    """A view on a resource."""

    template = Template("www/resource.pt", content_type="text/xml")
    authorization = PublicAccess

    def _traverse(self, name, request):
        if name == 'timetables':
            return TimetableTraverseView(self.context, readonly=True)
        if name == 'booking':
            return BookingView(self.context)
        return ApplicationObjectTraverserView._traverse(self, name, request)


class NoteView(View):
    """A view on a single note"""

    authorization = PublicAccess

    template = Template("www/note.pt", content_type="text/xml")


class NotesView(ApplicationObjectTraverserView):
    """A users view on their notes of a relatable object."""

    authorization = PublicAccess

    template = Template("www/notes.pt", content_type="text/xml")


#
# Helpers
#

def delete_app_object(obj, appLog):
    """Delete an application object from the system.

    Removes `obj` from the application object container that it resides in.
    Breaks all relationships that `obj` participates in.  Unbooks any
    resources that were booked by `obj`.  Adds a note to the application
    audit log.

    `appLog` is a function that logs a message (its only argument) to the
    application audit log.  Usually it is bound to request.appLog.
    """
    assert IApplicationObject.providedBy(obj)
    assert obj.__parent__ is not None
    assert callable(appLog)

    # Remove all relationships
    while obj.listLinks():
        # If you have a loop (i.e. obj is in a relationship with itself),
        # unlink() will remove two links.  That's why a simple
        #     for link in obj.listLinks():
        #         link.unlink()
        # won't work.
        obj.listLinks()[0].unlink()
    # Remove calendar events that book resources (to unbook resources)
    events_to_remove = [e for e in obj.calendar if e.context is not None]
    for e in events_to_remove:
        obj.calendar.removeEvent(e)
    # Remove all timetables (to unbook resources)
    obj.timetables.clear()
    # Remove the object from its container
    path = getPath(obj)
    container = obj.__parent__
    del container[obj.__name__]
    # Tell the world what we've done
    appLog(_("Object deleted: %s (%s)") % (path, obj.title))


#
# Setup
#

def setUp():
    """See IModuleSetup."""
    registerView(IPerson, PersonView)
    registerView(IGroup, GroupView)
    registerView(IResource, ResourceView)
    registerView(INote, NoteView)

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
Web-application views for the schooltool.model objects.

$Id$
"""

import sets
import itertools
from cStringIO import StringIO

from schooltool.rest.cal import CalendarView as RestCalendarView
from schooltool.rest.cal import CalendarReadView as RestCalendarReadView
from schooltool.rest.infofacets import resize_photo, canonical_photo_size
from schooltool.browser import View, Template
from schooltool.browser import absoluteURL
from schooltool.browser import notFoundPage
from schooltool.browser import AppObjectBreadcrumbsMixin
from schooltool.browser.auth import AuthenticatedAccess, ManagerAccess
from schooltool.browser.auth import PrivateAccess
from schooltool.browser.auth import ACLModifyAccess, ACLViewAccess
from schooltool.browser.auth import isManager
from schooltool.browser.cal import BookingView
from schooltool.browser.acl import ACLView
from schooltool.browser.timetable import TimetableTraverseView
from schooltool.browser.cal import CalendarView
from schooltool.component import FacetManager
from schooltool.component import getRelatedObjects, relate, getPath, traverse
from schooltool.component import getTimePeriodService
from schooltool.component import getTimetableSchemaService
from schooltool.component import getOptions
from schooltool.interfaces import IPerson, IGroup, IResource, INote
from schooltool.membership import Membership
from schooltool.noted import Noted
from schooltool.translation import ugettext as _
from schooltool.uris import URIMember, URIGroup, URITeacher
from schooltool.uris import URICalendarSubscription, URICalendarSubscriber
from schooltool.uris import URICalendarProvider, URINotation
from schooltool.teaching import Teaching
from schooltool.common import to_unicode
from schooltool.browser.widgets import TextWidget, TextAreaWidget, dateParser

__metaclass__ = type


class GetParentsMixin:
    """A helper for Person and Group views."""

    def getParentGroups(self):
        """Return groups that context is a member of."""
        list = [(obj.title, obj)
                for obj in getRelatedObjects(self.context, URIGroup)]
        list.sort()
        return [obj for title, obj in list]


class PersonInfoMixin:
    """A helper for Person views."""

    def info(self):
        return FacetManager(self.context).facetByName('person_info')

    def photoURL(self):
        if self.info().photo is None:
            return u''
        else:
            return absoluteURL(self.request, self.context) + '/photo.jpg'


class TimetabledViewMixin:
    """A helper for views for ITimetabled objects."""

    def timetables(self, empty=False):
        """Return a sorted list of all composite timetables on self.context.

        If `empty` is True, also includes empty timetables in the output.

        The list contains dicts with 'title', 'url' and 'empty' in them.
        """
        periods = getTimePeriodService(self.context).keys()
        periods.sort()
        schemas = getTimetableSchemaService(self.context).keys()
        schemas.sort()
        path = absoluteURL(self.request, self.context)
        nonempty = sets.Set(self.context.listCompositeTimetables())
        return [{'title': '%s, %s' % (period, schema),
                 'url': '%s/timetables/%s/%s' % (path, period, schema),
                 'empty': (period, schema) not in nonempty}
                for period in periods
                  for schema in schemas
                    if empty or (period, schema) in nonempty]


class PersonView(View, GetParentsMixin, PersonInfoMixin, TimetabledViewMixin,
                 AppObjectBreadcrumbsMixin):
    """Person information view (/persons/id)."""

    __used_for__ = IPerson

    authorization = AuthenticatedAccess

    template = Template("www/person.pt")

    def _traverse(self, name, request):
        if name == 'photo.jpg':
            return PhotoView(self.context)
        elif name == 'edit.html':
            return PersonEditView(self.context)
        elif name == 'password.html':
            return PersonPasswordView(self.context)
        elif name == 'timetables':
            return TimetableTraverseView(self.context)
        elif name == 'calendar':
            return CalendarView(self.context.calendar)
        elif name == 'calendar.ics':
            return RestCalendarView(self.context.calendar)
        elif name == 'timetable-calendar.ics':
            return RestCalendarReadView(self.context.makeTimetableCalendar())
        raise KeyError(name)

    def canEdit(self):
        return self.isManager()

    def editURL(self):
        return absoluteURL(self.request, self.context, 'edit.html')

    def canChangePassword(self):
        user = self.request.authenticated_user
        return isManager(user) or user is self.context

    def passwordURL(self):
        return absoluteURL(self.request, self.context, 'password.html')

    canViewCalendar = canChangePassword
    canChooseCalendars = canChangePassword

    def do_POST(self, request):
        if 'CHOOSE_CALENDARS' in request.args and self.canChooseCalendars():
            # Unlink old calendar subscriptions.
            for link in self.context.listLinks(URICalendarProvider):
                link.unlink()

            # Link selected groups.
            for group in self.getParentGroups():
                if ('group.' + group.__name__) in request.args:
                    relate(URICalendarSubscription,
                           (self.context, URICalendarSubscriber),
                           (group, URICalendarProvider))
        return self.do_GET(request)

    def checked(self, group):
        for providing in getRelatedObjects(self.context,
                                           URICalendarProvider):
            if group is providing:
                return "checked"
        else:
            return None


class PersonPasswordView(View, AppObjectBreadcrumbsMixin):
    """Page for changing a person's password (/persons/id/password.html)."""

    __used_for__ = IPerson

    authorization = PrivateAccess

    template = Template('www/password.pt')

    error = None

    message = None

    back = True

    def do_POST(self, request):
        old_password = request.args['old_password'][0]
        user = request.authenticated_user
        if not user.checkPassword(old_password):
            self.error = _("Incorrect password for %s." % user.title)
        else:
            if 'DISABLE' in request.args:
                self.message = _('Account disabled.')
                self.context.setPassword(None)
                request.appLog(_("Account disabled for %s (%s)") %
                               (self.context.title, getPath(self.context)))
            elif 'CHANGE' in request.args:
                new_password = request.args['new_password'][0]
                verify_password = request.args['verify_password'][0]
                if new_password != verify_password:
                    self.error = _('Passwords do not match.')
                else:
                    self.message = _('Password changed.')
                    self.context.setPassword(new_password)
                    request.appLog(_("Password changed for %s (%s)") %
                                   (self.context.title, getPath(self.context)))
                    # XXX I'd like to redirect to the person's page
                    #     here, because current behaviour is very annoying.
        return self.do_GET(request)


class PersonEditView(View, PersonInfoMixin, AppObjectBreadcrumbsMixin):
    """Page for changing information about a person.

    Can be accessed at /persons/$id/edit.html.
    """

    __used_for__ = IPerson

    authorization = ManagerAccess

    template = Template('www/person_edit.pt')

    error = None
    duplicate_warning = False

    back = True

    def __init__(self, context):
        View.__init__(self, context)
        info = self.info()
        self.first_name_widget = TextWidget('first_name', _('First name'),
                                            value=info.first_name)
        self.last_name_widget = TextWidget('last_name', _('Last name'),
                                           value=info.last_name)
        self.dob_widget = TextWidget('date_of_birth', _('Birth date'),
                                     unit=_('(YYYY-MM-DD)'), parser=dateParser,
                                     value=info.date_of_birth)
        self.comment_widget = TextAreaWidget('comment', _('Comment'),
                                             value=info.comment)

    def do_POST(self, request):
        if 'CANCEL' in request.args:
            return self.do_GET(request)
        widgets = [self.first_name_widget, self.last_name_widget,
                   self.dob_widget, self.comment_widget]
        for widget in widgets:
            widget.update(request)

        self.first_name_widget.require()
        self.last_name_widget.require()

        infofacet = self.info()
        full_name = (self.first_name_widget.value,
                     self.last_name_widget.value)
        allow_duplicates = 'CONFIRM' in request.args
        if ((infofacet.first_name, infofacet.last_name) != full_name
            and not allow_duplicates):
            for otheruser in self.context.__parent__.itervalues():
                other_info = FacetManager(otheruser).facetByName('person_info')
                if (other_info.first_name, other_info.last_name) == full_name:
                    self.error = _("Another user with this name already"
                                   " exists.")
                    self.duplicate_warning = True
                    return self.do_GET(request)

        for widget in widgets:
            if widget.error:
                return self.do_GET(request)

        first_name = self.first_name_widget.value
        last_name = self.last_name_widget.value
        dob = self.dob_widget.value
        comment = self.comment_widget.value
        remove_photo = 'REMOVE_PHOTO' in request.args
        photo = request.args.get('photo', [None])[0]

        if photo and not remove_photo:
            try:
                photo = resize_photo(StringIO(photo), canonical_photo_size)
            except IOError:
                self.error = _('Invalid photo')
                return self.do_GET(request)

        infofacet.first_name = first_name
        infofacet.last_name = last_name
        infofacet.date_of_birth = dob
        infofacet.comment = comment

        request.appLog(_("Person info updated on %s (%s)") %
                       (self.context.title, getPath(self.context)))

        if remove_photo:
            infofacet.photo = None
            request.appLog(_("Photo removed from %s (%s)") %
                           (self.context.title, getPath(self.context)))
        elif photo:
            infofacet.photo = photo
            request.appLog(_("Photo added on %s (%s)") %
                           (self.context.title, getPath(self.context)))

        url = absoluteURL(request, self.context)
        return self.redirect(url, request)


class GroupView(View, GetParentsMixin, TimetabledViewMixin,
                AppObjectBreadcrumbsMixin):
    """Group information view (/group/id)."""

    __used_for__ = IGroup

    authorization = ACLViewAccess

    template = Template("www/group.pt")

    def _traverse(self, name, request):
        if name == "edit.html":
            return GroupEditView(self.context)
        if name == "edit_subgroups.html":
            return GroupSubgroupView(self.context)
        elif name == "teachers.html":
            return GroupTeachersView(self.context)
        elif name == 'acl.html':
            return ACLView(self.context.acl)
        elif name == 'calendar':
            return CalendarView(self.context.calendar)
        elif name == 'timetables':
            return TimetableTraverseView(self.context)
        raise KeyError(name)

    def getOtherMembers(self):
        """Return members that are not groups."""
        list = [(obj.title, obj)
                for obj in getRelatedObjects(self.context, URIMember)
                    if not IGroup.providedBy(obj)]
        list.sort()
        return [obj for title, obj in list]

    def getSubGroups(self):
        """Return members that are groups."""
        list = [(obj.title, obj)
                for obj in getRelatedObjects(self.context, URIMember)
                    if IGroup.providedBy(obj)]
        list.sort()
        return [obj for title, obj in list]

    def teachersList(self):
        """Lists teachers of this group"""
        list = [(obj.title, obj)
                for obj in getRelatedObjects(self.context, URITeacher)]
        list.sort()
        return [obj for title, obj in list]

    def canEdit(self):
        return isManager(self.request.authenticated_user)


class RelationshipViewMixin:
    """A mixin for views that manage relationships on groups.

    Subclasses must define:

      linkrole = Attribute('URI of the role of the related object.')

      relname = Attribute('Relationship name')

      def createRelationship(self, other):
          'Create the relationship between self.context and other'

      errormessage = Attribute('A translated error that is displayed'
                               'when the relationship creation fails'
    """

    errormessage = property(lambda self: _("Cannot create relationship between"
                                           " %(other)s and %(this)s"))

    def list(self):
        """Return a list of related objects."""
        return self._list(getRelatedObjects(self.context, self.linkrole))

    def _list(self, objects):
        """Return a list of related objects."""
        # TODO: Get rid of this method and instead rewrite page templates to
        #       use whatever/obj/@@absolute_url instead of whatever/obj/url
        #       and replace self._list(...) with app_object_list(...)
        results = app_object_list(objects)
        for d in results:
            obj = d['obj']
            d['path'] = getPath(obj)
            d['url'] = absoluteURL(self.request, obj)
            del d['obj']
        return results

    def update(self):
        request = self.request
        if "DELETE" in request.args:
            paths = sets.Set(request.args.get("CHECK", []))
            for link in self.context.listLinks(self.linkrole):
                if getPath(link.traverse()) in paths:
                    link.unlink()
                    request.appLog(_("Relationship '%s' between %s and %s"
                                     " removed")
                                   % (self.relname, getPath(link.traverse()),
                                      getPath(self.context)))
        if "FINISH_ADD" in request.args:
            paths = filter(None, request.args.get("toadd", []))
            for path in paths:
                obj = traverse(self.context, path)
                try:
                    self.createRelationship(obj)
                except ValueError:
                    return self.errormessage % {'other': obj.title,
                                                'this': self.context.title}
                request.appLog(_("Relationship '%s' between %s and %s created")
                               % (self.relname, getPath(obj),
                                  getPath(self.context)))


class GroupEditView(View, RelationshipViewMixin, AppObjectBreadcrumbsMixin):
    """Page for "editing" a Group (/group/id/edit.html)."""

    __used_for__ = IGroup

    authorization = ACLModifyAccess

    template = Template('www/group_edit.pt')

    linkrole = URIMember

    relname = property(lambda self: _('Membership'))

    back = True

    errormessage = property(lambda self: _("Cannot add %(other)s to %(this)s"))

    edit_subgroups = False

    def addList(self):
        """Return a list of objects available for adding."""
        try:
            searchstr = to_unicode(self.request.args['SEARCH'][0]).lower()
        except UnicodeError:
            return []
        members = sets.Set(getRelatedObjects(self.context, URIMember))
        addable = []
        restrict_membership = getOptions(self.context).restrict_membership
        for obj in self._source(restrict_membership):
            if (searchstr in obj.title.lower() and obj not in members):
                addable.append(obj)
        # 'obj not in members' is not strong enough; we should check for
        # transitive membership as well
        return self._list(addable)

    def createRelationship(self, other):
        Membership(group=self.context, member=other)

    def _source(self, restrict_membership):
        if restrict_membership:
            parents = getRelatedObjects(self.context, URIGroup)
            siblings = itertools.chain(*[getRelatedObjects(parent, URIMember)
                                         for parent in parents])
            return [member for member in siblings
                           if IPerson.providedBy(member)
                              or IResource.providedBy(member)]
        else:
            return itertools.chain(
                        traverse(self.context, '/persons').itervalues(),
                        traverse(self.context, '/resources').itervalues())

    def _list(self, objects):
        objs = [obj for obj in objects
                if IPerson.providedBy(obj) or IResource.providedBy(obj)]
        return RelationshipViewMixin._list(self, objs)


class GroupSubgroupView(GroupEditView):
    """A view to add subgroups to a group."""

    edit_subgroups = True

    def _source(self, restrict_membership):
        return traverse(self.context, '/groups').itervalues()

    def _list(self, objects):
        groups = [obj for obj in objects if IGroup.providedBy(obj)]
        return RelationshipViewMixin._list(self, groups)


class GroupTeachersView(View, RelationshipViewMixin,
                        AppObjectBreadcrumbsMixin):

    __used_for__ = IGroup

    authorization = ACLModifyAccess

    template = Template('www/group_teachers.pt')

    linkrole = URITeacher

    relname = property(lambda self: _('Teaching'))

    back = True

    errormessage = property(lambda self: _("Cannot add teacher"
                                           " %(other)s to %(this)s"))

    def addList(self):
        """List all members of the Teachers group except current teachers."""
        current_teachers = getRelatedObjects(self.context, URITeacher)
        teachers = traverse(self.context, '/groups/teachers')
        addable = [obj for obj in getRelatedObjects(teachers, URIMember)
                           if obj not in current_teachers]
        return self._list(addable)

    def createRelationship(self, other):
        Teaching(taught=self.context, teacher=other)


class ResourceView(View, GetParentsMixin, AppObjectBreadcrumbsMixin):
    """View for displaying a resource."""

    __used_for__ = IResource

    authorization = AuthenticatedAccess

    template = Template("www/resource.pt")

    def canEdit(self):
        return isManager(self.request.authenticated_user)

    def editURL(self):
        return absoluteURL(self.request, self.context) + '/edit.html'

    def _traverse(self, name, request):
        if name == "edit.html":
            return ResourceEditView(self.context)
        elif name == "book":
            return BookingView(self.context)
        elif name == 'acl.html':
            return ACLView(self.context.acl)
        elif name == 'calendar':
            return CalendarView(self.context.calendar)
        elif name == 'timetables':
            return TimetableTraverseView(self.context)
        else:
            raise KeyError(name)


class ResourceEditView(View, AppObjectBreadcrumbsMixin):
    """View for displaying a resource."""

    __used_for__ = IResource

    authorization = ManagerAccess

    template = Template("www/resource_edit.pt")

    duplicate_warning = False

    back = True

    def __init__(self, context):
        View.__init__(self, context)
        self.title_widget = TextWidget('title', _('Title'),
                                       value=context.title)

    def do_POST(self, request):
        if 'CANCEL' in request.args:
            return self.do_GET(request)
        self.title_widget.update(request)
        if self.title_widget.raw_value == '':
            self.title_widget.setRawValue(None)
        self.title_widget.require()
        if self.title_widget.error:
            return self.do_GET(request)
        new_title = self.title_widget.value
        if new_title != self.context.title:
            if 'CONFIRM' not in request.args:
                for other in self.context.__parent__.itervalues():
                    if new_title == other.title:
                        self.duplicate_warning = True
                        self.title_widget.error = ("This title is already used"
                                                   " for another resource.")
                        return self.do_GET(request)
            self.context.title = self.title_widget.value
            request.appLog(_("Resource %s modified") % getPath(self.context))
        url = absoluteURL(request, self.context)
        return self.redirect(url, request)


class NoteView(View, GetParentsMixin, AppObjectBreadcrumbsMixin):
    """View for displaying a note."""

    __used_for__ = INote

    authorization = AuthenticatedAccess

    template = Template("www/note.pt")

    def canEdit(self):
        # Right now we only want to be editible by the owner
        user = request.authenticated_user
        return user == context.owner

    def editURL(self):
        return absoluteURL(self.request, self.context, 'edit.html')

    def _traverse(self, name, request):
        if name == "edit.html":
            return NoteEditView(self.context)
        else:
            raise KeyError(name)


class NoteEditView(View, RelationshipViewMixin, AppObjectBreadcrumbsMixin):
    """Page for "editing" a Note (/notes/id/edit.html)."""

    authorization = AuthenticatedAccess

    template = Template('www/note_edit.pt')

    linkrole = URINotation

    relname = property(lambda self: _('Noted'))

    back = True

    errormessage = property(lambda self: _("Cannot edit %(note)s to %(this)s"))

    def createRelationship(self, other):
        Noted(notation=self.context, notandum=other)

    def __init__(self, context):
        View.__init__(self, context)
        self.title_widget = TextWidget('title', _('Title'),
                                       value=context.title)
        self.body_widget = TextAreaWidget('body', _('Note'), value=info.body)

    def do_POST(self, request):
        if 'CANCEL' in request.args:
            return self.do_GET(request)

        widgets = [self.title_widget, self.body_widget]

        for widget in widgets:
            widget.update(request)

        # This is how to require a field.  Do we want any required here?
        #self.country_widget.require()

        allow_duplicates = 'CONFIRM' in request.args

        for widget in widgets:
            if widget.error:
                return self.do_GET(request)

        title = self.title_widget.value
        body = self.body_widget.value

        request.appLog(_("Note info updated on %s (%s)") %
                       (self.context.title, getPath(self.context)))

        url = absoluteURL(request, self.context)
        return self.redirect(url, request)


class PhotoView(View):
    """View for displaying a person's photo (/persons/id/photo.jpg)."""

    __used_for__ = IPerson

    authorization = AuthenticatedAccess

    def do_GET(self, request):
        facet = FacetManager(self.context).facetByName('person_info')
        if facet.photo is None:
            return notFoundPage(request)
        else:
            request.setHeader('Content-Type', 'image/jpeg')
            return facet.photo


def app_object_icon(obj):
    """Select the appropriate icon for an application object.

    Returns (image_url, alt_text).
    """
    if IPerson.providedBy(obj):
        return '/person.png', _('Person')
    elif IGroup.providedBy(obj):
        return '/group.png', _('Group')
    elif IResource.providedBy(obj):
        return '/resource.png', _('Resource')
    else:
        return None, obj.__class__.__name__


def app_object_list(objects):
    """Prepare a list of application objects for presentation.

    Sorts the list first by type, then by group.

    Returns a list of dicts with the following keys

      title      Title of the object.
      obj        The object itself.
      icon_url   URL of the icon image.
      icon_text  Alternative text for the icon.
    """
    result = [app_object_icon(obj) + (obj.title, obj) for obj in objects]
    result.sort()
    return [{'title': title,
             'obj': obj,
             'icon_url': icon_url,
             'icon_text': icon_text}
            for icon_url, icon_text, title, obj in result]

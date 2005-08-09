#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
SchoolBell application interfaces

Overview
--------

ISchoolBellApplication is the main interface.  From it you can get to all
persons, groups and resources in the system via IPersonContainer,
IGroupContainer and IResourceContainer.

Persons, as described by IPerson, are users of the system.  Groups and
resources (IGroup, IResource) are passive objects.  Groups may contain
persons and resources, but there are no additional semantics attached
to group membership (at the time of this writing).

IPersonContained, IGroupContained and IResourceContained describe persons,
groups and resources in context of the rest of the application.  Partly it is
done to avoid a circular dependency between IXxxContained and IXxxContainer.

$Id$
"""

import calendar

import zope.interface
import zope.schema

import zope.app.event.objectevent
import zope.app.container.constraints
from zope.app import container
from zope.app import event
from zope.app.annotation.interfaces import IAnnotatable
from zope.app.location.interfaces import ILocation
from zope.app.security.interfaces import IAuthentication, ILogout

import pytz

from schoolbell import SchoolBellMessageID as _
from schoolbell.calendar.interfaces import IEditCalendar, ICalendarEvent


# Dirty hacks that provide sensible i10n for widget error messages.
# See issue #221 (http://issues.schooltool.org/issue221).
from zope.schema.interfaces import RequiredMissing
RequiredMissing.__doc__ = _("""Required input is missing.""")

import zope.app.form.browser.textwidgets
zope.app.form.browser.textwidgets._ = _
# Here we do a particulary evil thing: we override the translation (_) function
# in the textwidgets module.  This means that all the messages in that module
# are now in the 'schoolbell' domain.  This is the list of the messages
# (don't remove the list, it is used in localizable string extraction).
textwidgets_strings=[_('Form input is not a file object'),
                     _("Invalid integer data"),
                     _("Invalid text data"),
                     _("Invalid textual data"),
                     _("Invalid unicode data"),
                     _("Invalid integer data"),
                     _("Invalid floating point data"),
                     _("Invalid datetime data")]


def vocabulary(choices):
    """Create a SimpleVocabulary from a list of values and titles.

    >>> v = vocabulary([('value1', u"Title for value1"),
    ...                 ('value2', u"Title for value2")])
    >>> for term in v:
    ...   print term.value, '|', term.token, '|', term.title
    value1 | value1 | Title for value1
    value2 | value2 | Title for value2

    """
    return zope.schema.vocabulary.SimpleVocabulary(
        [zope.schema.vocabulary.SimpleTerm(v, title=t) for v, t in choices])


# Events

class IApplicationInitializationEvent(event.interfaces.IObjectEvent):
    """The SchoolTool application is being initiazed.

    Usually subscribers add soemthing to the initialization process.
    """

class ApplicationInitializationEvent(event.objectevent.ObjectEvent):
    zope.interface.implements(IApplicationInitializationEvent)


class ISchoolBellCalendar(IEditCalendar, ILocation):
    """A SchoolBell calendar.

    Calendars stored within all provide ISchoolBellCalendarEvent.
    """

    title = zope.schema.TextLine(
        title=u"Title",
        description=u"Title of the calendar.")


class ISchoolBellCalendarEvent(ICalendarEvent,
                               container.interfaces.IContained):
    """An event that is contained in a SchoolBell calendar."""

    resources = zope.interface.Attribute(
        """Resources that are booked by this event""")

    def bookResource(resource):
        """Book a resource."""

    def unbookResource(resource):
        """Book a resource."""


class IHaveNotes(IAnnotatable):
    """An object that can have Notes.

    See also INote and INotes.
    """


class INote(zope.interface.Interface):
    """A note."""

    title = zope.schema.TextLine(
        title=_("Title"),
        description=_("Title of the note."))

    body = zope.schema.Text(
        title=_("Body"),
        description=_("Body of the note."))

    privacy = zope.schema.Choice(
        title=_("Privacy"),
        values=('private', 'public'),
        description=u"""
        Determines who can view the note.

        Can be one of two values: 'private', 'public'

        'private'  the note can only be viewed by the creator of the note.

        'public'   anyone can view the note, including anonymous users.

        """)

    owner = zope.interface.Attribute("""IPerson who owns this note""")

    unique_id = zope.schema.TextLine(
        title=u"UID",
        required=False,
        description=u"""A globally unique id for this note.""")


class INotes(zope.interface.Interface):
    """A set of notes.

    Objects that can have notes are those that have an adapter to INotes.

    See also `INote`.
    """

    def __iter__():
        """Iterate over all notes."""

    def add(note):
        """Add a new note."""

    def remove(note):
        """Remove a note.

        Raises ValueError if note is not in the set.
        """

    def clear():
        """Remove all notes."""


class ICalendarOwner(zope.interface.Interface):
    """An object that has a calendar."""

    calendar = zope.schema.Object(
        title=u"The object's calendar.",
        schema=ISchoolBellCalendar)


class IGroupMember(zope.interface.Interface):
    """An object that knows the groups it is a member of."""

    groups = zope.interface.Attribute("""Groups (see IRelationshipProperty)""")


class IHavePreferences(IAnnotatable):
    """An object that can have preferences. Namely a Person."""


class IReadPerson(IGroupMember):
    """Publically accessible part of IPerson."""

    title = zope.schema.TextLine(
        title=_("Full name"),
        description=_("Name that should be displayed"))

    photo = zope.schema.Bytes(
        title=_("Photo"),
        required=False,
        description=_("""Photo (in JPEG format)"""))

    username = zope.schema.TextLine(
        title=_("Username"))

    overlaid_calendars = zope.interface.Attribute(
        """Additional calendars to overlay.

            A user may select a number of calendars that should be displayed in
            the calendar view, in addition to the user's calendar.

            This is a relationship property.""") # XXX Please use a Field.

    def checkPassword(password):
        """Check if the provided password is the same as the one set
        earlier using setPassword.

        Returns True if the passwords match.
        """

    def hasPassword():
        """Check if the user has a password.

        You can remove user's password (effectively disabling the account) by
        passing None to setPassword.  You can reenable the account by passing
        a new password to setPassword.
        """


class IWritePerson(zope.interface.Interface):
    """Protected part of IPerson."""

    def setPassword(password):
        """Set the password in a hashed form, so it can be verified later.

        Setting password to None disables the user account.
        """


class IPerson(IReadPerson, IWritePerson, ICalendarOwner):
    """Person.

    A person has a number of informative fields such as name, an optional
    photo, and so on.

    A person can also be a user of the system, therefore IPerson defines
    `username`, and methods for setting/checking passwords (`setPassword`,
    `checkPassword` and `hasPassword`).

    Use IPersonContained instead if you want a person in context (that is,
    one that you can use to traverse to other persons/groups/resources).
    """


class IPersonContainer(container.interfaces.IContainer):
    """Container of persons."""

    container.constraints.contains(IPerson)


class IPersonContained(IPerson, container.interfaces.IContained):
    """Person contained in an IPersonContainer."""

    container.constraints.containers(IPersonContainer)


class IPersonPreferences(zope.interface.Interface):
    """Preferences stored in an annotation on a person."""

    __parent__ = zope.interface.Attribute(
        """Person who owns these preferences""")

    timezone = zope.schema.Choice(
        title=_("Time Zone"),
        description=_("Time Zone used to display your calendar"),
        values=pytz.common_timezones)

    timeformat = zope.schema.Choice(
        title=_("Time Format"),
        description=_("Time Format"),
        vocabulary=vocabulary([("%H:%M", _("HH:MM")),
                               ("%I:%M %p", _("HH:MM am/pm"))]))

    dateformat = zope.schema.Choice(
        title=_("Date Format"),
        description=_("Date Format"),
        vocabulary=vocabulary([("%m/%d/%y", _("MM/DD/YY")),
                               ("%Y-%m-%d", _("YYYY-MM-DD")),
                               ("%d %B, %Y", _("Day Month, Year"))]))

    # SUNDAY and MONDAY are integers, 6 and 0 respectivley
    weekstart = zope.schema.Choice(
        title=_("Week starts on:"),
        description=_("Start display of weeks on Sunday or Monday"),
        vocabulary=vocabulary([(calendar.SUNDAY, _("Sunday")),
                               (calendar.MONDAY, _("Monday"))]))

    # XXX: Only available in SchoolTool, but that's ok for now.
    cal_periods = zope.schema.Bool(
        title=_("Show periods"),
        description=_("Show period names in daily view"))


class IPersonDetails(ILocation):
    """Contacts details stored as an annotation on a Person."""

    nickname = zope.schema.TextLine(
        title=_("Nickname"),
        required=False,
        description=_("A short nickname for this person."))

    primary_email = zope.schema.TextLine(
        title=_("Primary Email"),
        required=False)

    secondary_email = zope.schema.TextLine(
        title=_("Secondary Email"),
        required=False)

    primary_phone = zope.schema.TextLine(
        title=_("Primary phone"),
        required=False,
        description=_("Recommended telephone number."))

    secondary_phone = zope.schema.TextLine(
        title=_("Secondary phone"),
        required=False,
        description=_("Secondary telephone number."))

    home_page = zope.schema.TextLine(
        title=_("Website"),
        required=False,
        description=_("Website or weblog."))

    mailing_address = zope.schema.Text(
        title=_("Mailing address"),
        required=False)


class IGroup(ICalendarOwner):
    """Group."""

    title = zope.schema.TextLine(
        title=_("Title"),
        description=_("Title of the group."))

    description = zope.schema.Text(
        title=_("Description"),
        required=False,
        description=_("Description of the group."))

    members = zope.interface.Attribute(
        """Members of the group (see IRelationshipProperty)""")


class IGroupContainer(container.interfaces.IContainer):
    """Container of groups."""

    container.constraints.contains(IGroup)


class IGroupContained(IGroup, container.interfaces.IContained):
    """Group contained in an IGroupContainer."""

    container.constraints.containers(IGroupContainer)


class IResource(ICalendarOwner):
    """Resource."""

    title = zope.schema.TextLine(
        title=_("Title"),
        description=_("Title of the resource."))

    description = zope.schema.Text(
        title=_("Description"),
        required=False,
        description=_("Description of the resource."))

    isLocation = zope.schema.Bool(
        title=_("A Location."),
        description=_(
            """Indicate this resource is a location, like a classroom."""),
        required=False,
        default=False)

class IResourceContainer(container.interfaces.IContainer):
    """Container of resources."""

    container.constraints.contains(IResource)


class IResourceContained(IResource, container.interfaces.IContained):
    """Group contained in an IGroupContainer."""

    container.constraints.containers(IResourceContainer)


class ISchoolBellApplication(container.interfaces.IReadContainer,
                             ICalendarOwner):
    """The main SchoolBell application object.

    The application is a read-only container with the following items:

        'persons' - IPersonContainer
        'groups' - IGroupContainer
        'resources' - IResourceContainer

    This object can be added as a regular content object to a folder, or
    it can be used as the application root object.
    """

    title = zope.schema.TextLine(
        title=_("Title"),
        description=_("Title of the application."))


class IApplicationPreferences(zope.interface.Interface):
    """Preferences stored in an annotation on the SchoolBellApplication."""

    title = zope.schema.TextLine(
        title=_("Title"),
        required=False,
        description=_("""The name for the school or organization running
            this server.  This will be displayed on the public calendar, the
            bottom of all pages and in the page title."""))

    frontPageCalendar = zope.schema.Bool(
        title=_("Front Page Calendar"),
        description=_("""Display site-wide calendar as the front page of the
            site."""),
        required=False,
        default=True)


class ISchoolBellAuthentication(IAuthentication, ILogout):
    """A local authentication utility for SchoolBell"""

    def setCredentials(request, username, password):
        """Save the username and password in the session.

        If the credentials passed are invalid, ValueError is raised.
        """

    def clearCredentials(request):
        """Forget the username and password stored in a session"""


class IWriteCalendar(zope.interface.Interface):

    def write(data, charset='UTF-8'):
        """Update the calendar data
        """

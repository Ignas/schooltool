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
r"""
Browser views for schoolbell.calendar.

$Id$

iCalendar views
---------------

CalendarICalendarView can export calendars in iCalendar format

    >>> from datetime import datetime, timedelta
    >>> from schoolbell.calendar.simple import ImmutableCalendar
    >>> from schoolbell.calendar.simple import SimpleCalendarEvent
    >>> event = SimpleCalendarEvent(datetime(2004, 12, 16, 11, 46, 16),
    ...                             timedelta(hours=1), "doctests",
    ...                             location=u"Matar\u00f3",
    ...                             unique_id="12345678-5432@example.com")
    >>> calendar = ImmutableCalendar([event])

    >>> from zope.publisher.browser import TestRequest
    >>> view = CalendarICalendarView()
    >>> view.context = calendar
    >>> view.request = TestRequest()
    >>> output = view.show()

    >>> lines = output.splitlines(True)
    >>> from pprint import pprint
    >>> pprint(lines)
    ['BEGIN:VCALENDAR\r\n',
     'VERSION:2.0\r\n',
     'PRODID:-//SchoolTool.org/NONSGML SchoolBell//EN\r\n',
     'BEGIN:VEVENT\r\n',
     'UID:12345678-5432@example.com\r\n',
     'SUMMARY:doctests\r\n',
     'LOCATION:Matar\xc3\xb3\r\n',
     'DTSTART:20041216T114616\r\n',
     'DURATION:PT1H\r\n',
     'DTSTAMP:...\r\n',
     'END:VEVENT\r\n',
     'END:VCALENDAR\r\n']

     The last line must end in '\r\n' see RFC 2445 4.4.

Register the iCalendar read view in ZCML as

    <browser:page
        for="schoolbell.calendar.interfaces.ICalendar"
        name="calendar.ics"
        permission="zope.Public"
        class="schoolbell.calendar.browser.CalendarICalendarView"
        attribute="show"
        />

"""

from schoolbell.calendar.icalendar import convert_calendar_to_ical

__metaclass__ = type


class CalendarICalendarView:
    """RFC 2445 (ICalendar) view for calendars."""

    def show(self):
        data = "\r\n".join(convert_calendar_to_ical(self.context)) + "\r\n"
        request = self.request
        if request is not None:
            request.response.setHeader('Content-Type',
                                       'text/calendar; charset=UTF-8')
            request.response.setHeader('Content-Length', len(data))

        return data


#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
Timetables are meeting schedules created from scheduled day templates.
"""
import pytz
import datetime

from persistent import Persistent
from persistent.list import PersistentList
from persistent.dict import PersistentDict
from zope.interface import implements
from zope.container.btree import BTreeContainer
from zope.component import getUtility
from zope.intid.interfaces import IIntIds

from schooltool.common import DateRange
from schooltool.timetable import interfaces
from schooltool.timetable.schedule import Meeting, Schedule
from schooltool.timetable.schedule import iterMeetingsInTimezone
from schooltool.timetable.schedule import iterMeetingsWithExceptions


class Timetable(Persistent, Schedule):
    implements(interfaces.ITimetable)

    periods = None
    time_slots = None
    exceptions = None

    def __init__(self, *args, **kw):
        Persistent.__init__(self)
        Schedule.__init__(self, *args, **kw)
        self.exceptions = PersistentDict()

    def uniqueMeetingId(self, date, period, int_ids):
        date_id = date.isoformat()
        period_id = int_ids.getId(period)
        uid = '%s.%s' % (date_id, period_id)
        return uid

    def iterOriginalMeetings(self, from_date, until_date=None):
        if until_date is None:
            until_date = from_date
        timezone = pytz.timezone(self.timezone)
        int_ids = getUtility(IIntIds)

        dates = DateRange(from_date, until_date)
        days = zip(dates,
                   self.periods.iterDates(dates),
                   self.time_slots.iterDates(dates))
        for day_date, day_periods, day_time_slots in days:
            if day_periods is None:
                continue
            day = combineTemplates(day_periods, day_time_slots)
            for period, time_slot in day:
                tstart = time_slot.tstart
                dtstart = datetime.datetime.combine(day_date, tstart)
                dtstart = dtstart.replace(tzinfo=timezone)
                meeting_id = self.uniqueMeetingId(day_date, period, int_ids)
                meeting = Meeting(
                    dtstart, time_slot.duration,
                    period=period,
                    meeting_id=meeting_id)
                yield meeting

    def iterMeetings(self, date, until_date=None):
        meetings = self.iterOriginalMeetings(date, until_date=until_date)

        return iterMeetingsWithExceptions(
            meetings, self.exceptions, self.timezone,
            date, until_date=until_date)


def combineTemplates(periods_template, time_slots_template):
    """Return ordered list of period, time_slot tuples."""
    result = []
    periods_by_activity = {}
    period_queue = periods_template.values()
    for period in period_queue:
        if period.activity_type not in periods_by_activity:
            periods_by_activity[period.activity_type] = []
        periods_by_activity[period.activity_type].append(period)

    for time_slot in sorted(time_slots_template.values()):
        activity = time_slot.activity_type
        if activity is not None:
            if (activity not in periods_by_activity or
                not periods_by_activity[activity]):
                continue # no more periods for this activity
            period = periods_by_activity[activity].pop(0)
            period_queue.remove(period)
            result.append((period, time_slot))
        else:
            period = period_queue.pop(0)
            periods_by_activity[period.activity_type].remove(period)
            result.append((period, time_slot))
    return result


class TimetableContainer(BTreeContainer):
    implements(interfaces.ITimetableContainer)

    default_id = None

    @property
    def default(self):
        if self.default_id is None:
            return None
        return self.get(self.default_id, None)

    @default.setter
    def default(self, timetable):
        if timetable is None:
            self.default_id = None
            return
        key = timetable.__name__
        if key not in self:
            raise KeyError(key)
        self.default_id = key


class SelectedPeriodsSchedule(Persistent, Schedule):
    implements(interfaces.ISelectedPeriodsSchedule)

    # XXX: think about storing intid here
    # or maybe better - a relationship
    timetable = None

    _periods = None

    consecutive_periods_as_one = False

    def __init__(self, timetable, *args, **kw):
        Schedule.__init__(self, *args, **kw)
        self.timetable = timetable
        self._periods = PersistentList()

    @property
    def periods(self):
        result = []
        for day in self.timetable.periods.templates.values():
            result.extend([period for period in day.values()
                           if self.hasPeriod(period)])
        return result

    def periodKey(self, period):
        day = period.__parent__
        return (day.__name__, period.__name__)

    def hasPeriod(self, period):
        key = self.periodKey(period)
        return key in self._periods

    def addPeriod(self, period):
        key = self.periodKey(period)
        if key not in self._periods:
            self._periods.append(key)

    def removePeriod(self, period):
        key = self.periodKey(period)
        if key in self._periods:
            self._periods.remove(key)

    def iterMeetings(self, date, until_date=None):
        if self.timetable is None:
            return
        meetings = iterMeetingsInTimezone(
            self.timetable, self.timezone, date, until_date=until_date)
        selected_periods = list(self.periods)
        for meeting in meetings:
            # XXX: update meetings by consecutive_periods_as_one
            # XXX: proxy issues may breed here
            if meeting.period in selected_periods:
                yield meeting

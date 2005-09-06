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
Unit tests for schoolbell.calendar.recurrent.

$Id$
"""

import unittest
from datetime import datetime, date, timedelta
from zope.interface.verify import verifyObject


class RecurrenceRuleTestBase:
    """Base tests for the recurrence rules"""

    def test_comparison(self):
        d = self.createRule()
        d2 = d.replace()
        d3 = d.replace(count=2)
        assert d is not d2
        self.assertEqual(d, d2)
        assert not d != d2
        self.assertEqual(hash(d), hash(d2))
        assert d != None
        assert d < None or d > None
        assert d3 < d or d < d3

    def test_replace(self):
        rule = self.createRule(interval=1, until=date(2005, 1, 1))
        assert rule == rule.replace()
        rule2 = rule.replace(until=None, count=20)
        assert rule != rule2
        self.assertRaises(ValueError, rule.replace, count=20)

    def test_validate(self):
        self.assertRaises(ValueError, self.createRule, count=3,
                          until=date.today())
        self.assertRaises(ValueError, self.createRule, exceptions=(1,))
        self.assertRaises(ValueError, self.createRule, interval=0)
        self.assertRaises(ValueError, self.createRule, interval=-1)
        self.createRule(exceptions=(date.today(),))
        self.createRule(until=date.today())
        self.createRule(count=42)

    def test_iCalRepresentation(self):
        # simple case
        rule = self.createRule(interval=2)
        freq = rule.ical_freq
        self.assertEquals(rule.iCalRepresentation(None),
                          ['RRULE:FREQ=%s;INTERVAL=2' % freq])

        # count
        rule = self.createRule(interval=3, count=5)
        self.assertEquals(rule.iCalRepresentation(None),
                          ['RRULE:FREQ=%s;COUNT=5;INTERVAL=3' % freq])

        # until
        rule = self.createRule(until=date(2004, 10, 20))
        self.assertEquals(rule.iCalRepresentation(None),
                          ['RRULE:FREQ=%s;UNTIL=20041020T000000;INTERVAL=1'
                           % freq])

        # exceptions
        rule = self.createRule(exceptions=[date(2004, 10, 2*d)
                                           for d in range(3, 6)])
        self.assertEquals(rule.iCalRepresentation(None),
                          ['RRULE:FREQ=%s;INTERVAL=1' % freq,
                           'EXDATE;VALUE=DATE:20041006,20041008,20041010'])

    def test_immutability(self):
        r = self.createRule()
        for attrname in ['interval', 'count', 'until', 'exceptions']:
            self.assertRaises(AttributeError, setattr, r, attrname, 'not-ro')


class TestDailyRecurrenceRule(unittest.TestCase, RecurrenceRuleTestBase):

    def createRule(self, *args, **kwargs):
        from schoolbell.calendar.recurrent import DailyRecurrenceRule
        return DailyRecurrenceRule(*args, **kwargs)

    def test(self):
        from schoolbell.calendar.interfaces import IDailyRecurrenceRule
        rule = self.createRule()
        verifyObject(IDailyRecurrenceRule, rule)

    def test_apply(self):
        from schoolbell.calendar.simple import SimpleCalendarEvent
        rule = self.createRule()
        ev = SimpleCalendarEvent(datetime(2004, 10, 13, 12, 0),
                           timedelta(minutes=10),
                           "reality check", unique_id='uid')

        # The event happened after the range -- empty result
        result = list(rule.apply(ev, enddate=date(2003, 10, 1)))
        self.assertEqual(result, [])

        # Simplest case
        result = list(rule.apply(ev, enddate=date(2004, 10, 20)))
        self.assertEqual(result, [date(2004, 10, d) for d in range(13, 21)])

        # With an end date
        rule = self.createRule(until=date(2004, 10, 20))
        result = list(rule.apply(ev))
        self.assertEqual(result, [date(2004, 10, d) for d in range(13, 21)])

        # With an end date as datetime, see issue318
        rule = self.createRule(until=datetime(2004, 10, 20))
        result = list(rule.apply(ev))
        self.assertEqual(result, [date(2004, 10, d) for d in range(13, 21)])

        # With a count
        rule = self.createRule(count=8)
        result = list(rule.apply(ev))
        self.assertEqual(result, [date(2004, 10, d) for d in range(13, 21)])

        # With an interval
        rule = self.createRule(interval=2)
        result = list(rule.apply(ev, enddate=date(2004, 10, 20)))
        self.assertEqual(result, [date(2004, 10, d) for d in range(13, 21, 2)])

        # With exceptions
        rule = self.createRule(exceptions=[date(2004, 10, d)
                                           for d in range(16, 21)])
        result = list(rule.apply(ev, enddate=date(2004, 10, 20)))
        self.assertEqual(result, [date(2004, 10, d) for d in range(13, 16)])

        # With exceptions and count -- exceptions are excluded after
        # counting
        rule = self.createRule(exceptions=[date(2004, 10, d)
                                           for d in range(16, 21)],
                               count=6)
        result = list(rule.apply(ev, enddate=date(2004, 10, 20)))
        self.assertEqual(result, [date(2004, 10, 13), date(2004, 10, 14),
                                  date(2004, 10, 15)])


class TestYearlyRecurrenceRule(unittest.TestCase, RecurrenceRuleTestBase):

    def createRule(self, *args, **kwargs):
        from schoolbell.calendar.recurrent import YearlyRecurrenceRule
        return YearlyRecurrenceRule(*args, **kwargs)

    def test(self):
        from schoolbell.calendar.interfaces import IYearlyRecurrenceRule
        rule = self.createRule()
        verifyObject(IYearlyRecurrenceRule, rule)

    def test_apply(self):
        from schoolbell.calendar.simple import SimpleCalendarEvent
        rule = self.createRule()
        ev = SimpleCalendarEvent(datetime(1978, 5, 17, 12, 0),
                           timedelta(minutes=10),
                           "reality check", unique_id='uid')

        # The event happened after the range -- empty result
        result = list(rule.apply(ev, enddate=date(1970, 1, 1)))
        self.assertEqual(result, [])

        # Simplest case
        result = list(rule.apply(ev, enddate=date(2004, 10, 20)))
        self.assertEqual(result, [date(y, 5, 17) for y in range(1978, 2005)])

        # With an end date
        rule = self.createRule(until=date(2004, 10, 20))
        result = list(rule.apply(ev))
        self.assertEqual(result, [date(y, 5, 17) for y in range(1978, 2005)])

        # With a count
        rule = self.createRule(count=8)
        result = list(rule.apply(ev))
        self.assertEqual(result, [date(y, 5, 17) for y in range(1978, 1986)])

        # With an interval
        rule = self.createRule(interval=4)
        result = list(rule.apply(ev, enddate=date(2004, 10, 20)))
        self.assertEqual(result,
                         [date(y, 5, 17)
                          for y in [1978, 1982, 1986, 1990, 1994, 1998, 2002]])

        # With exceptions
        rule = self.createRule(exceptions=[date(1980, 5, 17)])
        result = list(rule.apply(ev, enddate=date(2004, 10, 20)))
        self.assertEqual(result,
                         [date(y, 5, 17)
                          for y in [1978, 1979] + range(1981, 2005)])

        # With exceptions and count -- the total nr. of events is less
        # that count.
        rule = self.createRule(exceptions=[date(1980, 5, 17)], count=4)
        result = list(rule.apply(ev, enddate=date(2004, 10, 20)))
        self.assertEqual(result,
                         [date(1978, 5, 17), date(1979, 5, 17),
                          date(1981, 5, 17)])


class TestWeeklyRecurrenceRule(unittest.TestCase, RecurrenceRuleTestBase):

    def createRule(self, *args, **kwargs):
        from schoolbell.calendar.recurrent import WeeklyRecurrenceRule
        return WeeklyRecurrenceRule(*args, **kwargs)

    def test(self):
        from schoolbell.calendar.interfaces import IWeeklyRecurrenceRule
        rule = self.createRule()
        verifyObject(IWeeklyRecurrenceRule, rule)

    def test_weeekday_validation(self):
        self.assertRaises(ValueError, self.createRule, weekdays=(1, 7))
        self.assertRaises(ValueError, self.createRule, weekdays=(1, "TH"))

    def test_replace_weekly(self):
        rule = self.createRule(weekdays=(1, 3))
        assert rule == rule.replace()
        assert rule != rule.replace(weekdays=(1,))

    def test_apply(self):
        from schoolbell.calendar.simple import SimpleCalendarEvent
        rule = self.createRule()
        ev = SimpleCalendarEvent(datetime(1978, 5, 17, 12, 0),
                           timedelta(minutes=10),
                           "reality check", unique_id='uid')

        # The event happened after the range -- empty result
        result = list(rule.apply(ev, enddate=date(1970, 1, 1)))
        self.assertEqual(result, [])

        # Simplest case
        result = list(rule.apply(ev, enddate=date(1978, 7, 17))) # Wednesday
        expected = [date(1978, 5, 17) + timedelta(w * 7) for w in range(9)]
        self.assertEqual(result, expected)

        # With an end date
        rule = self.createRule(until=date(1978, 7, 12))
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With an end date as datetime
        rule = self.createRule(until=datetime(1978, 7, 12))
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With a count
        rule = self.createRule(count=9)
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With an interval
        rule = self.createRule(interval=2, weekdays=(3,))
        result = list(rule.apply(ev, enddate=date(1978, 7, 12)))
        expected = [date(1978, 5, 17), date(1978, 5, 18),
                    date(1978, 5, 31), date(1978, 6, 1),
                    date(1978, 6, 14), date(1978, 6, 15),
                    date(1978, 6, 28), date(1978, 6, 29),
                    date(1978, 7, 12)]
        self.assertEqual(result, expected)

        # With exceptions
        rule = self.createRule(interval=2, weekdays=(3,),
                               exceptions=[date(1978, 6, 29)])
        result = list(rule.apply(ev, enddate=date(1978, 7, 12)))
        expected = [date(1978, 5, 17), date(1978, 5, 18),
                    date(1978, 5, 31), date(1978, 6, 1),
                    date(1978, 6, 14), date(1978, 6, 15),
                    date(1978, 6, 28), date(1978, 7, 12)]
        self.assertEqual(result, expected)

    def test_iCalRepresentation_weekly(self):
        rule = self.createRule(weekdays=(0, 3, 6))
        dtstart = datetime(2005, 01, 01, 12, 0) # saturday
        self.assertEquals(rule.iCalRepresentation(dtstart),
                          ['RRULE:FREQ=WEEKLY;BYDAY=MO,TH,SA,SU;INTERVAL=1'])
        self.assertEquals(rule.iCalRepresentation(None),
                          ['RRULE:FREQ=WEEKLY;INTERVAL=1'])


class TestMonthlyRecurrenceRule(unittest.TestCase, RecurrenceRuleTestBase):

    def createRule(self, *args, **kwargs):
        from schoolbell.calendar.recurrent import MonthlyRecurrenceRule
        return MonthlyRecurrenceRule(*args, **kwargs)

    def test(self):
        from schoolbell.calendar.interfaces import IMonthlyRecurrenceRule
        rule = self.createRule()
        verifyObject(IMonthlyRecurrenceRule, rule)

    def test_monthly_validation(self):
        self.assertRaises(ValueError, self.createRule, monthly="whenever")
        self.assertRaises(ValueError, self.createRule, monthly=date.today())
        self.assertRaises(ValueError, self.createRule, monthly=None)
        self.createRule(monthly="lastweekday")
        self.createRule(monthly="monthday")
        self.createRule(monthly="weekday")

    def test_replace_(self):
        rule = self.createRule(monthly="lastweekday")
        assert rule == rule.replace()
        assert rule != rule.replace(monthly="monthday")

    def test_apply_monthday(self):
        from schoolbell.calendar.simple import SimpleCalendarEvent
        rule = self.createRule(monthly="monthday")
        ev = SimpleCalendarEvent(datetime(1978, 5, 17, 12, 0),
                           timedelta(minutes=10),
                           "reality check", unique_id='uid')

        # The event happened after the range -- empty result
        result = list(rule.apply(ev, enddate=date(1970, 1, 1)))
        self.assertEqual(result, [])

        # Simplest case
        result = list(rule.apply(ev, enddate=date(1978, 8, 17)))
        expected = [date(1978, m, 17) for m in range(5,9)]
        self.assertEqual(result, expected)

        # Over the end of the year
        result = list(rule.apply(ev, enddate=date(1979, 2, 17)))
        expected = ([date(1978, m, 17) for m in range(5, 13)] +
                    [date(1979, m, 17) for m in range(1, 3)])
        self.assertEqual(result, expected)

        # With an end date
        rule = self.createRule(monthly="monthday", until=date(1979, 2, 17))
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With a count
        rule = self.createRule(count=10)
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With an interval
        rule = self.createRule(monthly="monthday", interval=2)
        result = list(rule.apply(ev, enddate=date(1979, 2, 17)))
        expected = [date(1978, 5, 17), date(1978, 7, 17),date(1978, 9, 17),
                    date(1978, 11, 17), date(1979, 1, 17)]
        self.assertEqual(result, expected)

        # With exceptions
        rule = self.createRule(monthly="monthday", interval=2,
                               exceptions=[date(1978, 7, 17)])
        result = list(rule.apply(ev, enddate=date(1978, 9, 17)))
        expected = [date(1978, 5, 17), date(1978, 9, 17)]
        self.assertEqual(result, expected)

    def test_apply_endofmonth(self):
        from schoolbell.calendar.simple import SimpleCalendarEvent
        rule = self.createRule(monthly="monthday")
        ev = SimpleCalendarEvent(datetime(2001, 1, 31, 0, 0),
                           timedelta(minutes=10),
                           "End of month", unique_id="uid")

        # The event happened after the range -- empty result
        result = list(rule.apply(ev, enddate=date(2001, 12, 31)))
        self.assertEqual(len(result), 7)

        rule = self.createRule(monthly="monthday", count=7)
        result = list(rule.apply(ev, enddate=date(2001, 12, 31)))
        self.assertEqual(len(result), 7)
        self.assertEqual(result[-1], date(2001, 12, 31))

        rule = self.createRule(monthly="monthday", interval=2)
        result = list(rule.apply(ev, enddate=date(2002, 1, 31)))
        self.assertEqual(result, [date(2001, 1, 31),
                                  date(2001, 3, 31),
                                  date(2001, 5, 31),
                                  date(2001, 7, 31),
                                  date(2002, 1, 31),])

    def test_apply_weekday(self):
        from schoolbell.calendar.simple import SimpleCalendarEvent
        rule = self.createRule(monthly="weekday")
        ev = SimpleCalendarEvent(datetime(1978, 5, 17, 12, 0),  # 3rd Wednesday
                           timedelta(minutes=10),
                           "reality check", unique_id='uid')

        # The event happened after the range -- empty result
        result = list(rule.apply(ev, enddate=date(1970, 1, 1)))
        self.assertEqual(result, [])

        # Simplest case
        result = list(rule.apply(ev, enddate=date(1978, 8, 17)))
        expected = [date(1978, 5, 17), date(1978, 6, 21),
                    date(1978, 7, 19), date(1978, 8, 16)]
        self.assertEqual(result, expected)

        # Over the end of the year
        result = list(rule.apply(ev, enddate=date(1979, 2, 21)))
        expected = [date(1978, 5, 17), date(1978, 6, 21),
                    date(1978, 7, 19), date(1978, 8, 16),
                    date(1978, 9, 20), date(1978, 10, 18),
                    date(1978, 11, 15), date(1978, 12, 20),
                    date(1979, 1, 17), date(1979, 2, 21)]
        self.assertEqual(result, expected)

        # With an end date
        rule = self.createRule(monthly="weekday", until=date(1979, 2, 21))
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With a count
        rule = self.createRule(monthly="weekday", count=10)
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With an interval
        rule = self.createRule(monthly="weekday", interval=2)
        result = list(rule.apply(ev, enddate=date(1979, 2, 21)))
        expected = [date(1978, 5, 17), date(1978, 7, 19),
                    date(1978, 9, 20), date(1978, 11, 15),
                    date(1979, 1, 17)]
        self.assertEqual(result, expected)

        # With exceptions
        rule = self.createRule(monthly="weekday", interval=2,
                               exceptions=[date(1978, 7, 19)])
        result = list(rule.apply(ev, enddate=date(1978, 9, 30)))
        expected = [date(1978, 5, 17), date(1978, 9, 20)]
        self.assertEqual(result, expected)

    def test_apply_lastweekday(self):
        from schoolbell.calendar.simple import SimpleCalendarEvent
        rule = self.createRule(monthly="lastweekday")
        ev = SimpleCalendarEvent(datetime(1978, 5, 17, 12, 0),  # 3rd last Wednesday
                           timedelta(minutes=10),
                           "reality check", unique_id='uid')

        # The event happened after the range -- empty result
        result = list(rule.apply(ev, enddate=date(1970, 1, 1)))
        self.assertEqual(result, [])

        # Simplest case
        result = list(rule.apply(ev, enddate=date(1978, 8, 17)))
        expected = [date(1978, 5, 17), date(1978, 6, 14),
                    date(1978, 7, 12), date(1978, 8, 16)]
        self.assertEqual(result, expected)

        # Over the end of the year
        result = list(rule.apply(ev, enddate=date(1979, 2, 21)))
        expected = [date(1978, 5, 17), date(1978, 6, 14),
                    date(1978, 7, 12), date(1978, 8, 16),
                    date(1978, 9, 13), date(1978, 10, 11),
                    date(1978, 11, 15), date(1978, 12, 13),
                    date(1979, 1, 17), date(1979, 2, 14)]
        self.assertEqual(result, expected)

        # With an end date
        rule = self.createRule(monthly="lastweekday", until=date(1979, 2, 21))
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With a count
        rule = self.createRule(monthly="lastweekday", count=10)
        result = list(rule.apply(ev))
        self.assertEqual(result, expected)

        # With an interval
        rule = self.createRule(monthly="lastweekday", interval=2)
        result = list(rule.apply(ev, enddate=date(1979, 2, 21)))
        expected = [date(1978, 5, 17), date(1978, 7, 12),
                    date(1978, 9, 13), date(1978, 11, 15),
                    date(1979, 1, 17)]
        self.assertEqual(result, expected)

        # With exceptions
        rule = self.createRule(monthly="lastweekday", interval=2,
                               exceptions=[date(1978, 7, 12)])
        result = list(rule.apply(ev, enddate=date(1978, 9, 30)))
        expected = [date(1978, 5, 17), date(1978, 9, 13)]
        self.assertEqual(result, expected)

    def test_iCalRepresentation(self):
        # This method deliberately overrides the test in the base class.

        # monthday
        rule = self.createRule(monthly="monthday")
        self.assertEquals(rule.iCalRepresentation(date(2004, 10, 26)),
                          ['RRULE:FREQ=MONTHLY;BYMONTHDAY=26;INTERVAL=1'])

        # weekday
        rule = self.createRule(monthly="weekday")
        self.assertEquals(rule.iCalRepresentation(date(2004, 10, 26)),
                          ['RRULE:FREQ=MONTHLY;BYDAY=4TU;INTERVAL=1'])

        # lastweekday
        rule = self.createRule(monthly="lastweekday")
        self.assertEquals(rule.iCalRepresentation(date(2004, 10, 26)),
                          ['RRULE:FREQ=MONTHLY;BYDAY=-1TU;INTERVAL=1'])

        # some standard stuff
        rule = self.createRule(interval=3, count=7,
                               exceptions=[date(2004, 10, 2*d)
                                           for d in range(3, 6)])
        self.assertEquals(rule.iCalRepresentation(date(2004, 10, 26)),
                      ['RRULE:FREQ=MONTHLY;COUNT=7;BYMONTHDAY=26;INTERVAL=3',
                       'EXDATE;VALUE=DATE:20041006,20041008,20041010'])


class TestWeekSpan(unittest.TestCase):

    def test_weekspan(self):
        from schoolbell.calendar.recurrent import weekspan

        # The days are in the same week
        self.assertEqual(weekspan(date(2004, 10, 11), date(2004, 10, 17)), 0)
        #                              Monday, w42         Sunday, w42

        # The days are in the adjacent weeks
        self.assertEqual(weekspan(date(2004, 10, 17), date(2004, 10, 18)), 1)
        #                              Sunday, w42         Monday, w43

        # The days span the end of year
        self.assertEqual(weekspan(date(2004, 12, 30), date(2005, 01, 07)), 1)
        #                              Thursday, w53       Friday, w1

        # The days span the end of year, two weeks
        self.assertEqual(weekspan(date(2004, 12, 30), date(2005, 01, 14)), 2)
        #                              Thursday, w53       Friday, w2


class TestMonthIndex(unittest.TestCase):

    def test_monthindex(self):
        from schoolbell.calendar.recurrent import monthindex
        # First Friday of October 2004
        self.assertEqual(monthindex(2004, 10, 1, 4), date(2004, 10, 1))
        self.assertEqual(monthindex(2004, 10, 1, 3), date(2004, 10, 7))
        self.assertEqual(monthindex(2004, 10, 1, 3), date(2004, 10, 7))

        # Users must check whether the month is correct themselves.
        self.assertEqual(monthindex(2004, 10, 5, 3), date(2004, 11, 4))

        self.assertEqual(monthindex(2004, 10, 4, 3), date(2004, 10, 28))
        self.assertEqual(monthindex(2004, 10, -1, 3), date(2004, 10, 28))

        self.assertEqual(monthindex(2004, 11, -1, 1), date(2004, 11, 30))
        self.assertEqual(monthindex(2004, 11, -1, 2), date(2004, 11, 24))

        self.assertEqual(monthindex(2004, 12, -1, 3), date(2004, 12, 30))
        self.assertEqual(monthindex(2004, 12, -1, 4), date(2004, 12, 31))
        self.assertEqual(monthindex(2004, 12, -1, 3), date(2004, 12, 30))
        self.assertEqual(monthindex(2004, 12, -2, 3), date(2004, 12, 23))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDailyRecurrenceRule))
    suite.addTest(unittest.makeSuite(TestYearlyRecurrenceRule))
    suite.addTest(unittest.makeSuite(TestWeeklyRecurrenceRule))
    suite.addTest(unittest.makeSuite(TestMonthlyRecurrenceRule))
    suite.addTest(unittest.makeSuite(TestWeekSpan))
    suite.addTest(unittest.makeSuite(TestMonthIndex))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

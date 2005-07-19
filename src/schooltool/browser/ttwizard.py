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
Timetable setup wizard for SchoolTool.

This module implements a the workflow described by Tom Hoffman on Jun 9 2005
on the schooltool mailing list, in ttschema-wireframes.pdf[1].

    [1] http://lists.schooltool.org/pipermail/schooltool/2005-June/001347.html

The workflow is as follows:

    1. "New timetable schema"

       (The user enters a name.)

    2. "Does your school's timetable cycle use days of the week, or a rotating
        cycle?"

        Skip to step 3 if days of the week was chosen.

    3. "Enter names of days in cycle:"

        (The user enters a list of day names in a single textarea.)

    4. "Do classes begin and end at the same time each day in your school's
        timetable?"

        Continue with step 5 if "yes".
        Skip to step 6 if "no", and "cycle" was chosen in step 2.
        Skip to step 7 if "no", and "days of the week" was chosen in step 2.

    5. "Enter start and end times for each slot"

        (The user enters a list of start and end times in a single textarea.)

        Jump to step 9.

    6. "Do the start and end times vary based on the day of the week, or the
        day in the cycle?"

        Continue with step 7 if "days of week".
        Continue with step 8 if "cycle".

    7. "Enter the start and end times of each slot on each day:"

        (The user sees 5 columns of text lines, with five buttons that let him
        add an extra slot for each column.)

        Jump to step 9.

    8. "Enter the start and end times of each slot on each day:"

        (The user sees N columns of text lines, with five buttons that let him
        add an extra slot for each column.)

    9. "Do periods have names or are they simply designated by time?"

        Skip to step 14 if periods are simply designated by time.

    10. "Enter names of the periods:"

        (The user enters a list of periods in a single textarea.)

    11. "Is the sequence of periods each day the same or different?"

        Skip to step 13 if it is different

    12. "Put the periods in order for each day:"

        (The user sees a grid of drop-downs.)

        Jump to step 14.

    13. "Put the periods in order:"

        (The user sees a list of drop-downs.)

    14. The timetable schema is created.


The shortest path through this workflow contains 6 steps, the longest contains
11 steps.

Step 14 needs the following data:

    - title (determined in step 1)
    - timetable model factory (determined in step 2)
    - a list of day IDs (determined in step 3)
    - a list of periods for each day ID
    - a list of day templates (weekday -> period_id -> start time & duration)

$Id$
"""

from zope.interface import Interface
from zope.schema import TextLine
from zope.app import zapi
from zope.app.form.utility import setUpWidgets
from zope.app.form.utility import getWidgetsData
from zope.app.form.interfaces import IInputWidget
from zope.app.publisher.browser import BrowserView
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.container.interfaces import INameChooser
from zope.app.session.interfaces import ISession

from schooltool import SchoolToolMessageID as _
from schooltool.interfaces import ITimetableSchemaContainer
from schooltool.timetable import TimetableSchema
from schooltool.timetable import TimetableSchemaDay
from schooltool.timetable import SchooldayTemplate
from schooltool.timetable import WeeklyTimetableModel


class Step(BrowserView):
    """A step, one of many."""

    __used_for__ = ITimetableSchemaContainer

    def getSessionData(self):
        return ISession(self.request)['schooltool.ttwizard']


class FirstStep(Step):
    """First step: enter the title for the new schema."""

    template = ViewPageTemplateFile("templates/ttwizard.pt")

    class schema(Interface):
        title = TextLine(title=_("Title"), required=True)

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        setUpWidgets(self, self.schema, IInputWidget,
                     initial={'title': 'default'})

    def update(self):
        data = getWidgetsData(self, self.schema)
        session = self.getSessionData()
        session['title'] = data['title']

    def __call__(self):
        return self.template()


class FinalStep(Step):
    """Final step: create the schema."""

    def createSchema(self):
        """Create the timetable schema."""
        session = self.getSessionData()
        title = session['title']
        day_ids = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        periods = ['A', 'B']
        day_templates = {None: SchooldayTemplate()}
        model = WeeklyTimetableModel(day_ids, day_templates)
        ttschema = TimetableSchema(day_ids, title=title, model=model)
        for day_id in day_ids:
            ttschema[day_id] = TimetableSchemaDay(periods)
        return ttschema

    def add(self, ttschema):
        """Add the timetable schema to self.context."""
        nameChooser = INameChooser(self.context)
        key = nameChooser.chooseName('', ttschema)
        self.context[key] = ttschema

    def __call__(self):
        ttschema = self.createSchema()
        self.add(ttschema)
        self.request.response.redirect(
            zapi.absoluteURL(self.context, self.request))


class TimetableSchemaWizard(BrowserView):
    """View for defining a new timetable schema."""

    __used_for__ = ITimetableSchemaContainer

    def __call__(self):
        first_step = FirstStep(self.context, self.request)
        final_step = FinalStep(self.context, self.request)
        if 'CREATE' in self.request:
            first_step.update()
            return final_step()
        else:
            return first_step()


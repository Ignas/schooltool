#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
Web-application views for managing SchoolTool data in CSV format.

$Id$
"""

import csv

from schooltool.browser import View, Template, ToplevelBreadcrumbsMixin
from schooltool.browser.auth import ManagerAccess
from schooltool.csvimport import CSVImporterBase, DataError
from schooltool.common import parse_date
from schooltool.component import FacetManager, getFacetFactory
from schooltool.interfaces import IApplication
from schooltool.membership import Membership
from schooltool.teaching import Teaching
from schooltool.timetable import Timetable, TimetableActivity
from schooltool.translation import ugettext as _
from schooltool.browser.widgets import SelectionWidget, TextWidget

__metaclass__ = type


class CharsetMixin:

    charsets = [('UTF-8', _('Unicode (UTF-8)')),
                ('ISO-8859-1', _('Western (ISO-8859-1)')),
                ('ISO-8859-15', _('Western (ISO-8859-15)')),
                ('Windows-1252', _('Western (Windows-1252)')),
                ('', _('Other (please specify)'))]

    def __init__(self, context):
        self.charset_widget = SelectionWidget('charset', _('Charset'),
                                              self.charsets,
                                              validator=self.validate_charset)
        self.other_charset_widget = TextWidget('other_charset',
                                               _('Specify other charset'),
                                               validator=self.validate_charset)

    def getCharset(self, request):
        """Return the charset (as a string) that was specified in request.

        Uses the widgets charset_widget and other_charset_widget.
        Raises ValueError if the charset is missing or invalid.
        """
        self.charset_widget.update(request)
        if self.charset_widget.error:
            raise ValueError("No charset specified")

        if not self.charset_widget.value:
            self.other_charset_widget.update(request)
            if self.other_charset_widget.value == "":
                # Force a "field is required" error if value is ""
                self.other_charset_widget.setRawValue(None)
            self.other_charset_widget.require()
            if self.other_charset_widget.error:
                raise ValueError("No charset specified")
        return (self.charset_widget.value or self.other_charset_widget.value)

    def validate_charset(self, charset):
        if not charset:
            return
        try:
            unicode(' ', charset)
        except LookupError:
            raise ValueError(_('Unknown charset'))


class CSVImportView(View, CharsetMixin, ToplevelBreadcrumbsMixin):
    """A view for importing SchoolTool objects in CSV format."""

    __used_for__ = IApplication

    authorization = ManagerAccess

    template = Template('www/csvimport.pt')

    error = u""
    success = False

    def __init__(self, context):
        View.__init__(self, context)
        CharsetMixin.__init__(self, context)

    def do_POST(self, request):
        try:
            charset = self.getCharset(request)
        except ValueError:
            return self.do_GET(request)

        groups_csv = request.args['groups.csv'][0]
        resources_csv = request.args['resources.csv'][0]
        teachers_csv = request.args['teachers.csv'][0]
        pupils_csv = request.args['pupils.csv'][0]

        if not (groups_csv or resources_csv or pupils_csv or teachers_csv):
            self.error = _('No data provided.')
            return self.do_GET(request)

        try:
            for csv in [groups_csv, resources_csv, teachers_csv, pupils_csv]:
                unicode(csv, charset)
        except UnicodeError:
            self.error = _('Could not convert data to Unicode'
                           ' (incorrect charset?).')
            return self.do_GET(request)

        importer = CSVImporterZODB(self.context, charset)

        try:
            if groups_csv:
                importer.importGroupsCsv(groups_csv.splitlines())
            if resources_csv:
                importer.importResourcesCsv(resources_csv.splitlines())
            if teachers_csv:
                importer.importPersonsCsv(teachers_csv.splitlines(),
                                          'teachers', teaching=True)
            if pupils_csv:
                importer.importPersonsCsv(pupils_csv.splitlines(),
                                          'pupils', teaching=False)
        except DataError, e:
            self.error = _("Import failed: %s") % e
            return self.do_GET(request)

        self.success = True
        request.appLog(_("CSV data import started"))
        for log_entry in importer.logs:
            request.appLog(log_entry)
        request.appLog(_("CSV data import finished successfully"))

        return self.do_GET(request)


class CSVImporterZODB(CSVImporterBase):
    """A CSV importer that works directly with the database."""

    def __init__(self, app, charset):
        self.groups = app['groups']
        self.persons = app['persons']
        self.resources = app['resources']
        self.logs = []
        self.charset = charset

    def recode(self, value):
        return unicode(value, self.charset)

    def importGroup(self, name, title, parents, facets):
        try:
            group = self.groups.new(__name__=name, title=title)
        except KeyError, e:
            raise DataError(_("Group already exists: %r") % name)

        for path in parents.split():
            try:
                parent = self.groups[path]
            except KeyError:
                raise DataError(_("No such group: %s") % path)
            try:
                Membership(group=parent, member=group)
            except ValueError, e:
                raise DataError(_("Cannot add %s to group %s") %
                                (group, parent))

        for facet_name in facets.split():
            try:
                factory = getFacetFactory(facet_name)
            except KeyError:
                raise DataError(_("Unknown facet type: %s") % facet_name)
            facet = factory()
            FacetManager(group).setFacet(facet, name=factory.facet_name)
        self.logs.append(_('Imported group: %s') % name)
        return group.__name__

    def importPerson(self, title, parent, groups, teaching=False):
        try:
            person = self.persons.new(title=title)
        except KeyError, e:
            raise DataError(_("Group already exists: %r") % name)

        if parent:
            try:
                Membership(group=self.groups[parent], member=person)
            except KeyError:
                raise DataError(_("Invalid group: %s") % parent)

        if not teaching:
            for group in groups.split():
                try:
                    Membership(group=self.groups[group], member=person)
                except KeyError, e:
                    raise DataError(_("No such group: %r") % group)
                except ValueError:
                    raise DataError(_("Cannot add %r to %r") % (person, group))
            self.logs.append(_('Imported person: %s') % title)
        else:
            for group in groups.split():
                try:
                    Teaching(teacher=person, taught=self.groups[group])
                except KeyError, e:
                    raise DataError(_("No such group: %r") % group)
                except ValueError:
                    raise DataError(_("Cannot add %r as a teacher for %r")
                                    % (person, group))
            self.logs.append(_('Imported person (teacher): %s') % title)

        return person.__name__

    def importResource(self, title, groups):
        resource = self.resources.new(title=title)
        for group in groups.split():
            try:
                other = self.groups[group]
            except KeyError:
                raise DataError(_("Invalid group: %s") % group)
            try:
                Membership(group=other, member=resource)
            except ValueError:
                raise DataError(_("Cannot add %r to %r") % (person, group))
        self.logs.append(_('Imported resource: %s') % title)
        return resource.__name__

    def importPersonInfo(self, name, title, dob, comment):
        person = self.persons[name]
        infofacet = FacetManager(person).facetByName('person_info')

        try:
            infofacet.first_name, infofacet.last_name = title.split(None, 1)
        except ValueError:
            infofacet.first_name = ''
            infofacet.last_name = title

        if dob:
            infofacet.date_of_birth = parse_date(dob)
        else:
            infofacet.date_of_birth = None
        infofacet.comment = comment
        self.logs.append(_('Imported person info for %s (%s %s, %s)')
                         % (name, infofacet.first_name, infofacet.last_name,
                            infofacet.date_of_birth))


class TimetableCSVImportView(View, CharsetMixin, ToplevelBreadcrumbsMixin):
    """View to upload the school timetable as CSV."""

    __used_for__ = IApplication

    authorization = ManagerAccess

    template = Template("www/timetable-csvupload.pt")

    error = None
    success = None

    def __init__(self, context):
        View.__init__(self, context)
        CharsetMixin.__init__(self, context)

    def do_POST(self, request):
        try:
            charset = self.getCharset(request)
        except ValueError:
            return self.do_GET(request)

        timetable_csv = request.args['timetable.csv'][0]
        roster_txt = request.args['roster.txt'][0]

        if not (timetable_csv or roster_txt):
            self.error = _('No data provided.')
            return self.do_GET(request)

        try:
            # TODO timetable_csv = unicode(timetable_csv, charset) ?
            unicode(timetable_csv, charset)
            roster_txt = unicode(roster_txt, charset)
        except UnicodeError:
            self.error = _('Could not convert data to Unicode'
                           ' (incorrect charset?).')
            return self.do_GET(request)

        importer = TimetableCSVImporter()
        try:
            if timetable_csv:
                self.importTimetable(timetable_csv)
            if roster_txt:
                self.importRoster(roster_txt)
        except DataError, e:
            self.error = _("Import failed: %s") % e
            return self.do_GET(request)

        # TODO: log import
        return self.do_GET(request)


class TimetableCSVImporter:
    """A timetable CSV parser and importer."""

    def __init__(self, app):
        self.app = app
        self.groups = self.app['groups']
        self.persons = self.app['persons']

    def importTimetable(self, timetable_csv):
        """Import timetables from CSV data."""
        lines = timetable_csv.splitlines()
        reader = csv.reader(lines)
        # TODO: error checking
        self.ttschema_name, self.period_id = reader.next()
        self.day_ids = reader.next()
        try:
            periods = reader.next()[1:]
        except StopIteration:
            return

        for period in periods:
            pass # TODO: check existence of periods

        for row in reader:
            location, row = row[0], row[1:]
            # TODO: create location
            subjects = [record.split(" ", 1)[0] for record in row]
            teachers = [record.split(" ", 1)[1] for record in row]

            for period, subject, teacher in zip(periods, subjects, teachers):
                pass # TODO: register

    def _findByTitle(self, container, title):
        # XXX Could be sped up by constructing a dict
        for obj in container.itervalues():
            if obj.title == title:
                return obj
        else:
            raise KeyError("Group %r not found" % subject)

    def _clearTimetables(self):
        """Delete timetables of the period and schema we are dealing with."""
        for group in self.groups.itervalues():
            if (self.period_id, self.ttschema_name) in group.timetables.keys():
                del group.timetables[self.period_id, self.ttschema_name]

    def _scheduleClass(self, period, subject, teacher):
        """Schedule a class of subject during a given period."""
        group = self._findByTitle(self.groups, subject)
        teacher = self._findByTitle(self.persons, teacher)

        # Create the timetable if it does not exist yet.
        if (self.period_id, self.ttschema_name) not in group.timetables.keys():
            tt = self.app.timetableSchemaService[self.ttschema_name]
            group.timetables[self.period_id, self.ttschema_name] = tt
        else:
            tt = group.timetables[self.period_id, self.ttschema_name]

        # Add a new activity to the timetable
        act = TimetableActivity(title=subject, owner=teacher)
        # TODO: resources
        for day_id in self.day_ids:
            tt[day_id].add(period, act)

    def importRoster(self, roster_txt):
        """Import timetables from provided unicode data."""
        pass # TODO

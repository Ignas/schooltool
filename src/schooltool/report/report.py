#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
Base classes for report reference and request adapters

"""

import urllib

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility, queryUtility, getGlobalSiteManager
from zope.interface import implements
from zope.publisher.browser import BrowserView
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.course.interfaces import ISectionContainer
from schooltool.group.interfaces import IGroupContainer
from schooltool.report.interfaces import IReportLinkViewletManager
from schooltool.report.interfaces import IRegisteredReportsUtility
from schooltool.report.interfaces import IReportLinksURL
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin import flourish
from schooltool.skin.skin import OrderedViewletManager
from schooltool.term.interfaces import IDateManager


class ReportLinkViewletManager(OrderedViewletManager):
    implements(IReportLinkViewletManager)


class IFlourishReportLinkViewletManager(flourish.interfaces.IViewletManager,
                                        IReportLinkViewletManager):
    pass


class FlourishReportLinkViewletManager(flourish.viewlet.ViewletManager):
    template = ViewPageTemplateFile('templates/f_report_link_manager.pt')

    @property
    def table(self):
        result = {}
        for viewlet in self.viewlets:
            group = result.setdefault(viewlet.file_type, {
                'file_type': viewlet.file_type.upper(),
                'rows': [],
                })
            group['rows'].append({
                'title': viewlet.title,
                'url': viewlet.link,
                'link_id': viewlet.link.replace('.', '_'),
                'form_id': viewlet.link.replace('.', '_') + '_form',
                'description': viewlet.description,
                })
        return [group for key, group in sorted(result.items())]


class ReportLinkViewlet(object):
    template=ViewPageTemplateFile('templates/report_link.pt')
    group=u''
    title=u''
    link=u'' # an optional relative link - subclasses can override report_link property in some cases

    @property
    def report_link(self):
        return '%s/%s' % (absoluteURL(self.context, self.request), self.link)

    def render(self, *args, **kw):
        return self.template()


class RegisteredReportsUtility(object):
    implements(IRegisteredReportsUtility)

    def __init__(self):
        self.reports_by_group = {}

    def registerReport(self, group, title, description, file_type, name, layer):
        # make a non-translatable group key
        group_key = unicode(group)

        if group_key not in self.reports_by_group:
            self.reports_by_group[group_key] = []
        self.reports_by_group[group_key].append({
            'group': group, # remember the translatable group title
            'title': title,
            'description': description,
            'file_type': file_type,
            'name': name,
            'layer': layer,
            })


def getReportRegistrationUtility():
    """Helper - returns report registration utility and registers a new one
    if missing."""
    utility = queryUtility(IRegisteredReportsUtility)
    if not utility:
        utility = RegisteredReportsUtility()
        getGlobalSiteManager().registerUtility(utility,
            IRegisteredReportsUtility)
    return utility


class ReportLinksURL(BrowserView):
    implements(IReportLinksURL)

    def actualContext(self):
        return self.context

    def __unicode__(self):
        return urllib.unquote(self.__str__()).decode('utf-8')

    def __str__(self):
        return absoluteURL(self.actualContext(), self.request)

    def __call__(self):
        return self.__str__()


class StudentReportLinksURL(ReportLinksURL):

    def actualContext(self):
        return ISchoolToolApplication(None)['persons']


class GroupReportLinksURL(ReportLinksURL):

    def actualContext(self):
        current_term = getUtility(IDateManager).current_term
        if current_term is None:
            return ISchoolToolApplication(None)
        return IGroupContainer(ISchoolYear(current_term))


class SchoolYearReportLinksURL(ReportLinksURL):

    def actualContext(self):
        current_term = getUtility(IDateManager).current_term
        if current_term is None:
            return ISchoolToolApplication(None)
        return ISchoolYear(current_term)


class TermReportLinksURL(ReportLinksURL):

    def actualContext(self):
        current_term = getUtility(IDateManager).current_term
        if current_term is None:
            return ISchoolToolApplication(None)
        return current_term


class SectionReportLinksURL(ReportLinksURL):

    def actualContext(self):
        current_term = getUtility(IDateManager).current_term
        if current_term is None:
            return ISchoolToolApplication(None)
        return ISectionContainer(current_term)


class FlourishSchoolReportLinksURL(ReportLinksURL):

    def __str__(self):
        app = ISchoolToolApplication(None)
        return absoluteURL(app, self.request) + '/manage'


class FlourishGroupReportLinksURL(GroupReportLinksURL):

    def __str__(self):
        app = ISchoolToolApplication(None)
        return absoluteURL(app, self.request) + '/groups'


class FlourishSchoolYearReportLinksURL(SchoolYearReportLinksURL):

    def __str__(self):
        app = ISchoolToolApplication(None)
        return absoluteURL(app, self.request) + '/schoolyears'


class FlourishTermReportLinksURL(TermReportLinksURL):

    def __str__(self):
        app = ISchoolToolApplication(None)
        return absoluteURL(app, self.request) + '/terms'


class FlourishSectionReportLinksURL(SectionReportLinksURL):

    def __str__(self):
        app = ISchoolToolApplication(None)
        return absoluteURL(app, self.request) + '/sections'

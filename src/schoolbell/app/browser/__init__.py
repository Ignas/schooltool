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
Browser views for the SchoolBell application.

$Id$
"""

import itertools

from zope.interface import implements
from zope.component import adapts
from zope.app.publisher.browser import BrowserView
from zope.app.location.interfaces import ILocation
from zope.app.traversing.interfaces import IPathAdapter
from zope.app.traversing.interfaces import ITraversable

from schoolbell.app.interfaces import ISchoolBellApplication


def getSchoolBellApplication(obj):
    """Return the nearest ISchoolBellApplication from ancestors of obj"""
    cur = obj
    while True:
        if ISchoolBellApplication.providedBy(cur):
            return cur

        if ILocation.providedBy(cur):
            cur = cur.__parent__
        else:
            cur = None

        if cur is None:
            raise ValueError("can't get a SchoolBellApplication from %r" % obj)


class NavigationView(BrowserView):
    """XXX I want a docstring"""

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        self.app = getSchoolBellApplication(context)


class SortBy(object):
    """TALES path adapter for sorting lists.

    In a page template you can use it as follows:

        tal:repeat="something some_iterable/sortby:attribute_name"

    In Python code you can write

        >>> l = [{'name': 'banana'}, {'name': 'apple'}]
        >>> SortBy(l).traverse('name')
        [{'name': 'apple'}, {'name': 'banana'}]

    You can sort arbitrary iterables, not just lists.  The sort key
    can refer to a dictionary key, or an object attribute.
    """

    adapts(None)
    implements(IPathAdapter, ITraversable)

    def __init__(self, context):
        self.context = context

    def traverse(self, name, furtherPath=()):
        """Return self.context sorted by a given key."""
        # We need to get the first item without losing it forever
        iterable = iter(self.context)
        try:
            first = iterable.next()
        except StopIteration:
            return [] # We got an empty list
        iterable = itertools.chain([first], iterable)
        if hasattr(first, name):
            items = [(getattr(item, name), item) for item in iterable]
        else:
            items = [(item[name], item) for item in iterable]
        items.sort()
        return [row[-1] for row in items]


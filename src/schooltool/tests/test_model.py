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
Unit tests for schooltool.model

$Id$
"""

import unittest
from persistence import Persistent
from zope.interface import implements
from zope.interface.verify import verifyObject
from schooltool.interfaces import IGroupMember, IFacet, IFaceted
from schooltool.interfaces import IEventConfigurable

__metaclass__ = type

class P(Persistent):
    pass

class MemberStub:
    implements(IGroupMember, IFaceted)

    def __init__(self):
        self.__facets__ = {}
        self.added = None
        self.removed = None

    def notifyAdded(self, group, name):
        self.added = group

    def notifyRemoved(self, group):
        self.removed = group

class GroupStub(Persistent):
    deleted = None

    def __delitem__(self, key):
        self.deleted = key

    def add(self, thing):
        self.added = thing
        thing.notifyAdded(self, 'foo')

class FacetStub:
    implements(IFacet)

    def __init__(self, context=None, active=False):
        self.context = context
        self.active = active


class TestPerson(unittest.TestCase):

    def test(self):
        from schooltool.interfaces import IPerson, IEventTarget, IRelatable
        from schooltool.model import Person
        person = Person('John Smith')
        verifyObject(IPerson, person)
        verifyObject(IEventTarget, person)
        verifyObject(IEventConfigurable, person)
        verifyObject(IRelatable, person)

    def testQueryLinks(self):
        from schooltool.model import Person
        from schooltool.interfaces import IQueryLinks, URIGroup, URIMember
        from schooltool.interfaces import ISpecificURI
        person = Person("Test Monkey")
        verifyObject(IQueryLinks, person)
        self.assertEqual(person.listLinks(), [])
        group = GroupStub()
        key = group.add(person)

        for role in (URIGroup, ISpecificURI):
            links = person.listLinks(role)
            self.assertEqual(len(links), 1, str(role))
            self.assertEqual(links[0].role, URIGroup)
            self.assertEqual(links[0].title, "Membership")
            self.assert_(links[0].traverse() is group)

        class URIFoo(URIMember):
            "http://example.com/ns/foo"

        for role in (URIMember, URIFoo):
            links = person.listLinks(role)
            self.assertEqual(links, [], str(role))

        class URISomeRole(ISpecificURI): "foo:bar"

        class LinkStub:
            def __init__(self, role):
                self.role = role

        person.__links__ = [LinkStub(URISomeRole)]

        links = person.listLinks()
        self.assertEqual(len(links), 2)

        links = person.listLinks(URIGroup)
        self.assertEqual(len(links), 1)

        links = person.listLinks(URISomeRole)
        self.assertEqual(len(links), 1)

        links = person.listLinks(URIFoo)
        self.assertEqual(links, [])


class TestGroup(unittest.TestCase):

    def test(self):
        from schooltool.interfaces import IGroup, IEventTarget, IRelatable
        from schooltool.model import Group
        group = Group("root")
        verifyObject(IGroup, group)
        verifyObject(IGroupMember, group)
        verifyObject(IFaceted, group)
        verifyObject(IEventTarget, group)
        verifyObject(IEventConfigurable, group)
        verifyObject(IRelatable, group)

    def test_add_group(self):
        from schooltool.model import Group
        group = Group("root")
        member = Group("people")
        key = group.add(member)
        self.assertEqual(member, group[key])
        self.assertEqual(list(member.groups()), [group])

    def test_facet_management(self):
        from schooltool.model import Group
        from schooltool.component import getFacet
        group = Group("root", FacetStub)
        member = MemberStub()
        key = group.add(member)
        facet = getFacet(member, group)
        self.assertEquals(facet.context, member)
        self.assert_(facet.active)

        del group[key]
        self.assert_(getFacet(member, group) is facet)
        self.assert_(not facet.active)

        key = group.add(member)
        self.assert_(getFacet(member, group) is facet)
        self.assert_(facet.active)

    def testQueryLinks(self):
        from schooltool.model import Group
        from schooltool.interfaces import IQueryLinks, URIGroup, URIMember
        from schooltool.interfaces import ISpecificURI
        group = Group("group")
        verifyObject(IQueryLinks, group)
        self.assertEqual(group.listLinks(), [])
        member = MemberStub()
        key = group.add(member)

        for role in (URIMember, ISpecificURI):
            links = group.listLinks(role)
            self.assertEqual(len(links), 1, str(role))
            self.assertEqual(links[0].role, URIMember)
            self.assertEqual(links[0].title, "Membership")
            self.assert_(links[0].traverse() is member)

        class URIFoo(URIMember):
            "http://example.com/ns/foo"

        for role in (URIGroup, URIFoo):
            links = group.listLinks(role)
            self.assertEqual(links, [], str(role))

        root = Group("root")
        root.add(group)

        class URISomeRole(ISpecificURI): "foo:bar"

        class LinkStub:
            def __init__(self, role):
                self.role = role

        group.__links__ = [LinkStub(URISomeRole)]

        links = group.listLinks()
        self.assertEqual(len(links), 3)

        links = group.listLinks(URIMember)
        self.assertEqual(len(links), 1)

        links = group.listLinks(URISomeRole)
        self.assertEqual(len(links), 1)

        links = group.listLinks(URIFoo)
        self.assertEqual(links, [])

        links = group.listLinks(URIGroup)
        self.assertEqual([link.traverse() for link in links], [root])
        self.assertEqual([link.role for link in links], [URIGroup])
        self.assertEqual([link.title for link in links], ["Membership"])


class TestRootGroup(unittest.TestCase):

    def test_interfaces(self):
        from schooltool.interfaces import IRootGroup
        from schooltool.model import RootGroup
        group = RootGroup("root")
        verifyObject(IRootGroup, group)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPerson))
    suite.addTest(unittest.makeSuite(TestGroup))
    suite.addTest(unittest.makeSuite(TestRootGroup))
    return suite

if __name__ == '__main__':
    unittest.main()

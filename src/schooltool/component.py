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
The schooltool component.

$Id$
"""
import re
from sets import Set
from zope.interface import moduleProvides
from zope.interface.interfaces import IInterface
from schooltool.interfaces import IContainmentAPI, IFacetAPI, IURIAPI
from schooltool.interfaces import ILocation, IContainmentRoot, IFaceted
from schooltool.interfaces import IServiceAPI, IServiceManager
from schooltool.interfaces import ComponentLookupError, ISpecificURI
from schooltool.interfaces import URIGroup, URIMember, URIMembership

moduleProvides(IContainmentAPI, IFacetAPI, IServiceAPI, IURIAPI)

adapterRegistry = {}

provideAdapter = adapterRegistry.__setitem__

def getAdapter(object, interface):
    """Stub adapter lookup.

    Only matches exact resulting interfaces and does not look at the
    context's interfaces at all.  Will be replaced with PyProtocols
    when we need more features.
    """

    if interface.isImplementedBy(object):
        return object
    try:
        factory = adapterRegistry[interface]
    except KeyError:
        raise ComponentLookupError("adapter from %s to %s"
                                   % (object, interface))
    return factory(object)


#
# IContainmentAPI
#

def getPath(obj):
    """Returns the path of an object implementing ILocation"""

    if IContainmentRoot.isImplementedBy(obj):
        return '/'
    cur = obj
    segments = []
    while True:
        if IContainmentRoot.isImplementedBy(cur):
            segments.append('')
            segments.reverse()
            return '/'.join(segments)
        elif ILocation.isImplementedBy(cur):
            segments.append(cur.__name__)
            cur = cur.__parent__
        else:
            raise TypeError("Cannot determine path for %s" % obj)


#
# IFacetAPI
#

def setFacet(ob, key, facet):
    """Set a facet marked with a key on a faceted object."""
    if not IFaceted.isImplementedBy(ob):
        raise TypeError("%r does not implement IFaceted" % ob)
    ob.__facets__[key] = facet

def getFacet(ob, key):
    """Get a facet of an object"""
    if not IFaceted.isImplementedBy(ob):
        raise TypeError("%r does not implement IFaceted" % ob)
    return ob.__facets__[key]

def queryFacet(ob, key, default=None):
    """Get a facet of an object, return the default value if there is
    none.
    """
    try:
        return getFacet(ob, key)
    except KeyError:
        return default

def getFacetItems(ob):
    """Returns a sequence of (key, facet) for all facets of an object."""
    if not IFaceted.isImplementedBy(ob):
        raise TypeError("%r does not implement IFaceted" % ob)
    return ob.__facets__.items()


#
# IServiceAPI
#

def getEventService(context):
    """See IServiceAPI"""

    # The following options for finding the event service are available:
    #   1. Use a thread-global variable
    #      - downside: only one event service per process
    #   2. Use context._p_jar.root()[some_hardcoded_name]
    #      - downside: only one event service per database
    #      - downside: context might not be in the database yet
    #   3. Traverse context until you get at the root and look for services
    #      there
    #      - downside: context might not be attached to the hierarchy yet
    # I dislike globals immensely, so I won't use option 1 without a good
    # reason.  Option 2 smells of too much magic.  I will consider it if
    # option 3 proves to be non-viable.

    place = context
    while not IServiceManager.isImplementedBy(place):
        if not ILocation.isImplementedBy(place):
            raise ComponentLookupError(
                    "Could not find the service manager for ", context)
        place = place.__parent__
    return place.eventService


#
# URI API
#

def inspectSpecificURI(uri):
    """Returns a tuple of a URI and the documentation of the ISpecificURI.

    Raises a TypeError if the argument is not ISpecificURI.
    Raises a ValueError if the URI's docstring does not conform.
    """
    if not IInterface.isImplementedBy(uri):
        raise TypeError("URI must be an interface (got %r)" % (uri,))

    if not uri.extends(ISpecificURI, True):
        raise TypeError("URI must strictly extend ISpecificURI (got %r)" %
                        (uri,))

    segments = uri.__doc__.split("\n", 1)
    uri = segments[0].strip()
    if not isURI(uri):
        raise ValueError("This does not look like a URI: %r" % uri)

    if len(segments) > 1:
        doc = segments[1].lstrip()
    else:
        doc = ""

    return uri, doc


def isURI(uri):
    """Checks if the argument looks like a URI.

    Refer to http://www.ietf.org/rfc/rfc2396.txt for details.
    We're only approximating to the spec.
    """
    uri_re = re.compile(r"^[A-Za-z][A-Za-z0-9+-.]*:\S\S*$")
    return uri_re.search(uri)


#
# Relationships
#

# relate3 is replaced by a stub when unit testing
from schooltool.relationships import relate as relate3

def relate(relationship_type, (a, role_a), (b, role_b), title=None):
    """See IRelationshipAPI"""
    # XXX This is to avoid a circular import
    from schooltool.membership import MemberLink, GroupLink
    from schooltool.event import RelationshipAddedEvent, MemberAddedEvent

    if relationship_type is URIMembership:
        if title is not None and title != "Membership":
            raise TypeError(
                "A relationship of type URIMembership must have roles"
                " URIMember and URIGroup, and the title (if any) must be"
                " 'Membership'.")

        r = Set((role_a, role_b))
        try:
            r.remove(URIMember)
            r.remove(URIGroup)
        except KeyError:
            raise TypeError(
                "A relationship of type URIMembership must have roles"
                " URIMember and URIGroup, and the title (if any) must be"
                " 'Membership'.")

        if r:
            raise TypeError(
                "A relationship of type URIMembership must have roles"
                " URIMember and URIGroup, and the title (if any) must be"
                " 'Membership'.")

        if role_a is URIGroup:
            group, member = a, b
            name = group.add(member)
            links = (MemberLink(group, member, name),
                     GroupLink(member, group, name))
        else:
            group, member = b, a
            name = group.add(member)
            links = (GroupLink(member, group, name),
                     MemberLink(group, member, name))
        event = MemberAddedEvent(links)
    else:
        links = relate3(relationship_type, (a, role_a), (b, role_b),
                        title=title)
        event = RelationshipAddedEvent(links)

    event.dispatch(a)
    event.dispatch(b)
    return links


def getRelatedObjects(obj, role):
    """See IRelationshipAPI"""
    return [link.traverse() for link in obj.listLinks(role)]


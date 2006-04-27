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
Macros

$Id$
"""
import zope.interface

from zope.app import zapi
from zope.publisher.browser import BrowserView

from zope.app import basicskin

class StandardMacros(basicskin.standardmacros.StandardMacros):
    macro_pages = ('view_macros', 'dialog_macros',)


class SchoolToolMacros(BrowserView):
    zope.interface.implements(zope.interface.common.mapping.IItemMapping)

    macro_pages = ('calendar_macros', 'generic_macros')

    def __getitem__(self, key):
        name = key + '_macros'

        if name in self.macro_pages:
            return zapi.getMultiAdapter((self.context, self.request), name=name)

        raise KeyError, key

#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
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

from zope.cachedescriptors.property import Lazy
from zope.component import adapts

from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.skin import flourish
from schooltool.task.interfaces import IRemoteTask
from schooltool.task.tasks import TaskReadStatus

from schooltool.common import SchoolToolMessage as _


class TaskContainer(flourish.page.Page):

    @property
    def tasks(self):
        return sorted(self.context.values(), key=lambda t: (str(t.scheduled), t.task_id))


class TaskStatus(flourish.page.Page):

    @Lazy
    def status(self):
        return TaskReadStatus(self.task_id)

    @property
    def task_id(self):
        return self.context.task_id


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
from __future__ import absolute_import

import sys
import datetime
import pkg_resources
import pytz

import celery.task
import celery.result
import celery.utils
import celery.states
import transaction
import transaction.interfaces
from celery.task import task, periodic_task
from persistent import Persistent
from zope.interface import implements, implementer
from zope.component import adapter
from zope.container.btree import BTreeContainer
from zope.container.contained import Contained
from zope.interface import implements
from ZODB.POSException import ConflictError
from zope.component.hooks import getSite, setSite
from zope.app.publication.zopepublication import ZopePublication

from schooltool.app.app import StartUpBase
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.task.celery import open_schooltool_db
from schooltool.task.interfaces import IRemoteTask, ITaskContainer


IN_PROGRESS = 'IN_PROGRESS'
COMMITTING = 'COMMITTING_ZODB'


class NoDatabaseException(Exception):
    pass


class DBTaskMixin(object):

    db_connection = None
    schooltool_app = None
    track_started = True

    def __call__(self, *args, **kwargs):
        db = open_schooltool_db(self.app)
        if db is None:
            raise NoDatabaseException()
        self.db_connection = db.open()
        root = self.db_connection.root()
        self.schooltool_app = root[ZopePublication.root_name]
        transaction.begin()
        site = getSite()
        setSite(self.schooltool_app)
        fatal_exc = None
        recoverable_exc = None
        try:
            result = self.run(*args, **kwargs)
        except Exception, fatal_exc:
            transaction.abort()

        if fatal_exc is None:
            try:
                status = TaskWriteStatus(self.request.id)
                status.set_committing()
                transaction.commit()
            except ConflictError, recoverable_exc:
                pass
        self.schooltool_app = None
        setSite(site)
        self.db_connection.close()
        self.db_connection = None
        if fatal_exc is not None:
            raise fatal_exc
        if recoverable_exc is not None:
            max_retries = getattr(self, 'max_db_conflict_retries',
                                  self.app.conf.SCHOOLTOOL_RETRY_DB_CONFLICTS)
            raise self.retry(exc=recoverable_exc, retries=max_retries)
        return result


class DBTask(DBTaskMixin, celery.task.Task):
    abstract = True

    @property
    def remote_task(self):
        app = ISchoolToolApplication(None)
        tasks = ITaskContainer(app)
        return tasks.get(self.request.id)


def db_task(*args, **kw):
    return celery.task.task(*args, **dict({'base': DBTask}, **kw))


class PeriodicDBTask(DBTaskMixin, celery.task.PeriodicTask):
    abstract = True


def periodic_db_task(*args, **kw):
    return celery.task.task(*args, **dict({'base': PeriodicDBTask}, **kw))


class TaskTransactionManager(object):
    implements(transaction.interfaces.IDataManager)

    tpc_result = None
    task = None
    options = None

    tracker = None

    def __init__(self, tracker, task, args, kwargs, **options):
        self.task = celery.task.subtask(task, args=args, kwargs=kwargs)
        self.options = options
        self.tracker = tracker

    @property
    def transaction_manager(self):
        return transaction.manager

    def abort(self, transaction):
        self.task = None
        self.optons = None
        self.tracker = None
        if self.tpc_result is not None:
            self.tpc_result.revoke()

    # TPC protocol: tpc_begin commit tpc_vote (tpc_finish | tpc_abort)

    def tpc_begin(self, transaction):
        pass

    def commit(self, transaction):
        pass

    def tpc_vote(self, transaction):
        # XXX: actual commit should happen in tpc_finish.  Now, if other manager(s)
        #      fail the vote, there's no guarantee that the task can be aborted.
        self.tpc_result = self.task.apply_async(
            task_id=self.tracker.task_id, **self.options)

    def tpc_finish(self, transaction):
        pass

    def tpc_abort(self, transaction):
        try:
            self.tpc_result.revoke()
        except Exception, e:
            print >> sys.stderr, 'Failed to revoke task %s with exception %r' % (
                self.tpc_result, e)

    def sortKey(self):
        return '~schooltool:%s:%s' % (
            self.__class__.__name__, id(self))


class RemoteTask(Persistent, Contained):
    implements(IRemoteTask)

    task_id = None
    handler = None
    scheduled = None

    def __init__(self):
        Persistent.__init__(self)
        Contained.__init__(self)
        self.task_id = celery.utils.uuid()

    @property
    def async_result(self):
        return celery.task.Task.AsyncResult(self.task_id)

    @property
    def internal_state(self):
        return self.async_result.state

    @property
    def working(self):
        # Note: only works if celery task has track_started set
        return self.async_result.state == celery.states.STARTED

    @property
    def finished(self):
        # Note: non-existing tasks will be permanently pending on
        #       at least some celery backends
        return self.async_result.ready()

    @property
    def succeeded(self):
        return self.async_result.successful()

    @property
    def failed(self):
        return self.async_result.failed()

    @property
    def result(self):
        return self.async_result.result

    @property
    def traceback(self):
        return self.async_result.traceback

    def schedule(self, handler=None, args=(), kwargs=None, **options):
        if handler is None:
            handler = self.handler
        assert handler is not None
        assert self.task_id is not None
        if kwargs is None:
            kwargs = {}
        current_transaction = transaction.get()
        resource = TaskTransactionManager(
                self, task=handler, args=args, kwargs=kwargs, **options
                )
        current_transaction.join(resource)
        app = ISchoolToolApplication(None)
        tasks = ITaskContainer(app)
        tasks[self.task_id] = self
        self.scheduled = self.utcnow
        return self

    @property
    def utcnow(self):
        return pytz.UTC.localize(datetime.datetime.utcnow())


class TaskContainer(BTreeContainer):
    implements(ITaskContainer)


@adapter(ISchoolToolApplication)
@implementer(ITaskContainer)
def getTaskContainerForApp(app):
    return app['schooltool.tasks']


class TasksStartUp(StartUpBase):

    def __call__(self):
        if 'schooltool.tasks' not in self.app:
            self.app['schooltool.tasks'] = TaskContainer()


class TaskReadStatus(object):

    task_id = None
    _meta = None
    _progress_states = (celery.states.STARTED, IN_PROGRESS)

    def __init__(self, task_id):
        self.task_id = task_id
        self._meta = None, None, None
        self.reload()

    def reload(self):
        result = celery.task.Task.AsyncResult(self.task_id)
        self._meta = result.state, result.result, result.traceback

    @property
    def state(self):
        return self._meta[0]

    @property
    def in_progress(self):
        return (self.state in self._progress_states or self.committing)

    @property
    def committing(self):
        return self.state == COMMITTING

    @property
    def pending(self):
        return self.state in celery.states.UNREADY_STATES

    @property
    def finished(self):
        return self.state in celery.states.READY_STATES

    @property
    def failed(self):
        return self.state in celery.states.PROPAGATE_STATES

    @property
    def succeeded(self):
        return self.state == celery.states.SUCCESS

    @property
    def progress(self):
        if self.in_progress:
            return self._meta[1]

    @property
    def result(self):
        if self.succeeded:
            return self._meta[1]

    @property
    def failure(self):
        if self.failed:
            return self._meta[1]

    @property
    def info(self):
        return self._meta[1]

    @property
    def traceback(self):
        return self._meta[2]


class NotInProgress(Exception):
    pass


undefined = object()

class TaskWriteStatus(TaskReadStatus):

    def set_progress(self, progress=None):
        result = celery.task.Task.AsyncResult(self.task_id)
        # XXX: only check this if task.track_started
        if result.state not in self._progress_states:
            raise NotInProgress(result.state, self._progress_states)
        result.backend.store_result(result.task_id, progress, IN_PROGRESS)
        self.reload()

    def set_committing(self):
        result = celery.task.Task.AsyncResult(self.task_id)
        # XXX: only check this if task.track_started
        if result.state not in self._progress_states:
            raise NotInProgress(result.state, self._progress_states)
        result.backend.store_result(result.task_id, self.info, COMMITTING)
        self.reload()


def load_plugin_tasks():
    task_entries = list(pkg_resources.iter_entry_points('schooltool.tasks'))
    for entry in task_entries:
        entry.load()

load_plugin_tasks()

#!/usr/bin/env python2.3
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
Schooltool HTTP server.

$Id$
"""

import os
import sys
import ZConfig
import urllib
import copy
import getopt
from persistence import Persistent
from transaction import get_transaction
from zodb.interfaces import ConflictError
from twisted.web import server, resource
from twisted.internet import reactor
from twisted.protocols import http
from twisted.python import threadable
from twisted.python import failure

from schooltool.mockup import FakeApplication, RootView

__metaclass__ = type


#
# HTTP server
#

SERVER_VERSION = "SchoolTool/0.1"

class Request(server.Request):
    """Threaded request processor, integrated with ZODB"""

    reactor_hook = reactor
    get_transaction_hook = get_transaction

    def process(self):
        """Process the request"""

        # Do all the things server.Request.process would do
        self.site = self.channel.site
        self.setHeader('Server', SERVER_VERSION)
        self.setHeader('Date', http.datetimeToString())
        self.setHeader('Content-Type', "text/html")
        self.prepath = []
        self.postpath = map(urllib.unquote, self.path[1:].split('/'))

        # But perform traversal and rendering in a separate worker thread
        self.reactor_hook.callInThread(self._process)

    def _process(self):
        """Process the request in a separate thread.

        Every request gets a separate transaction and a separate ZODB
        connection.
        """
        self.zodb_conn = None
        try:
            try:
                retries = self.site.conflictRetries
                while True:
                    try:
                        self.zodb_conn = self.site.db.open()
                        resrc = self.traverse()
                        body = self.render(resrc)
                        txn = self.get_transaction_hook()
                        txn.note(self.path)
                        txn.setUser(self.getUser()) # anonymous is ""
                        txn.commit()
                    except ConflictError:
                        if retries <= 0:
                            raise
                        retries -= 1
                        self.get_transaction_hook().abort()
                        self.zodb_conn.close()
                        self.reset()
                    else:
                        break
            except:
                self.get_transaction_hook().abort()
                self.reactor_hook.callFromThread(self.processingFailed,
                                                 failure.Failure())
            else:
                self.reactor_hook.callFromThread(self.write, body)
                self.reactor_hook.callFromThread(self.finish)
        finally:
            if self.zodb_conn:
                self.zodb_conn.close()
                self.zodb_conn = None

    def reset(self):
        """Resets the state of the request.

        Clears all cookies, headers.  In other words, undoes any changes
        caused by calling setHeader, addCookie, setResponseCode, redirect,
        setLastModified, setETag.

        Limitation: this method does not undo changes made by calling setHost.

        You may not call reset if the response is already partially written
        to the transport.
        """

        # should not happen
        assert not self.startedWriting, 'cannot reset at this state'

        self.cookies = []
        self.headers = {}
        self.lastModified = None
        self.etag = None
        self.setResponseCode(http.OK)

    def traverse(self):
        """Locate the resource for this request.

        This is called in a separate thread.
        """

        # Do things usually done by Site.getResourceFor
        self.sitepath = copy.copy(self.prepath)
        self.acqpath = copy.copy(self.prepath)

        # Get a persistent application object from ZODB
        root = self.zodb_conn.root()
        app = root[self.site.rootName]
        resource = self.site.viewFactory(app)
        return resource.getChildForRequest(self)

    def render(self, resrc):
        """Render a resource.

        This is called in a separate thread.
        """
        body = resrc.render(self)

        assert isinstance(body, str), "render did not return a string"

        if self.method == "HEAD":
            if len(body) > 0:
                self.setHeader('Content-Length', len(body))
            return ''
        else:
            self.setHeader('Content-Length', len(body))
            return body


class Site(server.Site):
    """Site for serving requests based on ZODB"""

    __super = server.Site
    __super___init__ = __super.__init__
    __super_buildProtocol = __super.buildProtocol

    conflictRetries = 5     # retry up to 5 times on ZODB ConflictErrors

    def __init__(self, db, rootName, viewFactory):
        """Creates a site.

        Arguments:
          db            ZODB database
          rootName      name of the application object in the database
          viewFactory   factory for the application object views
        """
        self.__super___init__(None)
        self.db = db
        self.viewFactory = viewFactory
        self.rootName = rootName

    def buildProtocol(self, addr):
        channel = self.__super_buildProtocol(addr)
        channel.requestFactory = Request
        return channel

#
# Main loop
#

class Server:
    """SchoolTool HTTP server."""

    threadable_hook = threadable
    reactor_hook = reactor
    get_transaction_hook = get_transaction

    def configure(self, args):
        """Process command line arguments and configuration files.

        This is called automatically from run.

        The following attributes define server configuration and are set by
        this method:
          appname       name of the application instance in ZODB
          config        configuration loaded from a config file, contains the
                        following attributes (see schema.xml for the definitive
                        list):
                            thread_pool_size
                            listen
                            database
        """

        # Defaults
        config_file = self.findDefaultConfigFile()
        self.appname = 'schooltool'

        # Process command line arguments
        opts, args = getopt.getopt(args, 'c:m', ['config=', 'mockup'])

        # Read configuration file
        for k, v in opts:
            if k in ('-c', '--config'):
                config_file = v
        self.config = self.loadConfig(config_file)

        # Process any command line arguments that may override config file
        # settings here.
        for k, v in opts:
            if k in ('-m', '--mockup'):
                self.appname = 'mockup'

    def findDefaultConfigFile(self):
        """Returns the default config file pathname."""
        dirname = os.path.dirname(__file__)
        dirname = os.path.normpath(os.path.join(dirname, '..', '..'))
        config_file = os.path.join(dirname, 'schooltool.conf')
        if not os.path.exists(config_file):
            config_file = os.path.join(dirname, 'schooltool.conf.in')

    def loadConfig(self, config_file):
        """Loads configuration from a given config file."""
        dirname = os.path.dirname(__file__)
        schema = ZConfig.loadSchema(os.path.join(dirname, 'schema.xml'))
        self.notifyConfigFile(config_file)
        config, handler = ZConfig.loadConfig(schema, config_file)
        return config

    def run(self, args):
        """Starts the SchoolTool HTTP server."""

        self.configure(args)

        self.threadable_hook.init()
        self.reactor_hook.suggestThreadPoolSize(self.config.thread_pool_size)

        db = self.config.database.open()
        self.ensureAppExists(db, self.appname)

        site = Site(db, self.appname, RootView)
        for interface, port in self.config.listen:
            self.reactor_hook.listenTCP(port, site, interface=interface)
            self.notifyServerStarted(interface, port)

        self.reactor_hook.run()

    def ensureAppExists(self, db, appname):
        """Makes sure the database has an application instance.

        Creates the application if necessary.
        """
        conn = db.open()
        root = conn.root()
        if root.get(appname) is None:
            root[appname] = FakeApplication()
            self.get_transaction_hook().commit()
        conn.close()

    def notifyConfigFile(self, config_file):
        print "Reading configuration from %s" % config_file

    def notifyServerStarted(self, network_interface, port):
        print "Started HTTP server on %s:%s" % (network_interface or "*", port)


def main():
    """Starts the SchoolTool HTTP server."""
    Server().run(sys.argv[1:])


if __name__ == '__main__':
    main()


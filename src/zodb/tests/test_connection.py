##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
import unittest

from persistence import Persistent
from persistence.dict import PersistentDict
from transaction.tests.abstestIDataManager import IDataManagerTests
from transaction import get_transaction

from zodb.db import DB
from zodb.storage.mapping import MappingStorage
from zodb.ztransaction import Transaction
from zodb.interfaces import ReadConflictError, ConflictError

class P(Persistent):
    pass

class Independent(Persistent):

    def _p_independent(self):
        return True

class DecoyIndependent(Persistent):

    def _p_independent(self):
        return False

class ConnectionTests(IDataManagerTests):

    def setUp(self):
        self.db = DB(MappingStorage())
        self.datamgr = self.db.open()
        self.obj = P()
        self.txn_factory = Transaction

    def tearDown(self):
        # Make sure the test doesn't leave a transaction active.
        get_transaction().abort()

    def get_transaction(self):
        t = super(ConnectionTests, self).get_transaction()
        t.setUser('IDataManagerTests')
        t.note('dummy note')
        return t

    def test_cacheGC(self):
        self.datamgr.cacheGC()

    def testReadConflict(self, shouldFail=True):
        # Two transactions run concurrently.  Each reads some object,
        # then one commits and the other tries to read an object
        # modified by the first.  This read should fail with a conflict
        # error because the object state read is not necessarily
        # consistent with the objects read earlier in the transaction.

        r1 = self.datamgr.root()
        r1["p"] = self.obj
        self.obj.child1 = P()
        get_transaction().commit()

        # start a new transaction with a new connection
        cn2 = self.db.open()
        r2 = cn2.root()

        # start a new transaction with the other connection
        txn = get_transaction()
        txn.suspend()

        self.obj.child2 = P()
        get_transaction().commit()

        # resume the transaction using cn2
        txn.resume()
        obj = r2["p"]
        # An attempt to access obj should fail, because r2 was read
        # earlier in the transaction and obj was modified by the othe
        # transaction.
        if shouldFail:
            self.assertRaises(ReadConflictError, lambda: obj.child1)
        else:
            # make sure that accessing the object succeeds
            obj.child1
        txn.abort()

    def testReadConflictIgnored(self):
        # Test that an application that catches a read conflict and
        # continues can not commit the transaction later.
        root = self.datamgr.root()
        root["real_data"] = real_data = PersistentDict()
        root["index"] = index = PersistentDict()

        real_data["a"] = PersistentDict({"indexed_value": False})
        real_data["b"] = PersistentDict({"indexed_value": True})
        index[True] = PersistentDict({"b": 1})
        index[False] = PersistentDict({"a": 1})
        get_transaction().commit()

        # load some objects from one connection
        cn2 = self.db.open()
        r2 = cn2.root()
        real_data2 = r2["real_data"]
        index2 = r2["index"]

        # start a new transaction with the other connection
        txn = get_transaction()
        txn.suspend()

        real_data["b"]["indexed_value"] = False
        del index[True]["b"]
        index[False]["b"] = 1
        get_transaction().commit()

        # switch back to the other transaction
        txn.resume()

        del real_data2["a"]
        try:
            del index2[False]["a"]
        except ReadConflictError:
            # This is the crux of the text.  Ignore the error.
            pass
        else:
            self.fail("No conflict occurred")

        # real_data2 still ready to commit
        self.assert_(real_data2._p_changed)

        # index2 values not ready to commit
        self.assert_(not index2._p_changed)
        self.assert_(not index2[False]._p_changed)
        self.assert_(not index2[True]._p_changed)

        self.assertRaises(ConflictError, txn.commit)
        get_transaction().abort()

    def testIndependent(self):
        self.obj = Independent()
        self.testReadConflict(shouldFail=False)

    def testNotIndependent(self):
        self.obj = DecoyIndependent()
        self.testReadConflict()

    def testAbortBeforeVote(self):
        self.datamgr.root()["obj"] = self.obj
        get_transaction().commit()
        x = self.obj.child = P()
        self.assert_(self.obj._p_changed)
        get_transaction().abort()
        self.assertEqual(getattr(self.obj, "child", None), None)
        self.assertEqual(x._p_oid, None)

    def tearDown(self):
        self.datamgr.close()
        self.db.close()

def test_suite():
    return unittest.makeSuite(ConnectionTests)

#!/usr/bin/env python


from functools import wraps
import os
import datetime
from couchbasedbx import *



class OpLog(object):
    def __init__(self, **kwargs):
        pass


    def log_start(self, **kwargs):
        pass


    def log_end(self, **kwargs):
        pass
    


def generate_op_record_key(oplog_record):
    return '%s_%s' % (oplog_record.record_type, datetime.datetime.utcnow().isoformat()) 



class CouchbaseOpLog(OpLog):
    def __init__(self, **kwargs):
        couchbase_host = kwargs.get('hostname', 'localhost')
        bucket_name = kwargs.get('bucket', 'default')
        self.couchbase_server = CouchbaseServer(couchbase_host)
        self.pmgr = CouchbasePersistenceManager(self.couchbase_server, bucket_name)
        self.pmgr.register_keygen_function('op_record', generate_op_record_key)


    def log_start(self, **kwargs):
        op_record = CouchbaseRecordBuilder('op_record').add_fields(kwargs).build()
        return self.pmgr.insert_record(op_record)


    def log_end(self, **kwargs):
        op_record = CouchbaseRecordBuilder('op_record').add_fields(kwargs).build()
        self.pmgr.insert_record(op_record)
    


class ContextDecorator(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


    def __enter__(self):
        return self


    def __exit__(self, typ, val, traceback):
        pass


    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return wrapper

    
    
class journal(ContextDecorator):
    def __init__(self, op_name, op_log):
        self.op_log = op_log
        self.op_name = op_name


    def __enter__(self):
        print 'writing oplog START record...'
        record = dict(timestamp=datetime.datetime.now().isoformat(),
                      phase='start',
                      pid=os.getpid(),
                      op_name=self.op_name)
        
        self.op_log.log_start(**record)
        return self


    def __exit__(self, typ, val, traceback):
        print 'writing oplog END record:...'
        record = dict(timestamp=datetime.datetime.now().isoformat(),
                      phase='end',
                      pid=os.getpid(),
                      op_name=self.op_name)
        
        self.op_log.log_end(**record)
        return self

    

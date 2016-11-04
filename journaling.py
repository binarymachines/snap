#!/usr/bin/env python


from functools import wraps
import os
import datetime
from couchbasedbx import *




def generate_op_record_key(oplog_record):
    return '%s_%s' % (oplog_record.record_type, datetime.datetime.utcnow().isoformat()) 




class OpLogField(object):
    def __init__(self, name):
        self.name = name

    def _value(self):
        '''return data to be logged'''

    def data(self):
        return { self.name : self._value() }

    

class OpLogEntry(object):
    def __init__(self, **kwargs):
        self.fields = []


    def add_field(self, op_log_field):
        self.fields.append(op_log_field)
        return self


    def data(self):
        result = {}
        for field in self.fields:
            result.update(field.data())
        return result
    

    
class TimestampField(OpLogField):
    def __init__(self):
        OpLogField.__init__(self, 'timestamp')
        #self.time = datetime.datetime.now().isoformat() 

        
    def _value(self):
        return datetime.datetime.now().isoformat()

    

class StatusField(OpLogField):
    def __init__(self, status_name):
        OpLogField.__init__(self, 'status')
        self.status = status_name


    def _value(self):
        return self.status


    
class PIDField(OpLogField):
    def __init__(self):
        OpLogField.__init__(self, 'pid')
        self.process_id = os.getpid()


    def _value(self):
        return self.process_id


    
    
class RecordPageField(OpLogField):
    def __init__(self, num_records, reading_frame):
        OpLogField.__init__(self, 'record_page')
        self.num_records = num_records
        self.page_number = reading_frame.index_number 

    def _value(self):
        return { 'num_records' : self.num_records,
                 'page_number': self.reading_frame.index_number,
                 'page_size': self.reading_frame.page_size
        }

    

class OpLogWriter(object):

    def write(self, **kwargs):
        '''implement in subclasses'''
        pass



    
class CouchbaseOpLogWriter(OpLogWriter):
    def __init__(self, **kwargs):
        couchbase_host = kwargs.get('hostname', 'localhost')
        bucket_name = kwargs.get('bucket', 'default')
        self.couchbase_server = CouchbaseServer(couchbase_host)
        self.pmgr = CouchbasePersistenceManager(self.couchbase_server, bucket_name)
        self.pmgr.register_keygen_function('op_record', generate_op_record_key)


    def write(self, **kwargs):
        op_record = CouchbaseRecordBuilder('op_record').add_fields(kwargs).build()
        return self.pmgr.insert_record(op_record)

        


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
    def __init__(self, op_name, oplog_writer, start_entry, end_entry = None):
        self.oplog_writer = oplog_writer
        self.op_name = op_name
        self.start_entry = start_entry
        self.end_entry  = end_entry
        

    def __enter__(self):
        print 'writing oplog START record...'
        record = self.start_entry.data()
        record['op_name'] = self.op_name
        self.oplog_writer.write(**record)
        return self


    def __exit__(self, typ, val, traceback):        
        if self.end_entry:
            print 'writing oplog END record:...'
            record = self.end_entry.data()
            record['op_name'] = self.op_name
            self.oplog_writer.write(**record)

        return self

    

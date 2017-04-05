#!/usr/bin/env python


from couchbase.bucket import Bucket
from couchbase.n1ql import N1QLQuery
from couchbase.exceptions import CouchbaseError
import json


class MissingKeygenFunctionError(Exception):
    def __init__(self, type_name):
        Exception.__init__(self, 'No key generator function registered for record type %s.' % type_name)

        

class NoRecordForKeyError(Exception):
    def __init__(self, key):
        Exception.__init__(self, 'No value in database for key: %s' % key)


        
class CouchbaseServer(object):
    def __init__(self, hostname):
        self.hostname = hostname

        
    def connection_url(self, bucket_name):
        return 'couchbase://%s/%s' % (self.hostname, bucket_name)


    def get_bucket(self, bucket_name, password=None):
        if password:
            return Bucket(self.connection_url(bucket_name), password)
        
        return Bucket(self.connection_url(bucket_name))

    

class CouchbaseRecord(object):
    def __init__(self, record_type, **kwargs):
        self.record_type = record_type

        

def rec2dict(couchbase_record):
    return couchbase_record.__dict__



class CouchbaseRecordBuilder(object):
    def __init__(self, record_type_name):
        self.record_type = record_type_name
        self.fields = {}

        
    def add_field(self, name, value):
        self.fields[name] = value
        return self

    
    def add_fields(self, param_dict):
        self.fields.update(param_dict)
        return self


    def from_json(self, json_doc):
        self.fields.update(json.loads(json_doc))
        return self
    

    def build(self):
        new_record = CouchbaseRecord(self.record_type)
        for (name, value) in self.fields.iteritems():
            setattr(new_record, name, value)

        return new_record
        
        
        
class CouchbasePersistenceManager(object):
    def __init__(self, couchbase_server, bucket_name, **kwargs):
        self.server = couchbase_server
        self.key_generation_functions = {}
        self.bucket_name = bucket_name
        self.bucket = self.server.get_bucket(bucket_name)


    def register_keygen_function(self, record_type_name, keygen_function):
        self.key_generation_functions[record_type_name] = keygen_function


    def generate_key(self, couchbase_record, **kwargs):
        keygen_func = self.key_generation_functions.get(couchbase_record.record_type)
        if not keygen_func:
            raise MissingKeygenFunctionError(couchbase_record.record_type)
        return keygen_func(couchbase_record, **kwargs)

    
    def lookup_record(self, record_type_name, key):        
        # TODO: update this logic when we start running on a cluster
        result = self.bucket.get(key, quiet=True)
        if result.success:
            data = result.value
            return CouchbaseRecordBuilder(record_type_name).add_fields(data).build()
        return None

    
    def lookup_record_raw(self, key):
        result =  self.bucket.get(key, quiet=True)
        if result.success:
            return result.value
        return None
        
    
    def insert_record(self, couchbase_record, **kwargs):
        key = self.generate_key(couchbase_record, **kwargs)
        self.bucket.insert(key, couchbase_record.__dict__)
        return key


    def update_record(self, couchbase_record, key, record_must_exist=False):
        existing_record = self.lookup_record(couchbase_record.record_type, key)
        if not existing_record and record_must_exist:
            raise NoRecordForKeyError(key)
        self.bucket.upsert(key, couchbase_record.__dict__)
    

    def update_record_raw(self, couchbase_record_dict, key):
        self.bucket.upsert(key, couchbase_record_dict)


    def retrieve_all(self, record_type_name):
        query = 'select * from %s where record_type = "%s"' % (self.bucket_name, record_type_name)
        results = self.bucket.n1ql_query(query)
        response = []
        for record in results:
            response.append(CouchbaseRecordBuilder(record_type_name).add_fields(record[self.bucket_name]).build())

        return response
            
    

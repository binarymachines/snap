#!/usr/bin/env python


from couchbase.bucket import Bucket
from couchbase.n1ql import N1QLQuery
from couchbase.exceptions import CouchbaseError


class MissingKeygenFunctionError(Exception):
    def __init__(self, type_name):
        


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
        self.key_generator = kwargs.get('keygen_function')


    def generate_key(self):
        pass
    

    
class CouchbaseRecordBuilder(object):
    def __init__(self, record_type_name):
        self.record_type = record_type_name
        self.keygen_function = keygen_function
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


    def generate_key(self, couchbase_record):
        keygen_func = self.key_generation_functions.get(couchbase_record.record_type)
        if not keygen_func:
            raise MissingKeygenFunctionError(couchbase_record.record_type)
        return keygen_func(couchbase_record)

    
    def lookup_record(self, record_type_name, key):        
        # TODO: update this logic when we start running on a cluster
        result = self.bucket.get(key, quiet=True)
        if result.success:
            data = result.value
            return CouchbaseRecordBuilder(record_type_name).from_json(data).build()
        return None

    
    def insert_record(self, couchbase_record):
        key = self.generate_key(couchbase_record)
        self.bucket.insert(key, couchbase_record.__dict__)
        return key


    def update_record(self, couchbase_record, key, record_must_exist=False):
        existing_record = self.lookup_record(couchbase_record.record_type, key)
        if not existing_record and record_must_exist:
            raise NoRecordForKeyError(key)
        self.bucket.upsert(key, couchbase_record.__dict__)
    


        

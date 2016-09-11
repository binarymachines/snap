#!/usr/bin/env python


from couchbase.bucket import Bucket
from couchbase.n1ql import N1QLQuery
from couchbase.exceptions import CouchbaseError



class CouchbaseServer(object):
    def __init__(self, hostname):
        self.hostname = hostname

        
    def connection_url(self, bucket_name):
        return 'couchbase://%s/%s' % (self.hostname, bucket_name)


    def get_bucket(self, bucket_name, password=None):
        if password:
            return Bucket(self.connection_url(bucket_name), password)
        
        return Bucket(self.connection_url(bucket_name))
        


class CouchbasePersistenceManager(object):
    def __init__(self, couchbase_server):
        self.server = couchbase_server


    


        

#!/usr/bin/env python


import os
import logging
import yaml
import redis
import json
import datetime
import ast



class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError



Structures = Enum(['pending_list',
                   'working_set',
                   'values_table',
                   'delayed_set',
                   'stats_table',
                   'segment_counter',
                   'segment_pool_table'])


SCHEMA_INIT_SECTION = 'schema'
STRUCTURE_NAMES =     'structures'


class SegmentPoolNotRegisteredError(Exception):
    def __init__(self, name):
        Exception.__init__(self, 'No segment pool registered under the name %s.' % name)



class MessageStats(object):
      def __init__(self, initData = {}):
          self.data = initData
          self.set('enqueue_time', self.currentDatestamp())
          self.set('last_dequeue_time', None)
          self.set('dequeue_count',  0)
          self.set('last_requeue_time', None)
          self.set('last_requeue_count', 0)


      def set(self, key, value):
          self.data[key] = value


      def currentDatestamp(self):
          return str(datetime.datetime.now())


      def logRequeue(self):
          self.set('last_requeue_time', self.currentDatestamp())
          self.set('last_requeue_count', self.data['last_requeue_count'] + 1)


      def logDequeue(self):
          self.set('last_dequeue_time', self.currentDatestamp())
          self.set('dequeue_count', self.data['dequeue_count'] + 1) 


      @staticmethod
      def load(messageKey, appConfig, redisServer):
          results = redisServer.instance.hget(appConfig.messageStatsTableName, messageKey)
          #print '>>> message stats for ID %s: %s' % (messageKey.uuid, results)          
          return MessageStats(ast.literal_eval(results))


      def save(self, messageKey, appConfig, redisServer):
          redisServer.instance.hset(appConfig.messageStatsTableName, messageKey, self.data)
          print 'saved message stats %s under ID %s' % (self.data, messageKey)


      def __repr__(self):
          return json.dumps(self.data, indent=4)



class DataConfig(object):
    def __init__(self, prefix):
        self.roles = ['']
        self.prefix = prefix

        
    @property
    def object_table_name(self):
        return '%s_object_table' % self.prefix

        
    @property
    def uuid_counter_name(self): 
        return '%s_uuid_counter' % self.prefix

    
    @property
    def pending_list_name(self):
        return '%s_pending_list' % self.prefix

    
    @property
    def working_set_name(self):
        return '%s_working_set' % self.prefix

    
    @property
    def delayed_set_name(self):
        return '%s_delayed_set' % self.prefix

    
    @property
    def values_table_name(self):
        return '%s_values_table' % self.prefix

    
    @property        
    def message_stats_table_name(self):
        return '%s_msg_stats_table' % self.prefix

    
    @property
    def queue_stats_table_name(self):
        return '%s_queue_stats_table' % self.prefix


    def segment_counter_name(self, segment_pool_name):
        return '%s_segment_counter_%s' % (self.prefix, segment_pool_name)


    def segment_pool_name(self, segment_pool_name):
        return '%s_segment_pool_%s' % (self.prefix, segment_pool_name)



class RedisServer(object):
    def __init__(self, hostname, port=6379):
        self.hostname = hostname
        self.port = port
        self._instance = redis.StrictRedis(hostname, port)

    def instance(self):
        return self._instance

    def newUUID(self, data_config):
        return self.instance.incr(data_config.uuid_counter_name)



class RedisObject(object):
    def __init__(self, name, redis_server):
        self.name = name
        self.redis_server = redis_server

    @property
    def redis(self):
        return self.redis_server.instance()



class Queue(RedisObject):
    def __init__(self, name, redis_server):
        RedisObject.__init__(self, name, redis_server)


    def push(self, object):
        self.redis_server.instance().lpush(self.name, object)


    def pop(self):
        return self.redis_server.instance().rpop(self.name)


    def range(self, start, end):
        return self.redis_server.instance().lrange(self.name, start, end)


class Set(RedisObject):
    def __init__(self, name, redis_server):
        RedisObject.__init__(self, name, redis_server)


    def add(self, object):
        self.redis_server.instance().sadd(self.name, object)

        
    def members(self):
        return self.redis_server.instance().smembers(self.name)
        

    

class Hashtable(RedisObject):
    def __init__(self, name, redis_server):
        RedisObject.__init__(self, name, redis_server)


    def put(self, key, value):
        self.redis_server.instance().hset(self.name, key, value)


    def get(self, key):
        return self.redis_server.instance().hget(self.name, key)
    
    
    
class SegmentPoolConfig():
    def __init__(self, name, segment_array):
        self.name = name
        self.segments = segment_array


    def save(self, redis_server, data_config):
        for s in self.segments:
            redis_server.instance.sadd(data_config.distribution_pool_name(self.name), s)



class SegmentPool():
    '''A stored list of arbitrary names ("segments") plus a counter value, for round robin work distribution.

    Remembers its place in the set of names ("segments") and returns consecutive segment names 
    on successive requests.
    '''
  

    def __init__(self, name, redis_server, app_config):        
        self.name = name        
        self.server = redis_server
        self.config = app_config
         

    @property
    def size(self):
        return len(self._loadSegments())


    def _load_segments(self):
        return list(self.server.instance.smembers(self.config.segment_pool_name(self.name)))
    


    def _get_segment(self, counter):        
        '''Return the segment ID represented by an unbounded integer value, using modulo 
        '''
        segment_array = self._load_segments()
        index = counter % len(segment_array)
        return segment_array[index]



    def next_segment(self):
        '''Return the next segment name in this pool's sequence, incrementing the internal counter.
        '''
        segment_counter_value = self.server.instance.incr(self.config.segment_counter_name(self.name)) 
        return self._get_segment(segment_counter_value)



def compose_key(*args):
    return ':'.join([str(arg) for arg in args])



'''    
class MessageID():
    def __init__(self, uuid, segment=None):
        print 'new MessageID with uuid: %s' % uuid
        self.data = (int(uuid), segment)

    
    @staticmethod
    def load(keyString):
        tokens = [t.strip() for t in keyString.split(':') if t]
        if len(tokens) > 3:
            raise Exception('Message ID string format is <uuid>:<segment>')

        uuid = tokens[1]
        segment = None
        if len(tokens) == 3:
                segment = tokens[2]

        
        newID =  MessageID(uuid, segment)
        print '>>> loaded new message ID object %s' % newID
        return newID
        

    def __repr__(self):
        if self.data[1]:
                return 'msg:%s:%s' % (self.data[0], self.data[1])
        else:
                return 'msg:%s:' % self.data[0]

            
    @property
    def uuid(self):
        return self.data[0]

    
    @property
    def segment(self):
        return self.data[1]


    
class Message(object):
    def __init__(self, message_key, payload):
        self.key = message_key
        self.payload = payload
'''        
    



        
        

      


      
        

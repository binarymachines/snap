#!/usr/bin/env python


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



Structures = Enum(['pending_list', 'working_set', 'values_table', 'delayed_set', 'stats_table', 'segment_counter', 'distribution_pool_table'])


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



class AppConfig(object):
    def __init__(self, initfileName):
        self.roles = ['']
 
        self.data = None
        with open(initfileName, 'r') as f:
            self.data = yaml.load(f)
         
        
        self.prefix = self.data['globals']['default_prefix']
        
    @property
    def uuidCounterName(self): 
        return '%s_uuid_counter' % self.prefix

    @property
    def pendingListName(self):
        return '%s_pending_list' % self.prefix

    @property
    def workingSetName(self):
        return '%s_working_set' % self.prefix

    @property
    def delayedSetName(self):
        return '%s_delayed_set' % self.prefix

    @property
    def valuesTableName(self):
        return '%s_values_table' % self.prefix
        
    @property        
    def messageStatsTableName(self):
        return '%s_msg_stats_table' % self.prefix

    @property
    def queueStatsTableName(self):
        return '%s_queue_stats_table' % self.prefix


    def segmentCounterName(self, distributionPoolName):
        return '%s_segment_counter_%s' % (self.prefix, distributionPoolName)


    def distributionPoolName(self, poolName):
        return '%s_distribution_pool_%s' % (self.prefix, poolName)
        

    @property
    def distributionPools(self):
        return self.data['distribution_pools']




class RedisServer(object):
    def __init__(self, hostname, port=6379):
        self.hostname = hostname
        self.port = port
        self.instance = redis.StrictRedis(hostname, port)

    def __call__(self):
        return self.instance

    def newUUID(self, rConfig):
        return self.instance.incr(rConfig.uuidCounterName)


    
class DistributionPoolConfig():
    def __init__(self, name, segmentArray):
        self.name = name
        self.segments = segmentArray


    def save(self, redisServer, appConfig):
        for s in self.segments:
            redisServer.instance.sadd(appConfig.distributionPoolName(self.name), s)




class DistributionPool():
    '''A stored list of arbitrary names ("segments") plus a counter value, for round robin work distribution.

    Remembers its place in the set of names ("segments") and returns consecutive segment names 
    on successive requests.
    '''
  

    def __init__(self, name, redisServer, appConfig):        
        self.name = name        
        self.server = redisServer
        self.config = appConfig
         

    @property
    def size(self):
        return len(self._loadSegments())


    def _loadSegments(self):
        return list(self.server.instance.smembers(self.config.distributionPoolName(self.name)))
    


    def _getSegment(self, counter):        
        '''Return the segment ID represented by an unbounded integer value, using modulo 

        '''
        segmentArray = self._loadSegments()
        index = int(counter % len(segmentArray))        
        return segmentArray[index]



    def nextSegment(self):
        '''Return the next segment name in this pool's sequence, incrementing the internal counter.

        '''
        segmentCounterValue = self.server.instance.incr(self.config.segmentCounterName(self.name)) 
        return self._getSegment(segmentCounterValue)

       
       
       
            



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


class QueueMessage(object):
    def __init__(self, messageKey, messagePayload):
        self.key = messageKey
        self.payload = messagePayload
        
    


class QueueServer(object):
    def __init__(self, appConfig, redisServer):
        self.config = appConfig
        self.server = redisServer
        

    def getUUID(self):
        return self.server.instance.incr(self.config.uuidCounterName)


    def purge(self):
        self.server.instance.delete(self.config.pendingListName)
        self.server.instance.delete(self.config.workingSetName)
        self.server.instance.delete(self.config.valuesTableName)
        self.server.instance.delete(self.config.delayedSetName)
        self.server.instance.delete(self.config.messageStatsTableName)



    def queueMessage(self, message, segment=None):
        msgKey = MessageID(self.getUUID(), segment)
        self.server.instance.hset(self.config.valuesTableName, msgKey, message)
        result = self.server.instance.rpush(self.config.pendingListName, msgKey)  
      
        if result < 1:
                raise Exception('rpush to list %s failed.' % self.config.pendingListName())
        stats = MessageStats()
        stats.save(msgKey, self.config, self.server)
        
        
    
    def dequeueMessage(self, segment=None):     
        '''Remove a message ID from the pending list, add it to the 
        working list, and return the matching message payload to the caller
        nondestructively. 
        '''

        messageKey = MessageID.load(self.server.instance.lpop(self.config.pendingListName))
        print '>>> Popped pending message key: %s from %s' % (messageKey, self.config.pendingListName)

        stats = MessageStats.load(messageKey, self.config, self.server)
        stats.logDequeue()
        stats.save(messageKey, self.config, self.server)
        print stats

        self.server.instance.lpush(self.config.workingSetName, messageKey)
        payload =  self.server.instance.hget(self.config.valuesTableName, messageKey)

        return QueueMessage(messageKey, payload)


    def removeMostRecentlyQueuedMessage(self, segment=None):
        '''Remove a messge from the *input* side of the queue.
        Effectively undoes the most recent message addition. Used mainly for testing.
        '''

        keyString = self.server.instance.rpop(self.config.pendingListName)
        messageKey = MessageID.load(keyString)
        print '>>> Popped most recently queued message key: %s from %s' % (messageKey, self.config.pendingListName)
        

        payload = self.server.instance.hget(self.config.valuesTableName, messageKey)

        return QueueMessage(messageKey, payload)

        

    def requeueMessage(self, messageKey):
        '''Place a message ID back on the pending list for reprocessing
        '''

        self.server.instance.rpush(self.config.pendingListName, messageKey)
        stats = Stats.load(messageKey, self.config, self.server)
        stats.logRequeue()
        stats.save(self.config, self.server)


    def requeueMessageWithDelay(self, messageKey, delayMillis):
        '''Place a message ID on the delay queue and mark it with a time offset
        in milliseconds. After the offset has expired, the message ID is eligible
        for reprocessing.
        '''

        self.server.instance.zadd(sel.config.delayedSetName, messageKey, float(delayMillis))
        
        stats = Stats.load(messageKey, self.config, self.server)
        stats.logRequeue()
        stats.save(self.config, self.server)
        
    

    def getMessageCount(self):
        return self.server.instance.llen(self.config.pendingListName)



    def deferMessage(self, instanceName, messageID, delayMillis, segment=None):
        pass



        

        
        

      


      
        

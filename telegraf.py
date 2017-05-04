#!/usr/bin/env python

import os
import sys
import threading
import time
import datetime
import json
import docopt
import common
import copy
from kafka import KafkaProducer, KafkaConsumer
from raven import Client



class IngestRecordHeader(object):
    def __init__(self, record_type, stream_id, asset_id, **kwargs):
        self._version = 1
        self._record_type = record_type
        self._stream_id = stream_id
        self._asset_id = asset_id
        self._timestamp = datetime.datetime.now().isoformat()
        self._extra_headers = []
        for key, value in kwargs.iteritems():
            self._extra_headers.append({'name': key, 'value': value})


    def data(self):
        result = {}
        result['version'] = self._version
        result['record_type'] = self._record_type
        result['stream_id'] = self._stream_id
        result['asset_id'] = self._asset_id
        result['ingest_timestamp'] = self._timestamp
        result['extra_headers'] = self._extra_headers
        return result



class IngestRecordBuilder(object):
    def __init__(self, record_header, **kwargs):
        self.header = record_header
        self.source_data = kwargs or {}


    def add_field(self, name, value):
        self.source_data[name] = value
        return self


    def build(self):
        result = {}
        result['header'] = self.header.data()
        result['body'] = self.source_data
        return result



class KafkaNode(object):
    def __init__(self, host, port=9092):
        self._host = host
        self._port = port

    def __call__(self):
        return '%s:%s' % (self._host, self._port)



def json_serializer(value):
    return json.dumps(value).encode('utf-8')


class KafkaIngestLogWriter(object):
    def __init__(self, kafka_node_array, serializer=json_serializer):
        #KafkaProducer(bootstrap_servers=['broker1:1234'])
        # = KafkaProducer(value_serializer=lambda v: json.dumps(v).encode('utf-8'))
        self.producer = KafkaProducer(bootstrap_servers=','.join([n() for n in kafka_node_array]),
                                      value_serializer=serializer,
                                      acks=1)


    def write(self, topic, ingest_record):
        return self.producer.send(topic, ingest_record)


    def sync(self, timeout=0):
        self.producer.flush(timeout or None)



class KafkaIngestLogReader(object):
    def __init__(self, topic, kafka_node_array, **kwargs):
        self._topic = topic
        self.consumer = KafkaConsumer(group_id=None,
                                      bootstrap_servers=','.join([n() for n in kafka_node_array]),
                                      auto_offset_reset='latest')

        self.consumer.subscribe(topic)

    def read(self):
        for message in self.consumer:
            print message


    @property
    def topic(self):
        return self._topic



class ConsoleErrorHandler(object):
    def __init__(self):
        pass

    def handle_error(self, exception_obj):
        print str(exception_obj)



class SentryErrorHandler(object):
    def __init__(self, sentry_dsn):
        self.client = Client(sentry_dsn)


    def handle_error(self, exception_obj):
        self.client.send(str(exception_obj))



class IngestWritePromiseQueue(threading.Thread):
    '''Queues up the Future objects returned from KafkaProducer.send() calls
       and then handles the results of failed requests in a background thread
    '''

    def __init__(self, error_handler, log, futures = [], **kwargs):
        threading.Thread.__init__(self)
        self._futures = futures
        self._error_handler = error_handler
        self._log = log
        self._debug_mode = False
        if kwargs.get('debug_mode') == True:
            self._debug_mode = True

        self._future_retry_wait_time = 0.01


    def append(self, future):
        futures = copy.deepcopy(self._futures)
        futures.append(future)
        return IngestWritePromiseQueue(self._error_handler,
                                       self._log, futures,
                                       debug_mode=self._debug_mode)


    def process_entry(self, f):
        if f.succeeded:
            if self._debug_mode:
                self._log.debug('processed write promise with result:\n%s' % f.value.__dict__)
        else:
            if self._debug_mode:
                self._log.debug('write promise failed with exception: %s' % str(f.exception))
            self._error_handler.handle_error(f.exception)


    def run(self):
        self._log.info('processing %d Futures...' % len(self._futures))
        for f in self._futures:
            while not f.is_done:
                time.sleep(self._future_retry_wait_time)
            self.process_entry(f)
        self._log.info('all futures processed.')


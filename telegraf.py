#!/usr/bin/env python

import os
import sys
import threading
import datetime
import json
import docopt
import common
import copy
from kafka import KafkaProducer, KafkaConsumer




class IngestMessageHeader(object):
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


class IngestMessageBuilder(object):
    def __init__(self, message_header, **kwargs):
        self.header = message_header
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


    def write(self, topic, ingest_message):
        return self.producer.send(topic, ingest_message)


    def sync(self, timeout=0):
        self.producer.flush(timeout or None)



class KafkaIngestLogReader(object):
    def __init__(self, topic, kafka_node_array):
        self._topic = topic
        self.consumer = KafkaConsumer(bootstrap_servers=','.join([n() for n in kafka_node_array]),
                                      auto_offset_reset='earliest')


    def read(self):
        for message in self.consumer:
            print (message)


    @property
    def topic(self):
        return self._topic


class ConsoleErrorHandler(object):
    def __init__(self):
        pass

    def handle_error(self, exception_obj):
        print str(exception_obj)



class IngestWritePromiseQueue(threading.Thread):
    '''Queues up the Future objects returned from KafkaProducer.send() calls
       and then handles the results of failed requests in a background thread
    '''

    def __init__(self, error_handler, futures = []):
        threading.Thread.__init__(self)
        self._futures = []
        self._error_handler = error_handler



    def append(self, future):
        futures = copy.deepcopy(self._futures)
        futures.append(future)
        return IngestWritePromiseQueue(self._error_handler, futures)


    def process_entry(self, f):
        if f.succeeded:
            print 'future returned successfully.'
        else:
            self._error_handler.handle_error(f.exception)


    def run(self):
        print 'processing one or more Futures...'
        for f in self._futures:
            self.process_entry(f)

        print 'done.'








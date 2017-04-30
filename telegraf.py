#!/usr/bin/env python

import os
import sys
import datetime
import json
import docopt
import common
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


class IngestWritePromiseQueue(object):
    def __init__(self):
        self.futures = []

    
    def append(self, future):
        self.futures.append(future)



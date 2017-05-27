#!/usr/bin/env python

import os
import sys
import threading
import time
import datetime
import json
import docopt
import common
import couchbasedbx as cbx
import logging
import copy
from kafka import KafkaProducer, KafkaConsumer
from raven import Client
from raven.handlers.logging import SentryHandler

from logging import Formatter


sentry_logger = logging.getLogger('telegraf_log')
client = Client('https://64488b5074a94219ba25882145864700:9129da74c26a43cd84760d098b902f97@sentry.io/163031')
telegraf_error_handler = SentryHandler() 
telegraf_error_handler.setLevel(logging.ERROR)
sentry_logger.addHandler(telegraf_error_handler)




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


def json_deserializer(value):
    return json.loads(value)


class KafkaMessageHeader(object):
    def __init__(self, header_dict):
        self.__dict__ = header_dict


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
    def __init__(self,
                 topic,
                 kafka_node_array,
                 group=None,
                 deserializer=json_deserializer,
                 **kwargs):

        self._topic = topic
        # commit on every received message by default
        self._commit_interval = kwargs.get('commit_interval', 1)
        self._consumer = KafkaConsumer(group_id=group,
                                       bootstrap_servers=','.join([n() for n in kafka_node_array]),
                                       value_deserializer=deserializer,
                                       auto_offset_reset='earliest',
                                       consumer_timeout_ms=5000)

        #self._consumer.subscribe(topic)


    def read(self, data_relay, logger):
        interval_counter = 0
        for message in self._consumer:
            data_relay.send(message, logger)
            interval_counter += 1
            if interval_counter % self._commit_interval == 0:
                self._consumer.commit()
                interval_counter = 0


    @property
    def commit_interval(self):
        return self._commit_interval


    @property
    def consumer(self):
        return self._consumer


    @property
    def topic(self):
        return self._topic



class DataRelay(object):
    def __init__(self, **kwargs):
        self._transformer = kwargs.get('transformer')


    def pre_send(self, src_message_header, logger, **kwargs):
        pass


    def post_send(self, src_message_header, logger, **kwargs):
        pass

    '''
    def _send(self, src_message_header, data, logger, **kwargs):
        pass
    '''

    def send(self, kafka_message, logger, **kwargs):
        header_data = {}
        header_data['topic'] = kafka_message.topic
        header_data['partition'] = kafka_message.partition
        header_data['offset'] = kafka_message.offset
        header_data['key'] = kafka_message.key

        kmsg_header = KafkaMessageHeader(header_data)
        self.pre_send(kmsg_header, logger, **kwargs)
        if self._transformer:
            data_to_send = self._transformer.transform(kafka_message.value['body'])
        else:
            data_to_send = kafka_message.value
        self._send(kmsg_header, data_to_send, logger, **kwargs)
        self.post_send(kmsg_header, logger, **kwargs)



class ConsoleRelay(DataRelay):
    def __init__(self, **kwargs):
        DataRelay.__init__(self, **kwargs)


    def _send(self, src_message_header, message_data, logger):
        print '### record at offset %d: %s' % (src_message_header.offset, message_data)




class CouchbaseRelay(DataRelay):
    def __init__(self, host, bucket, record_type, keygen_function, **kwargs):
        DataRelay.__init__(self, **kwargs)
        self._record_type = record_type
        couchbase_server = cbx.CouchbaseServer(host)
        self._couchbase_mgr = cbx.CouchbasePersistenceManager(couchbase_server, bucket)
        self._couchbase_mgr.register_keygen_function(self._record_type, keygen_function)


    def _send(self, src_message_header, message_data, logger):
        builder = cbx.CouchbaseRecordBuilder(self._record_type)
        builder.from_json(message_data)
        cb_record = builder.build()
        key = self._couchbase_mgr.insert_record(cb_record)
        logger.info('new record key: %s' % key)



class K2Relay(DataRelay):
    def __init__(self, target_topic, kafka_ingest_log_writer, **kwargs):
        DataRelay.__init__(self, **kwargs)
        self._target_log_writer = kafka_ingest_log_writer
        self._target_topic = target_topic


    def _send(self, kafka_message, logger):
        self._target_log_writer.write(self._target_topic, kafka_message.value)



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
        self._log = sentry_logger
        self._debug_mode = False
        if kwargs.get('debug_mode'):
            self._debug_mode = True

        self._future_retry_wait_time = 0.01


    def append(self, future):
        futures = []
        futures.extend(self._futures)
        futures.append(future)
        return IngestWritePromiseQueue(self._error_handler,
                                       self._log, futures,
                                       debug_mode=self._debug_mode)

    def append_all(self, future_array):
        futures = []
        futures.extend(self._futures)
        futures.extend(future_array)
        return IngestWritePromiseQueue(self._error_handler,
                                       self._log, futures,
                                       debug_mode=self._debug_mode)


    def process_entry(self, f):
        if not f.succeeded:
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


#!/usr/bin/env python

import os
import sys
import threading
import time
import datetime
import json
import docopt
import common
import sqldbx as sqlx
import couchbasedbx as cbx
import logging
import copy
from kafka import KafkaProducer, KafkaConsumer, KafkaClient
from kafka.protocol.offset import OffsetRequest, OffsetResetStrategy
from kafka.common import OffsetRequestPayload

from raven import Client
from raven.handlers.logging import SentryHandler

from logging import Formatter


DEFAULT_SENTRY_DSN = 'https://64488b5074a94219ba25882145864700:9129da74c26a43cd84760d098b902f97@sentry.io/163031'


class NoSuchPartitionException(Exception):
    def __init__(self, partition_id):
        Exception.__init__(self, 'The target Kafka cluster has no partition "%s".' % partition_id)



class TelegrafErrorHandler(object):
    def __init__(self, log_name, logging_level=logging.DEBUG, sentry_dsn=DEFAULT_SENTRY_DSN):
        self._sentry_logger = logging.getLogger(log_name)
        self._client = Client(sentry_dsn)
        sentry_handler = SentryHandler()
        sentry_handler.setLevel(logging_level)
        self._sentry_logger.addHandler(sentry_handler)


    @property
    def sentry(self):
        return self._sentry_logger



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


class KafkaCluster(object):
    def __init__(self, nodes=[], **kwargs):
        self._nodes = nodes


    def add_node(self, kafka_node):
        new_nodes = copy.deepcopy(self._nodes)
        new_nodes.append(kafka_node)
        return KafkaCluster(new_nodes)


    @property
    def nodes(self):
        return ','.join([n() for n in self._nodes])


    @property
    def node_array(self):
        return self._nodes



class KafkaOffsetManagementContext(object):
    def __init__(self, kafka_cluster, topic, **kwargs):
        #NOTE: keep this code for now
        '''
        self._client = KafkaClient(bootstrap_servers=kafka_cluster.nodes)
        self._metadata = self._client.cluster
        '''
        self._partition_table = {}

        consumer_group = kwargs.get('consumer_group', 'test_group')
        kreader = KafkaIngestRecordReader(topic, kafka_cluster.node_array, consumer_group)

        print '### partitions for topic %s: %s' % (topic, kreader.consumer.partitions)
        part1 = kreader.consumer.partitions[0]
        print '### last committed offset for first partition: %s' % kreader.consumer.committed(part1)


    @property
    def partitions(self):
        # TODO: figure out how to do this
        return None


    def get_offset_for_partition(self, partition_id):
        '''NOTE TO SARAH: this should stay more or less as-is, because
        however we retrieve the partition & offset data from the cluster,
        we should store it in a dictionary'''

        offset = self._partition_table.get(partition_id)
        if offset is None:
            raise NoSuchPartitionException(partition_id)
        return offset



class KafkaLoader(object):
    def __init__(self, topic, kafka_ingest_record_writer, **kwargs):
        self._topic = topic
        self._kwriter = kafka_ingest_record_writer
        kwarg_reader = common.KeywordArgReader(['record_type', 'stream_id', 'asset_id'])
        kwarg_reader.read(**kwargs)
        record_type = kwarg_reader.get_value('record_type')
        stream_id = kwarg_reader.get_value('stream_id')
        asset_id = kwarg_reader.get_value('asset_id')
        self._header = IngestRecordHeader(record_type, stream_id, asset_id)

    def load(self, data):
        msg_builder = IngestRecordBuilder(self._header)
        for key, value in data.iteritems():
            msg_builder.add_field(key, value)
        ingest_record = msg_builder.build()

        print '### writing ingest record to kafka topic: %s' % self._topic
        print ingest_record

        self._kwriter.write(self._topic, ingest_record)


class KafkaIngestRecordWriter(object):
    def __init__(self, kafka_node_array, serializer=json_serializer):
        #KafkaProducer(bootstrap_servers=['broker1:1234'])
        # = KafkaProducer(value_serializer=lambda v: json.dumps(v).encode('utf-8'))
        self.producer = KafkaProducer(bootstrap_servers=','.join([n() for n in kafka_node_array]),
                                      value_serializer=serializer,
                                      acks=1)
        log = logging.getLogger(__name__)
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s:%(message)s')
        ch.setFormatter(formatter)
        log.setLevel(logging.DEBUG)
        log.addHandler(ch)

        error_handler = ConsoleErrorHandler()
        self._promise_queue = IngestWritePromiseQueue(error_handler, log, debug_mode=True)


    def write(self, topic, ingest_record):
        future = self.producer.send(topic, ingest_record)
        self._promise_queue.append(future)
        return future


    def sync(self, timeout=0):
        self.producer.flush(timeout or None)

    def process_write_promise_queue(self):
        self._promise_queue.run()
        return self._promise_queue.errors


class KafkaIngestRecordReader(object):
    def __init__(self,
                 topic,
                 kafka_node_array,
                 group=None,
                 deserializer=json_deserializer,
                 **kwargs):

        self._topic = topic
        self._num_commits = 0
        # commit on every received message by default
        self._commit_interval = kwargs.get('commit_interval', 1)
        self._consumer = KafkaConsumer(group_id=group,
                                       bootstrap_servers=','.join([n() for n in kafka_node_array]),
                                       value_deserializer=deserializer,
                                       auto_offset_reset='earliest',
                                       consumer_timeout_ms=5000)

        #self._consumer.subscribe(topic)


    def read(self, data_relay, logger):
        message_counter = 0
        for message in self._consumer:
            data_relay.send(message, logger)
            message_counter += 1
            if message_counter % self._commit_interval == 0:
                self._consumer.commit()
                self._num_commits += 1


    @property
    def commit_interval(self):
        return self._commit_interval


    @property
    def num_commits_issued(self):
        return self._num_commits


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


    def _send(self, src_message_header, data, logger, **kwargs):
        '''Override in subclass
        '''
        pass


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



class OLAPSchemaDimension(object):
    def __init__(self, **kwargs):
        kwreader = common.KeywordArgReader(['fact_table_field_name',
                                            'dim_table_name',
                                            'key_field_name',
                                            'value_field_name',
                                            'id_lookup_function'])

        kwreader.read(**kwargs)

        self._fact_table_field_name = kwreader.get_value('fact_table_field_name')
        self._dim_table_name = kwreader.get_value('dim_table_name')
        self._key_field_name = kwreader.get_value('key_field_name')
        self._value_field_name = kwreader.get_value('value_field_name')
        self._lookup_func = kwreader.get_value('id_lookup_function')



    def lookup_id_for_value(self, value):
        return self._lookup_func(value, self._dim_table_name, self._key_field_name, self._value_field_name)


    @property
    def fact_field(self):
        return self._fact_table_field_name



class OLAPSchemaFact(object):
    def __init__(self, table_name, pk_field_name, pk_field_type):
        self._table_name = table_name
        self._pk_field = pk_field_name
        self._pk_field_type = pk_field_type



class OLAPSchemaMappingContext(object):
    def __init__(self, schema_fact):
        self._fact = schema_fact
        self._dimensions = {}
        self._direct_mappings = {}


    def map_src_record_field_to_dimension(self, src_record_field_name, olap_schema_dimension):
        self._dimensions[src_record_field_name] = olap_schema_dimension


    def map_src_record_field_to_fact_value(self, src_record_field_name, fact_field_name):
        self._direct_mappings[src_record_field_name] = fact_field_name


    def get_fact_values(self, source_record):
        data = {}
        print '### source record info: %s'%  source_record

        for src_record_field_name in self._direct_mappings.keys():
            fact_field_name = self._direct_mappings[src_record_field_name]
            data[fact_field_name] = source_record[src_record_field_name]

        for src_record_field_name in self._dimensions.keys():
            dimension = self._dimensions[src_record_field_name]
            data[dimension.fact_field] = dimension.lookup_id_for_value(source_record[src_record_field_name])

        return data



class OLAPStarSchemaRelay(DataRelay):
    def __init__(self, persistence_mgr, olap_schema_map_ctx, **kwargs):
        DataRelay.__init__(self, **kwargs)
        self._pmgr = persistence_mgr
        self._schema_mapping_context = olap_schema_map_ctx


    def _send(self, msg_header, kafka_message, logger, **kwargs):
        logger.debug("writing kafka log message to db...")
        logger.debug('### kafka_message keys: %s' % '\n'.join(kafka_message.keys()))
        outbound_record = {}
        fact_data = self._schema_mapping_context.get_fact_values(kafka_message.get('body'))

        print common.jsonpretty(fact_data)



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
        self._errors = []
        self._log = log
        self._sentry_logger = kwargs.get('sentry_logger')
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
        result = {
            'status': 'ok',
            'message': ''
        }
        if not f.succeeded:
            result['status'] = 'error'
            result['message'] = f.exception.message
            self._log.error('write promise failed with exception: %s' % str(f.exception))
            self._sentry_logger.error('write promise failed with exception: %s' % str(f.exception))
            self._error_handler.handle_error(f.exception)
        return result


    def run(self):
        self._log.info('processing %d Futures...' % len(self._futures))
        results = []
        for f in self._futures:
            while not f.is_done:
                time.sleep(self._future_retry_wait_time)
            results.append(self.process_entry(f))
        self._errors = [r for r in results if r['status'] is not 'ok']
        self._log.info('all futures processed.')


    @property
    def errors(self):
        return self._errors



class KafkaPipelineConfig(object):
    def __init__(self, yaml_config, **kwargs):
        self._user_topics = {}
        self._cluster = KafkaCluster()
        for entry in yaml_config['globals']['cluster_nodes']:
            tokens = entry.split(':')
            ip = tokens[0]
            port = tokens[1]
            self._cluster = self._cluster.add_node(KafkaNode(ip, port))

        self._raw_topic = yaml_config['raw_record_topic']
        self._staging_topic = yaml_config['staging_topic']

        if yaml_config.get('user_topics'):
            for entry in yaml_config['user_topics']:
                self._user_topics[entry['alias']] = entry['name']


    @property
    def raw_topic(self):
        return self._raw_topic


    @property
    def staging_topic(self):
        return self._staging_topic


    @property
    def node_addresses(self):
        return self._cluster.nodes
    

    @property
    def topic_aliases(self):
        return self._user_topics.keys()    
    

    @property
    def cluster(self):
        return self.cluster


    def get_user_topic(self, alias):
        topic = self._user_topics.get(alias)
        if not topic:
            raise Exception('No topic with alias "%s" registered in pipeline config' % alias)
        return topic




    
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

from sqlalchemy import Integer, String, DateTime, text, and_
from sqlalchemy import Integer, String, DateTime, Float, text

from raven import Client
from raven.handlers.logging import SentryHandler

from logging import Formatter

DEFAULT_SENTRY_DSN = 'https://64488b5074a94219ba25882145864700:9129da74c26a43cd84760d098b902f97@sentry.io/163031'


class NoSuchPartitionException(Exception):
    def __init__(self, partition_id):
        Exception.__init__(self, 'The target Kafka cluster has no partition "%s".' % partition_id)


class UnregisteredTransferFunctionException(Exception):
    def __init__(self, op_name):
        Exception.__init__(self, 'No transfer function registered under the name "%s" with transfer agent.' % op_name)


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
        kwarg_reader = common.KeywordArgReader('record_type', 'stream_id', 'asset_id')
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



class CheckpointTimer(threading.Thread):
    def __init__(self, checkpoint_function, log, **kwargs):
        threading.Thread.__init__(self)
        kwreader = common.KeywordArgReader('checkpoint_interval').read(**kwargs)
        self._seconds = 0
        self._stopped = True
        self._checkpoint_function = checkpoint_function
        self._interval = kwreader.get_value('checkpoint_interval')
        self._checkpoint_function_args = kwargs
        self._log = log

        
    def run(self):        
        self._stopped = False
        self._log.info('starting checkpoint timer at %s.' % datetime.datetime.now().isoformat())
        while not self._stopped:
            time.sleep(1)
            self._seconds += 1
            if self. _seconds >= self._interval:
                self._checkpoint_function(self._log, **self._checkpoint_function_args)
                self.reset()


    @property
    def elapsed_time(self):
        return self._seconds


    def reset(self):        
        self._seconds = 0
        self._log.info('resetting checkpoint timer at %s.' % datetime.datetime.now().isoformat())


    def stop(self):
        self._stopped = True
        self._log.info('stopping checkpoint timer at %s.' % datetime.datetime.now().isoformat())



class KafkaIngestRecordReader(object):
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


    def read(self, data_relay, logger, **kwargs): # insist on passing a checkpoint_frequency as kwarg?

        # if we are in checkpoint mode, issue a checkpoint signal every <interval> seconds
        # or every <frequency> records, whichever is shorter
        checkpoint_frequency = int(kwargs.get('checkpoint_frequency', -1))
        checkpoint_interval = int(kwargs.get('checkpoint_interval', 300))

        checkpoint_mode = False
        checkpoint_timer = None
        if checkpoint_frequency > 0:
            checkpoint_mode = True
            checkpoint_timer = CheckpointTimer(data_relay.checkpoint, logger, **kwargs)
            checkpoint_timer.start()

        message_counter = 0
        num_commits = 0
        error_count = 0

        for message in self._consumer:
            try:
                data_relay.send(message, logger)                
                if message_counter % self._commit_interval == 0:
                    self._consumer.commit()
                    num_commits += 1
                if checkpoint_mode and message_counter % checkpoint_frequency == 0:
                    data_relay.checkpoint(logger, **kwargs)
                    checkpoint_timer.reset()
            except Exception, err:
                logger.error('Kafka message reader threw an exception from its DataRelay while processing message %d: %s' % (message_counter, str(err)))
                logger.error('Offending message: %s' % str(message))
                error_count += 1
            finally:
                message_counter += 1

        logger.info('%d committed reads from topic %s, %d messages processed, %d errors.' % (num_commits, self._topic, message_counter, error_count))
        
        # issue a last checkpoint on our way out the door
        # TODO: find out if what's really needed here is a Kafka consumer
        # timeout exception handler

        if checkpoint_mode:
            try:
                logger.info('Kafka message reader issuing final checkpoint command at %s...' % datetime.datetime.now().isoformat())
                data_relay.checkpoint(logger, **kwargs)
            except Exception, err:
                logger.error('Final checkpoint command threw an exception: %s' % str(err))
            finally:    
                checkpoint_timer.stop()
        


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


    def _checkpoint(self, logger, **kwargs):
        '''Override in subclass'''
        pass


    def checkpoint(self, logger, **kwargs):
        try:
            self._checkpoint(logger, **kwargs)
            logger.info('data relay passed checkpoint at %s' % datetime.datetime.now().isoformat())
        except Exception, err:
            logger.error('data relay failed checkpoint with error:')
            logger.error(err)


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


class BulkTransferAgent(object):
    def __init__(self, **kwargs):
        kwreader = common.KeywordArgReader('local_temp_dir',
                                           'src_filename',
                                           'src_file_header',
                                           'src_file_delimiter')

        kwreader.read(kwargs)
        self._local_temp_directory = kwreader.get_value('local_temp_dir')
        self._source_filename = kwreader.get_value('src_filename')
        self._source_file_header = kwreader.get_value('src_file_header')
        self._source_file_delimiter = kwreader.get_value('src_file_delimiter')
        self._svc_registry = None
        self._transfer_functions = {}


    def register_service_objects(self, name, service_object_config):
        service_object_tbl = snap.initialize_services(service_object_config)
        self._svc_registry = common.ServiceObjectRegistry(service_object_tbl)


    def register_transfer_function(self, operation_name, transfer_function):
        self._transfer_functions[operation_name] = transfer_function


    def transfer(self, operation_name, **kwargs):
        transfer_func = self._transfer_functions.get(operation_name)
        if not transfer_func:
            raise UnregisteredTransferFunctionException(operation_name)

        transfer_func(self._svc_registry, log, **kwargs)

 

class OLAPSchemaDimension(object):
    def __init__(self, **kwargs):
        kwreader = common.KeywordArgReader('fact_table_field_name',
                                            'dim_table_name',
                                            'key_field_name',
                                            'value_field_name',
                                            'primary_key_type',
                                            'id_lookup_function')

        kwreader.read(**kwargs)

        self._fact_table_field_name = kwreader.get_value('fact_table_field_name')
        self._dim_table_name = kwreader.get_value('dim_table_name')
        self._key_field_name = kwreader.get_value('key_field_name')
        self._value_field_name = kwreader.get_value('value_field_name')
        self._pk_type = kwreader.get_value('primary_key_type')
        self._lookup_func = kwreader.get_value('id_lookup_function')


    @property
    def fact_table_field_name(self):
        return self._fact_table_field_name


    @property
    def primary_key_field_name(self):
        return self._key_field_name


    @property
    def primary_key_field_type(self):
        return self._pk_type


    def lookup_id_for_value(self, value, **kwargs):
        return self._lookup_func(value,
                                 self._dim_table_name,
                                 self._key_field_name, 
                                 self._value_field_name, 
                                 **kwargs)




class OLAPSchemaFact(object):
    def __init__(self, table_name, pk_field_name, pk_field_type):
        self._table_name = table_name
        self._pk_field = pk_field_name
        self._pk_field_type = pk_field_type

    @property
    def table_name(self):
        return self._table_name

    @property
    def primary_key_field_name(self):
        return self._pk_field

    @property
    def primary_key_field_type(self):
        return self._pk_field_type



class NonDimensionField(object):
    def __init__(self, fname, ftype):
        self._field_name = fname
        self._field_type = ftype


    @property
    def field_name(self):
        return self._field_name


    @property
    def field_type(self):
        return self._field_type



class OLAPSchemaMappingContext(object):
    def __init__(self, schema_fact):
        self._fact = schema_fact
        self._dimensions = {}
        self._direct_mappings = {}

    @property
    def fact(self):
        return self._fact

    @property
    def dimension_names(self):
        return self._dimensions.keys()

    @property 
    def non_dimension_names(self):
        return self._direct_mappings.keys()


    def get_non_dimension_field(self, field_name):
        if not self._direct_mappings.get(field_name):
            #TODO: create custom exception
            raise Exception('No non-dimensional field "%s" registered with mapping context.' % field_name)
        return self._direct_mappings[field_name]
        
    
    def get_dimension(self, dimension_name):
        if not self._dimensions.get(dimension_name):
            #TODO: create custom exception
            raise Exception('No dimension "%s" registered with mapping context.' % dimension_name)
        return self._dimensions[dimension_name]


    def map_src_record_field_to_dimension(self, src_record_field_name, olap_schema_dimension):
        self._dimensions[src_record_field_name] = olap_schema_dimension


    def map_src_record_field_to_non_dimension(self, src_record_field_name, fact_field_name, fact_field_type):
        nd_field = NonDimensionField(fact_field_name, fact_field_type)
        self._direct_mappings[src_record_field_name] = nd_field


    def get_fact_values(self, source_record, **kwargs):
        data = {}
        print '### source record info: %s'%  source_record

        for src_record_field_name in self._direct_mappings.keys():
            non_dimension_field = self._direct_mappings[src_record_field_name]
            data[non_dimension_field.field_name] = source_record[src_record_field_name]

        for src_record_field_name in self._dimensions.keys():
            dimension = self._dimensions[src_record_field_name]
            data[dimension.fact_table_field_name] = dimension.lookup_id_for_value(source_record[src_record_field_name],
                                                                                  **kwargs)

        return data



class OLAPStarSchemaRelay(DataRelay):
    def __init__(self, persistence_mgr, olap_schema_map_ctx, **kwargs):
        DataRelay.__init__(self, **kwargs)
        self._pmgr = persistence_mgr
        self._dbconnection = self._pmgr.database.engine.connect()
        self._schema_mapping_context = olap_schema_map_ctx

        fact_record_type_builder = sqlx.SQLDataTypeBuilder('FactRecord', self._schema_mapping_context.fact.table_name)
        fact_record_type_builder.add_primary_key_field(self._schema_mapping_context.fact.primary_key_field_name,
                                                       self._schema_mapping_context.fact.primary_key_field_type)

        for name in self._schema_mapping_context.dimension_names:
            fact_record_type_builder.add_field(name,
                                               self._schema_mapping_context.get_dimension(name).fact_table_field_name,
                                               self._schema_mapping_context.get_dimension(name).primary_key_field_type)

        #TODO: add non-dimension fields to builder

        for name in self._schema_mapping_context.non_dimension_names:
            nd_field = self._schema_mapping_context.get_non_dimension_field(name)
            fact_record_type_builder.add_field(nd_field.field_name,
                                               nd_field.field_type)

        self._FactRecordType = fact_record_type_builder.build()


    def _handle_checkpoint_event(self, **kwargs):
        pass


    def _send(self, msg_header, kafka_message, logger, **kwargs):
        logger.debug("writing kafka log message to db...")
        logger.debug('### kafka_message keys: %s' % '\n'.join(kafka_message.keys()))
        outbound_record = {}
        fact_data = self._schema_mapping_context.get_fact_values(kafka_message.get('body'), 
                                                                 persistence_manager=self._pmgr)

        print '### OLAP fact data:'
        print common.jsonpretty(fact_data)

        insert_query_template = '''
        INSERT INTO {fact_table} ({field_names})
        VALUES ({data_placeholders});
        '''

        data_placeholder_segment = ', '.join([':%s' % name for name in fact_data.keys()])

        print '### initial rendering of insert statement: '
        iqtemplate_render = insert_query_template.format(fact_table=self._schema_mapping_context.fact.table_name,
                                                         field_names=','.join(fact_data.keys()),
                                                         data_placeholders=data_placeholder_segment)
        print iqtemplate_render

        insert_statement = text(iqtemplate_render)
        insert_statement = insert_statement.bindparams(**fact_data)                                                     
        #dbconnection = self._pmgr.database.engine.connect()
        result = self._dbconnection.execute(insert_statement)



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
        self._user_defined_consumer_groups = {}
        self._file_references = {}

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

        if yaml_config.get('input_files'):
            for datasource_alias in yaml_config['input_files']:
                filename = yaml_config['input_files'][datasource_alias]['name']
                location = common.load_config_var(yaml_config['input_files'][datasource_alias]['location'])
                self._file_references[datasource_alias] = os.path.join(location, filename)

        if yaml_config.get('user_defined_consumer_groups'):
            for entry in yaml_config['user_defined_consumer_groups']:
                self._user_defined_consumer_groups[entry['alias']] = entry['name']

        self._transform_map = yaml_config.get('transform_map', None)


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
    def file_ref_aliases(self):
        return self._file_references.keys()


    @property
    def group_aliases(self):
        return self._user_defined_consumer_groups.keys()


    def get_user_defined_consumer_group(self, alias):
        cgroup = self._user_defined_consumer_groups.get(alias)
        if not cgroup:
            #TODO: create custom exception
            raise Exception('No consumer group with alias "%s" registered in pipeline config' % alias)
        return cgroup


    def get_file_reference(self, alias):
        fileref = self._file_references.get(alias)
        if not fileref:
            #TODO: create custom exception
            raise Exception('No file reference with alias "%s" registered in pipeline config' % alias)
        return fileref


    @property
    def cluster(self):
        return self._cluster


    def get_user_topic(self, alias):
        topic = self._user_topics.get(alias)
        if not topic:
            # TODO: create custom exception
            raise Exception('No topic with alias "%s" registered in pipeline config' % alias)
        return topic

    
    @property
    def transform_map(self):
        return self._transform_map


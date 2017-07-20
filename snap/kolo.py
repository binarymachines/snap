#!\usr\bin\env python
#
#  
'''Usage:
        kolo.py --rtype=<record_type> --pconfig=<pipeline_config_file> --topic=<topic> --pgsql_host=<host> --pgsql_user=<user> --pgsql_password=<password> [<logfile>]
'''

#
# KOLO: Kafka-OLAP LOader
# comsumes data records from a designated Kafka topic into an OLAP star schema
# 

import yaml
import docopt
import logging
import telegraf as tg
import datamap as dmap
import sqldbx
from kafka import TopicPartition, KafkaConsumer
from sqlalchemy import Integer, String, DateTime, Float, Boolean, text, and_, bindparam
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER


def get_offset(topic, pipeline_config):
    cluster = pipeline_config.cluster
    consumer_group = pipeline_config.get_user_defined_consumer_group('scratch_group_2')

    kc = KafkaConsumer(group_id=consumer_group,
                       bootstrap_servers=cluster.nodes,
                       value_deserializer=tg.json_deserializer,
                       auto_offset_reset='earliest',
                       consumer_timeout_ms=5000)

    metadata = kc.partitions_for_topic(topic)

    tp = TopicPartition(topic, list(metadata)[0])
    kc.assign([tp])
    offset = kc.position(tp)
    return offset


def get_required_dimension_id_func(value, dim_table_name, key_field_name, value_field_name, **kwargs):

    db_schema = 'olap'
    raw_template = """
    SELECT {field}
    from {schema}.{table}
    where {dim_table_value_field_name} = :source_value""".format(schema=db_schema,
                                                                 field=key_field_name,
                                                                 table=dim_table_name,
                                                                 dim_table_value_field_name=value_field_name)
    template = text(raw_template)
    stmt = template.bindparams(bindparam('source_value', String))

    data_mgr =  kwargs['persistence_manager']
    dbconnection = data_mgr.database.engine.connect()
    #db_session = data_mgr.getSession()

    result = dbconnection.execute(stmt, {"source_value": value})
    record = result.fetchone()
    if not record:
        raise Exception('returned empty result set from query: %s where value is %s' % (str(stmt), value))

    return record[0]


def get_optional_dimension_id_func(value, dim_table_name, key_field_name, value_field_name, **kwargs):
    if not value:
        return None

    else:
        db_schema = 'olap'
        raw_template = """
            SELECT {field}
            from {schema}.{table}
            where {dim_table_value_field_name} = :source_value""".format(schema=db_schema,
                                                                         field=key_field_name,
                                                                         table=dim_table_name,
                                                                         dim_table_value_field_name=value_field_name)
        template = text(raw_template)
        stmt = template.bindparams(bindparam('source_value', String))

        data_mgr = kwargs['persistence_manager']
        dbconnection = data_mgr.database.engine.connect()
        # db_session = data_mgr.getSession()

        result = dbconnection.execute(stmt, {"source_value": value})
        record = result.fetchone()
        if not record:
            raise Exception('returned empty result set from query: %s where value is %s' % (str(stmt), value))

        return record[0]


def sst_to_direct_olap(pipeline_config, pgsql_host, pgsql_username, pgsql_password, log_name, source_topic):
    fact = tg.OLAPSchemaFact('olap.f_transactions',
                                   'id',
                                   UNIQUEIDENTIFIER())

    dim_reason_code = tg.OLAPSchemaDimension(fact_table_field_name='reason_code_id',
                                                   dim_table_name='d_reason_code',
                                                   key_field_name='id',
                                                   value_field_name='value',
                                                   primary_key_type=Integer(),
                                                   id_lookup_function=get_optional_dimension_id_func)

    dim_agreement_category = tg.OLAPSchemaDimension(fact_table_field_name='agreement_category_id',
                                                          dim_table_name='d_agreement_category',
                                                          key_field_name='id',
                                                          value_field_name='value',
                                                          primary_key_type=Integer(),
                                                          id_lookup_function=get_optional_dimension_id_func)

    dim_class_of_trade = tg.OLAPSchemaDimension(fact_table_field_name='cot_id',
                                                      dim_table_name='d_class_of_trade',
                                                      key_field_name='id',
                                                      value_field_name='value',
                                                      primary_key_type=Integer(),
                                                      id_lookup_function=get_required_dimension_id_func)

    dim_location = tg.OLAPSchemaDimension(fact_table_field_name='location_id',
                                                dim_table_name='d_location',
                                                key_field_name='id',
                                                value_field_name='value',
                                                primary_key_type=Integer(),
                                                id_lookup_function=get_required_dimension_id_func)

    dim_order_type = tg.OLAPSchemaDimension(fact_table_field_name='order_type_id',
                                                  dim_table_name='d_order_type',
                                                  key_field_name='id',
                                                  value_field_name='value',
                                                  primary_key_type=Integer(),
                                                  id_lookup_function=get_required_dimension_id_func)

    mapping_context = tg.OLAPSchemaMappingContext(fact)
    mapping_context.map_src_record_field_to_dimension('order_type', dim_order_type)
    mapping_context.map_src_record_field_to_dimension('reason_code', dim_reason_code)
    mapping_context.map_src_record_field_to_dimension('agreement_id', dim_agreement_category)
    mapping_context.map_src_record_field_to_dimension('class_of_trade', dim_class_of_trade)
    mapping_context.map_src_record_field_to_dimension('loc_shipped_to', dim_location)
    mapping_context.map_src_record_field_to_non_dimension('transaction_id', 'internal_txn_id', String())
    mapping_context.map_src_record_field_to_non_dimension('price_per_each', 'txn_price', Float())
    mapping_context.map_src_record_field_to_non_dimension('customer_is_340b', 'customer_is_340b', Boolean())
    # mapping_context.map_src_record_field_to_non_dimension('', 'txn_price', Float())


    db = sqldbx.PostgreSQLDatabase(pgsql_host, 'praxis')
    db.login(pgsql_username, pgsql_password)
    pmgr = sqldbx.PersistenceManager(db)

    oss_relay = tg.OLAPStarSchemaRelay(pmgr, mapping_context)

    group = pipeline_config.get_user_defined_consumer_group('scratch_group_2')
    topic = source_topic
    kreader = tg.KafkaIngestRecordReader(topic, pipeline_config.cluster.node_array, group)

    # show how many partitions this topic spans
    metadata = kreader.consumer.partitions_for_topic(topic)
    print '### partitions for topic %s:\n%s' % (topic, '\n'.join([str(p) for p in metadata]))

    tp = TopicPartition(topic, 0)
    kreader.consumer.assign([tp])

    offset = get_offset(topic, pipeline_config)
    topic_partition = TopicPartition(topic, list(metadata)[0])

    kreader.consumer.seek(topic_partition, offset)
    log = logging.getLogger(log_name)
    kreader.read(oss_relay, log)


def main(args):
    print args

    pipeline_config_file = args['--pconfig']
    src_topic = args['--topic']
    rectype = args['--rtype']
    host = args['--pgsql_host']
    user = args['--pgsql_user']
    passw = args['--pgsql_password']
    log_file = args.get('<logfile>', 'kola-log.txt')
    pipeline_config = None

    with open(pipeline_config_file) as f:
        yaml_config = yaml.load(f)
        pipeline_config = tg.KafkaPipelineConfig(yaml_config)

    log_name = log_file + "." + rectype + "." + src_topic
    # log = logging.getLogger(log_name)
    # ch = logging.StreamHandler()
    # formatter = logging.Formatter('%(levelname)s:%(message)s')
    # ch.setFormatter(formatter)
    # log.setLevel(logging.DEBUG)
    # log.addHandler(ch)

    logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

    if rectype == 'direct_sales':
        sst_to_direct_olap(pipeline_config, host, user, passw, log_name, src_topic)


if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)

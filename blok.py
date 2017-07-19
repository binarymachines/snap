#!\usr\bin\env python
#
# 
'''Usage:   
        blok.py --rtype=<record_type> --pconfig=<pipeline_config_file> --topic=<topic> <source_datafile>
'''

# BLOK: Bulk LOader for Kafka

import docopt
import telegraf as tg
import datamap as dmap
import os, sys
import yaml
import datetime


def main(args):
    print args

    pipeline_config_file = args['--pconfig']
    datafile = args['<source_datafile>']
    target_topic = args['--topic']

    #TODO: allow user to specify stream and asset IDs
    streamid = 'test_stream_%s' % datetime.datetime.now().isoformat()
    assetid = 'test_asset_%s' % datetime.datetime.now().isoformat()  
    rectype = args['--rtype']
    pipeline_config = None

    with open(pipeline_config_file) as f:
        yaml_config = yaml.load(f)
        pipeline_config = tg.KafkaPipelineConfig(yaml_config)

    knodes = pipeline_config.cluster.node_array
    kwriter = tg.KafkaIngestRecordWriter(knodes)
    kloader = tg.KafkaLoader(target_topic,
                                   kwriter,
                                   record_type=rectype,
                                   stream_id=streamid,
                                   asset_id=assetid)
    processor = dmap.WhitespaceCleanupProcessor()

    #TODO: un-hardcode delimiter and quote character
    extractor = dmap.CSVFileDataExtractor(processor, delimiter='|', quotechar='"')
    extractor.extract(datafile, load_function=kloader.load)
    kwriter.sync(0.1)



if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)
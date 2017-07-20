#!/usr/bin/env python

'''Usage:
            seesv.py --xform=<transform_file> --xmap=<transform_map> --schema=<schema_file> --rtype=<record_type> <datafile>
            seesv.py (-t | -f) --schema=<schema_file> --rtype=<record_type> <datafile>

   Options:
            -t --test          Test the records in the target file for schema compliance
            -f --filter        Send the compliant records in the target file to stdout

'''

#
# seesv: command line utility for examining CSV files and evaluating them against a schema of required fields
#

import docopt
import os, sys
import common
import datamap as dmap
import yaml



class TransformProcessor(dmap.DataProcessor):
    def __init__(self, transformer, data_processor):
        dmap.DataProcessor.__init__(self, data_processor)
        self._transformer = transformer
        self._records = []


    def _process(self, data_dict):        
        output = self._transformer.transform(data_dict)
        #print common.jsonpretty(output)
        return output



class Dictionary2CSVProcessor(dmap.DataProcessor):
    def __init__(self, header_fields, delimiter, data_processor, **kwargs):
        dmap.DataProcessor.__init__(self, data_processor)
        self._delimiter = delimiter
        self._header_fields = header_fields
        self._record_count = 0


    def _process(self, data_dict):
        if self._record_count == 0:
            print self._delimiter.join(self._header_fields)
        else:
            record = []
            for field in self._header_fields:
                data = data_dict.get(field)
                if data is None:
                    data = ''
                record.append(str(data))
            print self._delimiter.join(record)

        self._record_count += 1
        return data_dict
        


def build_transformer(map_file_path, mapname):
    transformer_builder = dmap.RecordTransformerBuilder(map_file_path,
                                                        map_name=mapname)
    return transformer_builder.build()


def transform_data(source_datafile, src_header_fields, target_header_fields, transformer):    
    delimiter = '|'
    quote_character = '"'

    transform_proc = TransformProcessor(transformer, dmap.WhitespaceCleanupProcessor())
    d2csv_proc = Dictionary2CSVProcessor(target_header_fields, delimiter, transform_proc)
    extractor = dmap.CSVFileDataExtractor(d2csv_proc,
                                          delimiter=delimiter,
                                          quotechar=quote_character,
                                          header_fields=src_header_fields)

    extractor.extract(source_datafile)


class ComplianceStatsProcessor(dmap.DataProcessor):
    def __init__(self, required_record_fields, processor=None):
        dmap.DataProcessor.__init__(self, processor)
        self._required_fields = required_record_fields
        self._valid_record_count = 0
        self._invalid_record_count = 0
        self._error_table = {}
        self._record_index = 0


    @property
    def total_records(self):
        return self._valid_record_count + self._invalid_record_count


    @property
    def valid_records(self):
        return self._valid_record_count


    @property
    def invalid_records(self):
        return self._invalid_record_count


    def match_format(self, obj, type_name='string'):
        # TODO: use a lookup table of regexes
        '''
        if obj is None:
            return True
        '''
        return True


    def _process(self, record_dict):
        error = False
        self._record_index += 1
        for name, datatype in self._required_fields.iteritems():
            if record_dict.get(name) is None:
                error = True
                self._error_table[self._record_index] = (name, 'null')
                break
            elif not self.match_format(record_dict[name]):
                error = True
                self._error_table[self._record_index] = (name, 'invalid_type')
                break

        if error:
            self._invalid_record_count += 1
        else:
            self._valid_record_count += 1

        return record_dict


    def get_stats(self):
        validity_stats = {
        'invalid_records': self.invalid_records,
        'valid_records': self.valid_records,
        'total_records': self.total_records,
        'errors_by_record': self._error_table
        }
        return validity_stats


def get_schema_compliance_stats(source_datafile, schema_config):

    required_fields = {}
    for field_name in schema_config:
        if schema_config[field_name]['required'] == True:
            required_fields[field_name] = schema_config[field_name]['type']

    cstats_proc = ComplianceStatsProcessor(required_fields, dmap.WhitespaceCleanupProcessor())
 
    extractor = dmap.CSVFileDataExtractor(cstats_proc,
                                          delimiter='|',
                                          quotechar='"',
                                          header_fields=required_fields.keys())
    extractor.extract(source_datafile)
    return cstats_proc.get_stats()


def get_required_fields(record_type, schema_config_file):
    required_fields = []
    with open(schema_config_file) as f:
        record_config = yaml.load(f)            
        schema_config = record_config['record_types'].get(record_type)
        if not schema_config:
            raise Exception('No record type "%s" found in schema config file %s.' % (record_type, schema_config_file))
        
        for field_name in schema_config:
            required_fields.append(field_name)
    return required_fields

def get_transform_target_header(transform_config_file, map_name):
    header_fields = []
    with open(transform_config_file) as f:
        transform_config = yaml.load(f)
        transform_map = transform_config['maps'].get(map_name)
        if not transform_map:
            raise Exception('No transform map "%s" found in transform config file %s.' % (map_name, transform_config_file))
        
        header_fields = [field_name for field_name in transform_map['fields']]
    return header_fields


def main(args):

    test_mode = args.get('--test')
    filter_mode = args.get('--filter')
    transform_mode = False
    src_datafile = args.get('<datafile>')

    if args.get('--xform'):
        transform_mode = True
        transform_config_file = args.get('--xform')
        transform_map = args.get('--xmap')
        schema_config_file = args.get('--schema')
        record_type = args.get('--rtype')
        
        src_header = get_required_fields(record_type, schema_config_file)
        target_header = get_transform_target_header(transform_config_file, transform_map)
        xformer = build_transformer(transform_config_file, transform_map)
        transform_data(src_datafile, src_header, target_header, xformer)

    elif test_mode:
        #print 'testing data in source file %s for schema compliance...' % src_datafile
        schema_config_file = args.get('--schema')
        with open(schema_config_file) as f:
            record_config = yaml.load(f)
            record_type = args.get('--rtype')
            schema_config = record_config['record_types'][record_type]
            print get_schema_compliance_stats(src_datafile, schema_config)


    elif filter_mode:
        # Filter source records for schema compliance
        print 'filtering data from source file %s...' % src_datafile




if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)

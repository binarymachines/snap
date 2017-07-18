#!/usr/bin/env python

'''Usage:
            xcsv.py --xmap=<transform_map> --xform=<transform_file> <datafile>
            xcsv.py (-t | -f) --schema=<schema_file> --rtype=<record_type> <datafile>

   Options:
            -t --test          Test the records in the target file for schema compliance
            -f --filter        Send the compliant records in the target file to stdout

'''

import docopt
import os, sys
import common
import datamap as dmap
import yaml


def build_transformer(map_file_path, mapname):

    transformer_builder = dmap.RecordTransformerBuilder(map_file_path,
                                                        map_name=mapname)
    return transformer_builder.build()


def transform_data(source_datafile, transformer):
    print 'placeholder: transforming data in sourcefile %s' % (source_datafile)



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


def main(args):
    print args

    test_mode = args.get('--test')
    filter_mode = args.get('--filter')
    transform_mode = False
    src_datafile = args.get('<datafile>')

    if args.get('--xform'):
        transform_mode = True
        transform_config_file = args.get('--xform')
        transform_map = args.get('--xmap')

        xformer = build_transformer(transform_config_file, transform_map)
        transform_data(src_datafile, xformer)

    elif test_mode:
        print 'testing data in source file %s for schema compliance...' % src_datafile
        schema_config_file = args.get('--schema')
        with open(schema_config_file) as f:
            record_config = yaml.load(f)
            record_type = args.get('--rtype')
            schema_config = record_config['record_types'][record_type]
            print get_schema_compliance_stats(src_datafile, schema_config)


    elif filter_mode:
        print 'filtering data from source file %s...' % src_datafile




if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)

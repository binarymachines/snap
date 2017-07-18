#!/usr/bin/env python

'''Usage:
            map_null_bytes.py --schema=<schema_file> --rtype=<record_type> --target=<target_file> <datafile>

'''

import docopt
import datamap as dmap
import yaml


def main(args):
    print args

    schema_config_file = args.get('--schema')

    target_file = args.get('--target')
    src_file = args.get('<datafile>')

    with open(schema_config_file) as f:
        record_config = yaml.load(f)
        record_type = args.get('--rtype')
        schema_config = record_config['record_types'][record_type]
        required_fields = []
        for field_name in schema_config:
            if schema_config[field_name]['required'] == True:
                required_fields.append(field_name)
        nb_reporter = dmap.NullByteReporter()
        nb_reporter.find_null_bytes(src_file, required_fields)
        with open(target_file, 'r+') as tfile:
            for null_pair in nb_reporter.null_byte_lines_and_fields:
                tfile.write('There was a null byte found at line number %d in field %s.' % null_pair)



if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)



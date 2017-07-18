#!/usr/bin/env python

'''Usage:
            map_null_bytes.py --schema=<schema_file> --rtype=<record_type> --target=<target_file> <datafile>

'''

import docopt
import datamap as dmap
import yaml


def main(args):
    print args

    target_file = args.get('--target')
    src_file = args.get('<datafile>')

    with open(src_file) as f:
        first_line = f.readline()
        fields = first_line.split('|')
        nb_reporter = dmap.NullByteReporter()
        nb_reporter.find_null_bytes(src_file, fields)
        with open(target_file, 'w') as tfile:
            for null_pair in nb_reporter.null_byte_lines_and_fields:
                tfile.write('There was a null byte found at line number %d in field %s.\n' % null_pair)



if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)



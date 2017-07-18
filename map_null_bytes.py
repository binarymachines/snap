#!/usr/bin/env python

'''Usage:
            map_null_bytes.py <datafile>

'''

import docopt
import datamap as dmap
from snap import common


def main(args):
    print args

    src_file = args.get('<datafile>')

    with open(src_file) as f:
        first_line = f.readline()
        fields = first_line.split('|')
        nb_reporter = dmap.NullByteReporter()
        nb_reporter.find_null_bytes(src_file, fields)
        for null_pair in nb_reporter.null_byte_lines_and_fields:
            print common.jsonpretty({'line_number': null_pair[0],
                                     'field': null_pair[1]
                                     })


if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)



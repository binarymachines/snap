#!/usr/bin/env python

'''Usage:
            null_byte_filter.py <datafile>

    Options:
            -n --null         Retrieve the line numbers of the lines with null bytes ('\0') and the first field in that line containing a null byte
            -r --readable     Retrieve the lines that can be read by a csv reader (do not contain null bytes)

'''

import docopt
import datamap as dmap
from snap import common


def main(args):
    print args

    src_file = args.get('<datafile>')
    null_mode = args.get('--null')
    readable_mode = args.get('--readable')

    with open(src_file) as f:
        first_line = f.readline()
        fields = first_line.split('|')
        nb_reporter = dmap.NullByteReporter()
        if null_mode:
            nb_reporter.find_null_bytes(src_file, fields)
            for null_pair in nb_reporter.null_byte_lines_and_fields:
                print common.jsonpretty({'line_number': null_pair[0],
                                         'field': null_pair[1]
                                         })
        elif readable_mode:
            nb_reporter.find_readable_lines(src_file)
            for line in nb_reporter.readable_lines:
                record_dict = {}
                value_array = line.split('|')
                for r_index, field in enumerate(fields):
                    record_dict[field] = value_array[r_index]

                print common.jsonpretty(record_dict)


if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)



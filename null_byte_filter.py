#!/usr/bin/env python

'''Usage:
            null_byte_filter.py (-n | -d | -l) <datafile>

    Options:
            -n --null         Retrieve the line numbers of the lines with null bytes ('\0') and the first field in that line containing a null byte
            -d --readable_dict     Retrieve the lines that can be read by a csv reader (do not contain null bytes) and return lines as dictionaries
            -l --readable_line     Retrieve readable lines and just return line

'''

import docopt
import datamap as dmap
from snap import common


def main(args):
    src_file = args.get('<datafile>')
    null_mode = args.get('--null')
    readable_dict_mode = args.get('--readable_dict')
    readable_line_mode = args.get('--readable_line')

    with open(src_file) as f:
        first_line = f.readline()
        fields = first_line.split('|')
        nb_reporter = dmap.NullByteFilter()
        if null_mode:
            nb_reporter.find_null_bytes(src_file, fields)
            for null_pair in nb_reporter.null_byte_lines_and_fields:
                print common.jsonpretty({'line_number': null_pair[0],
                                         'field': null_pair[1]
                                         })
        elif readable_dict_mode:
            nb_reporter.find_readable_lines(src_file)
            for line in nb_reporter.readable_lines:
                if line == first_line:
                    continue
                record_dict = {}
                value_array = line.split('|')
                for r_index, field in enumerate(fields):
                    record_dict[field] = value_array[r_index]

                print common.jsonpretty(record_dict)

        elif readable_line_mode:
            nb_reporter.find_readable_lines(src_file)
            for line in nb_reporter.readable_lines:
                if line == first_line:
                    continue
                print line

        else:
            print "Choose an option flag for record info output"


if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)



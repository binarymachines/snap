#!/usr/bin/env python

'''Usage:
            xlcr.py <excel_file> sheets
            xlcr.py <excel_file> --sheet=<sheet> cols

'''


import os, sys
import common
import docopt
import openpyxl as xl



def get_worksheet_names(workbook):
    result = []
    for sheet in workbook.worksheets:
        result.append(sheet.title)
    return result



def main(args):
    print common.jsonpretty(args)

    excel_file = args['<excel_file>']
    workbook = xl.load_workbook(excel_file)

    #print dir(workbook)

    if args['sheets']:
        print '\n'.join(workbook.get_sheet_names())

    elif args['cols']:
        wksht_name = args['--sheet']
        worksheet = workbook.get_sheet_by_name(wksht_name)
        print dir(worksheet)

if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)
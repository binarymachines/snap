#!/usr/bin/env python

'''Usage:
            xlcr.py <excel_file> sheets
            xlcr.py <excel_file> --sheet=<sheet> --row=<rownum>
            xlcr.py <excel_file> --sheet=<sheet> --col=<col_id>
            xlcr.py <excel_file> --sheet=<sheet> --cols=<col_ids> [--delimiter=<delimiter_char>]
            xlcr.py <excel_file> --sheet=<sheet> --cell=<cell_id>
            xlcr.py <excel_file> --sheet=<sheet> --cells=<cell_range>
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


def get_row(worksheet, rownum):
    data = []
    row = worksheet[rownum]
    for cell in row:
        data.append(cell.value)
    return data


def get_column(worksheet, col_letter):
    data = []
    column = worksheet[col_letter]
    for cell in column:
        data.append(str(cell.value))
    return data


def get_columns(worksheet, col_names, delimiter):
    data = {}
    max_col_length = 0
    for colname in col_names:
        data[colname] = get_column(worksheet, colname)
        if len(data[colname]) > max_col_length:
            max_col_length = len(data[colname])
    result = []

    '''
    print "column names: %s" % data.keys()
    print "column a: %s" % data['a']
    print "column a cell 0: %s" % data['a'][0]
    print "max column length = %d" % max_col_length

    print [data[x][0] for x in ['a', 'b']]
    '''

    for index in range(0, max_col_length):
        row = delimiter.join([data[col_name][index] for col_name in col_names])
        result.append(row)
    return result


def get_cell(worksheet, cell_id):
    cell = worksheet[cell_id]
    return cell.value


def main(args):
    print common.jsonpretty(args)

    excel_file = args['<excel_file>']
    workbook = xl.load_workbook(excel_file)

    #print dir(workbook)

    if args['sheets']:
        print '\n'.join(workbook.get_sheet_names())
        exit()

    wksht_name = args['--sheet']
    worksheet = workbook.get_sheet_by_name(wksht_name)

    if args['--row']:
        rownum = args['--row']
        rowdata = get_row(worksheet, int(rownum))
        print '\n'.join(rowdata)


    if args['--col']:
        col_name = args['--col']
        coldata = get_column(worksheet, col_name)
        print '\n'.join(coldata)

    if args['--cols']:
        col_string = args['--cols']
        if args['--delimiter'] is None:
            delimiter = ','
        else:
            delimiter = args['--delimiter']
        column_names = col_string.split(',')
        coldata = get_columns(worksheet, column_names, delimiter)
        print '\n'.join(coldata)


    if args['--cell']:
        cell_id = args['--cell']
        print get_cell(worksheet, cell_id)



if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)
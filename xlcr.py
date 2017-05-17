#!/usr/bin/env python

'''Usage:
            xlcr.py <excel_file> sheets
            xlcr.py <excel_file> --sheet=<sheet> --row=<rownum>
            xlcr.py <excel_file> --sheet=<sheet> --rows=<x:y> [--delimiter=<delimiter_char>]
            xlcr.py <excel_file> --sheet=<sheet> --col=<col_id>
            xlcr.py <excel_file> --sheet=<sheet> --cols=<col_ids> [--delimiter=<delimiter_char>]
            xlcr.py <excel_file> --sheet=<sheet> --cell=<cell_id>
            xlcr.py <excel_file> --sheet=<sheet> --cells=<cell_range>
            xlcr.py -i <init_file>
'''


import os, sys
import common
import core
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
        if cell.value.__class__.__name__ == 'unicode':            
            data.append(cell.value.encode('utf-8', 'replace'))
        else:
            data.append(str(cell.value))
    return data


def get_rows(worksheet, range_string, delimiter):
    if not ':' in range_string:
        raise Exception('range designator must be of the form x:y where y > x.')

    range_values = range_string.split(':')
    min_row = int(range_values[0])
    max_row = int(range_values[0])

    if max_row < min_row:
        raise Exception('range designator must be of the form x:y where y > x.')
    if len(range_values) == 2:
        max_row = int(range_values[1])

    data = []
    for x in range(min_row, max_row):
        data.append(delimiter.join(get_row(worksheet, x)))

    return data


def get_column(worksheet, col_letter):
    data = []
    column = worksheet[col_letter]
    for cell in column:
        if cell.value.__class__.__name__ == 'unicode':            
            data.append(cell.value.encode('utf-8', 'replace'))
        else:
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

    for index in range(0, max_col_length):
        row = delimiter.join([data[col_name][index] for col_name in col_names])
        result.append(row)
    return result


def get_cell(worksheet, cell_id):
    cell = worksheet[cell_id]
    if cell.value.__class__.__name__ == 'unicode':            
        return cell.value.encode('utf-8', 'replace')
    else:
        return str(cell.value)
    


def main(args):
    #rint common.jsonpretty(args)

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


    if args['--rows']:
        range_string = args['--rows']
        if args['--delimiter'] is None:
            delimiter = ','
        else:
            delimiter = args['--delimiter']
        rowdata = get_rows(worksheet, range_string, delimiter)
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
        
        if ',' in col_string:
            column_names = col_string.split(',')
            coldata = get_columns(worksheet, column_names, delimiter)
            print '\n'.join(coldata)
        '''
        elif '-' in col_string:
            column_names = []
            first_last_cols = col_string.split('-')
            first_col = first_last_cols[0]
            last_col = first_last_cols[1]   
        '''

        


    if args['--cell']:
        cell_id = args['--cell']
        print get_cell(worksheet, cell_id)



if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)
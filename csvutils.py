#!/usr/bin/env python


import common



class MethodNotImplementedError(Exception):
    def __init__(self, method_name, klass):
        Exception.__init__(self, 'Method %s(...) in class "%s" is not implemented. Please check your subclass(es).' % (method_name, klass.__name__))

        
class NoSuchFieldInSourceRecordError(Exception):
    def __init__(self, field_name, record):
        Exception.__init__(self, 'Field %s not present in source record: %s' % str(record))


class CSVField(object):
    def __init__(self, name, field_type):
        self.name = name
        self.type = field_type



class CSVDataConverter(object):
    def convert(self, obj):
        raise MethodNotImplementedError('convert', self.__class__)
    

        
        
    
class CSVRecordMap(object):
    def __init__(self, field_array, conversion_tbl={}):
        self.delimiter = ','
        self.fields = field_array
        self.conversion_tbl = conversion_tbl
        

    def header(self, **kwargs):
        output = []
        for f in self.fields:
            output.append(f.name)

        delimiter = kwargs.get('delimiter') or self.delimiter
        return delimiter.join(output)
    

    def format(self, data, field):
        if field.type.__name__ in ['str', 'unicode']:
            return '"%s"' % data
        return str(data)
    
    
    def dictionary_to_row(self, dict, **kwargs):
        should_accept_nulls = kwargs.get('accept_nulls')
        output = []
        for f in self.fields:
            data = dict.get(f.name)
            if not data and not should_accept_nulls:
                raise NoSuchFieldInSourceRecordError(f.name, dict)
            elif not data:
                data = 'NULL'
                
            if self.conversion_tbl.get(f.name):
                output.append(self.conversion_tbl[f.name].convert(dict.get(f.name)))
            else:
                output.append(self.format(data, f))

        delimiter = kwargs.get('delimiter') or self.delimiter
        return delimiter.join(output)
    

    
class CSVRecordMapBuilder(object):
    def __init__(self):
        self.fields = []
        self.converter_map = {}
        self.field_names = set()


    def register_converter(self, data_converter, field_name):
        if field_name not in self.field_names:
            raise NoSuchCSVFieldException(field_name)
        
        self.converter_map[field_name] = data_converter
        return self


    def add_field(self, csv_field):
        if csv_field.name in self.field_names:
            raise DuplicateCSVFieldNameException(csv_field.name)
        
        self.fields.append(csv_field)
        self.field_names.add(csv_field.name)
        return self


    def build(self):
        return CSVRecordMap(self.fields, self.converter_map)
    

    



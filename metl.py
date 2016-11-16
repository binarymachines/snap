#!/usr/bin/env python



def CSVRecordField(object):
    def __init__(self, name, field_type):
        self.name = name
        self.type = field_type


def CSVRecordMapBuilder(object):
    def __init__(self):
        pass


    def register_converter(self, field)

    
def CSVRecordMap(object):
    def __init__(self, fields):
        self.default_delimiter = ','
        self.fields = fields


    def header(self):
         pass

     
    def dictionary_to_row(self, dict, **kwargs):
        output = []
        for f in self.fields:
            output.append(dict.get(f.name))

        delimiter = kwargs.get('delimiter') or self.default_delimiter
        return delimiter.join(output)
    
        


rmb = CSVRecordMapBuilder()
rmb.add_entry('name')

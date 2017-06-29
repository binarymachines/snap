#!/usr/bin/env python


import csv
import common
import yaml


class NoSuchTargetFieldException(Exception):
    def __init__(self, field_name):
        Exception.__init__(self,
                           'RecordTransformer does not contain the target field %s.' % field_name)


class NoDatasourceForFieldException(Exception):
    def __init__(self, field_name):
        Exception.__init__(self,
                           'No datasource registered for target field name %s.' % field_name)


class NoSuchLookupMethodException(Exception):
    def __init__(self, datasource_classname, method_name):
        Exception.__init__(self,
                           'Registered datasource %s has no lookup method "%s(...)' % (datasource_classname, method_name))


class NonexistentDatasourceException(Exception):
    def __init__(self, src_name, module_name):
        Exception.__init__(self, 'No datasource named "%s" in target Python module "%s".' % (src_name, module_name))



class FieldValueResolver(object):
    def __init__(self, field_name_string):
        self._field_names = field_name_string.split('|')

    def resolve(self, source_record):
        for name in self._field_names:
            if source_record.get(name):
                return source_record[name]



class ConstValueResolver(object):
    def __init__(self, value):
        self._value = value

    def resolve(self, source_record):
        return self._value



class FieldValueMap(object):
    def __init__(self):
        self._resolvers = {}


    def add_resolver(self, field_value_resolver, field_name):
        self._resolvers[field_name] = field_value_resolver


    def get_value(self, field_name, source_record):
        resolver = self._resolvers.get(field_name)
        if not resolver:
            raise Exception('No FieldValueResolver registered with value map under the name "%s".' % field_name)
        return resolver.resolve(source_record)



class RecordTransformer:
    def __init__(self):
        self.target_record_fields = set()
        self.datasources = {}
        self.field_map = {}
        self.value_map = FieldValueMap()


    def add_target_field(self, target_field_name):
        self.target_record_fields.add(target_field_name)


    def map_source_to_target_field(self, source_field_designator, target_field_name):
        if not target_field_name in self.target_record_fields:
            raise NoSuchTargetFieldException(target_field_name)
        resolver = FieldValueResolver(source_field_designator)
        self.field_map[target_field_name] = resolver
        self.value_map.add_resolver(resolver, target_field_name)


    def map_const_to_target_field(self, target_field_name, value):
        if not target_field_name in self.target_record_fields:
            raise NoSuchTargetFieldException(target_field_name)
        self.field_map[target_field_name] = ConstValueResolver(value)


    def register_datasource(self, target_field_name, datasource):
        if not target_field_name in self.target_record_fields:
            raise Exception('No target field "%s" has been added to the transformer.' % target_field_name)
        self.datasources[target_field_name] = datasource


    def lookup(self, target_field_name, source_record):
        datasource = self.datasources.get(target_field_name)
        if not datasource:
            raise NoDatasourceForFieldException(target_field_name)

        transform_func_name = 'lookup_%s' % (target_field_name)
        if not hasattr(datasource, transform_func_name):
            raise NoSuchLookupMethodException(datasource.__class__.__name__, transform_func_name)

        transform_func = getattr(datasource, transform_func_name)
        return transform_func(target_field_name, source_record, self.value_map)


    def transform(self, source_record, **kwargs):
        target_record = {}
        for key, value in kwargs.iteritems():
            target_record[key] = value

        for target_field_name in self.target_record_fields:
            if self.datasources.get(target_field_name):
                target_record[target_field_name] = self.lookup(target_field_name, source_record)
            elif self.field_map.get(target_field_name):
                source_field_resolver = self.field_map[target_field_name]
                target_record[target_field_name] = source_field_resolver.resolve(source_record)

        #print 'transformer returning record: %s' % target_record
        return target_record



class RecordTransformerBuilder(object):
    def __init__(self, yaml_config_filename, **kwargs):

        self._map_name = kwargs.get('map_name')
        if not self._map_name:
            raise Exception('Missing keyword argument: "map_name"')

        '''
        self._datasource_name = kwargs.get('datasource')
        if not self._datasource_name:
            raise Exception('Missing keyword argument: "datasource_name"')
        '''

        self._transform_config = {}
        with open(yaml_config_filename) as f:
            self._transform_config = yaml.load(f)


    def load_datasource(self, src_name, transform_config):
        src_module = __import__(self._transform_config['globals']['lookup_source_module'])
        datasource_class_name = self._transform_config['sources'][src_name]['class']

        if not hasattr(src_module, datasource_class_name):
            raise NonexistentDatasourceException(datasource_class_name, src_module)

        klass = getattr(src_module, datasource_class_name)
        init_params = self._transform_config['sources'][src_name].get('init_params', {})
        return klass(**init_params)


    def build(self):

        datasource_name = self._transform_config['maps'][self._map_name]['lookup_source']
        datasource = self.load_datasource(datasource_name, self._transform_config)
        transformer = RecordTransformer()

        for fieldname in self._transform_config['maps'][self._map_name]['fields']:
            transformer.add_target_field(fieldname)

            field_config = self._transform_config['maps'][self._map_name]['fields'][fieldname]

            if field_config['source'] == 'record':
                transformer.map_source_to_target_field(field_config['key'], fieldname)
            elif field_config['source'] == 'lookup':
                transformer.register_datasource(fieldname, datasource)
            elif field_config['source'] == 'value':
                transformer.map_const_to_target_field(fieldname, field_config['value'])
            else:
                raise Exception('unrecognized source type "%s." Allowed types are record, lookup, and value.' % field_config['source'])                

        return transformer


    @property
    def config(self):
        return self._transform_config


class DataProcessor(object):
    def __init__(self, processor=None):
        self._processor = processor


    def _process(self, record):
        pass


    def process(self, record):
        if self._processor:
            data = self._processor.process(record)
        else:
            data = record
        return self._process(record)


class ConsoleProcessor(DataProcessor):
    def __init__(self, processor=None):
        DataProcessor.__init__(self, processor)

    def _process(self, record):
        print common.jsonpretty(record)
        return record



class WhitespaceCleanupProcessor(DataProcessor):
    def __init__(self, processor=None):
        DataProcessor.__init__(self, processor)


    def _process(self, record):
        data = {}
        for key, value in record.iteritems():
            data[key] = value.strip()
        return data



class CSVFileDataExtractor(object):
    def __init__(self, processor, **kwargs):
        self._delimiter = kwargs.get('delimiter', ',')
        self._quote_char = kwargs.get('quotechar')
        self._header_fields = kwargs.get('header_fields')
        self._processor = processor



    def extract(self, filename, **kwargs):
        load_func = kwargs.get('load_function')
        max_lines = int(kwargs.get('max_lines', -1))

        with open(filename, 'rb') as datafile:
            csv_reader = csv.DictReader(datafile,
                                        delimiter=self._delimiter,
                                        quotechar=self._quote_char)
            lines_read = 0
            if not max_lines:
                return
            
            for record in csv_reader:
                data = record
                if self._processor:
                    data = self._processor.process(record)
                if load_func:
                    load_func(data)
                lines_read += 1
                if max_lines > 0 and lines_read == max_lines:
                    break


    

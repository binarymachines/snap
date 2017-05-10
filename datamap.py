#!/usr/bin/env python



class NoSuchTargetFieldException(Exception):
    def __init__(self, field_name):
        Exception.__init__(self,
                           'RecordTransformer does not contain the target field %s.' % field_name)


class NoDatasourceForFieldException(Exception):
    def __init__(self, field_name):
        Exception.__init__(self,
                           'No datasource registered for target field name %s.' % field_name)


class NoSuchLookupMethodException(Exception):
    def __init__(self, method_name):
        Exception.__init__(self,
                           'Registered datasource of type %s has no lookup method "%s(...)' % (method_name))



class RecordTransformer:
    def __init__(self):
        self.target_record_fields = set()
        self.datasources = {}
        self.field_map = {}


    def add_target_field(self, target_field_name):
        self.target_record_fields.add(target_field_name)


    def map_source_to_target_field(self, source_field_name, target_field_name):
        if not target_field_name in self.target_record_fields:
            raise NoSuchTargetFieldException(target_field_name)
        self.field_map[source_field_name] = target_field_name


    def register_datasource(self, target_field_name, datasource):
        if not target_field_name in self.target_record_fields:
            raise Exception()
        self.datasources[target_field_name] = datasource


    def lookup(self, target_field_name):
        datasource = self.datasources.get(target_field_name)
        if not datasource:
            raise NoDatasourceForFieldException(target_field_name)

        transform_func_name = 'lookup_%s' % (target_field_name)
        if not hasattr(datasource, transform_func_name):
            raise NoSuchLookupMethodException(transform_func_name)

        transform_func = getattr(datasource, transform_func_name)
        return transform_func(target_field_name)


    def transform(self, source_record, **kwargs):
        target_record = {}
        for key, value in kwargs.iteritems():
            target_record[key] = value

        for target_field_name in self.target_record_fields:
            if self.datasources.get(target_field_name):
                target_record[target_field_name] = self.lookup(target_field_name)
            else:
                source_field_name = self.field_map[target_field_name]
                target_record[target_field_name] = source_record[source_field_name]

        return target_record



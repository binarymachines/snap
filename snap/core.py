#!/user/bin/env python

from snap import common
import argparse
import json
import re



HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_DEFAULT_ERRORCODE = 400
HTTP_NOT_IMPLEMENTED = 500

MIMETYPE_JSON = 'application/json'
CONFIG_FILE_ENV_VAR = 'BUTTONIZE_CFG'

ROUTE_VARIABLE_REGEX = re.compile(r'<([a-zA-Z_-]+):([a-zA-Z_-]+)>')


class MissingDataStatus():
    def __init__(self, field_name):
        self.message = 'The field "%s" is missing or empty.' % field_name

    def __repr__(self):
        return self.message

    
class MissingInputFieldException(Exception):
    def __init__(self, missing_data_status_errors):
        Exception.__init__(self, "One or more errors or omissions detected in input data: %s" % (','.join(missing_data_status_errors)))

        
class UnregisteredTransformException(Exception):
    def __init__(self, transform_name):
        Exception.__init__(self, 'No transform named "%s" has been registered with the object transform service.' % transform_name)

        
class NullTransformInputDataException(Exception):
    def __init__(self, transform_name):
        Exception.__init__(self, 'A null data table was passed in to the object transform service for type "%s". Please check your HTTP request body or query string.' 
                           % transform_name)

'''
class TransformNotImplementedException(Exception):
    def __init__(self, transform_name):
        Exception.__init__(self, 'transform function %s exists but performs no action. Time to add some code.' % transform_name)
'''

class ContentDecodingException(Exception):
    def __init__(self, mime_type):
        Exception.__init__(self, 'No decoding function has been registered for content-type "%s".' % mime_type)


def is_sequence(arg):
    return (not hasattr(arg, "strip") and
            hasattr(arg, "__getitem__") or
            hasattr(arg, "__iter__"))


def convert_multidict(md):
    result = {}
    for key in md.keys():
        if is_sequence(md[key]):
            result[key] = ','.join(md[key])
        else:
            result[key] = md[key]
    return result


class ContentProtocol(object):
    def __init__(self):
        self.decoding_map = {}        


    def update(self, content_type, decode_function):
        self.decoding_map[content_type] = decode_function
        return self
    

    def decode(self, http_request):
        ctype = http_request.headers['Content-Type']
        func = self.decoding_map.get(ctype)
        if not func:
            raise ContentDecodingException(ctype)        
        return func(http_request)


def decode_json(http_request):
    result =  http_request.get_json(silent=True)
    if not result:
        return {}


def decode_text_plain(http_request):
    if http_request.data:
        return json.loads(http_request.data)
    return {}


def decode_form_urlenc(http_request):
    return convert_multidict(http_request.form)


default_content_protocol = ContentProtocol()
default_content_protocol.update('application/json', decode_json)
default_content_protocol.update('text/plain', decode_text_plain)
default_content_protocol.update('application/x-www-form-urlencoded', decode_form_urlenc)
default_content_protocol.update('text/plain; charset=UTF-8', decode_text_plain)


def map_content(http_request):
    return default_content_protocol.decode(http_request)
        

def utf8_encode(raw_input_data):
    input_data = {}
    for key in raw_input_data:
        encoded_key = key
        encoded_value = raw_input_data[key]
        if key.__class__.__name__ == 'unicode':
            encoded_key = key.encode('utf-8')

        if encoded_value.__class__.__name__ == 'unicode':
            encoded_value = encoded_value.encode('utf-8')
        input_data[encoded_key] = encoded_value

    return input_data


def utf8_decode(raw_input_data):
    output_data = {}
    for key in raw_input_data:
        decoded_key = key
        decoded_value = raw_input_data[key]
        
        if key.__class__.__name__ == 'str':
            decoded_key = key.decode()
        
        if decoded_value.__class__.__name__ == 'str':
            decoded_value = decoded_value.decode()
        
        output_data[decoded_key] = decoded_value

    return output_data
        
        
class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, complex):
            return [obj.real, obj.imag]
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

        
class DataField():
    def __init__(self, name, is_required = False):
        self.name = name
        self.is_required = is_required

    def validate(self):
        pass

    def __str__(self):
        return 'DataField <%s>, required = %s' % (self.name, self.is_required)
    
    
class InputShape():
    def __init__(self, name):
        self.name = name
        self.fields = []
       
    def add_field(self, field_name, is_required=False):
        self.fields.append(DataField(field_name, is_required))
        
    # doesn't have to be limited to this. Regex for format validation might be nice
    def scan(self, input_data):
        errors = []
        for f in self.fields:
            value = input_data.get(f.name)
            if not value  and f.is_required:
                errors.append(repr(MissingDataStatus(f.name)))                                
        return errors

    def field_names(self):
        return [f.name for f in self.fields]
    

class Action():
    def __init__(self, input_shape, transform_function, mimetype):
        self.input_shape = input_shape
        self.transform_function = transform_function
        self.output_mimetype = mimetype


    def execute(self, input_data, service_object_registry, **kwargs):
        errors = self.input_shape.scan(input_data)
        if len(errors):
            raise MissingInputFieldException(errors)
        return self.transform_function(input_data, service_object_registry, **kwargs)



class TransformStatus(object):
    def __init__(self, output_data, is_ok=True, **kwargs):
        self.output_data = output_data
        self.ok = is_ok
        self.user_data = kwargs
        self.has_data = True if output_data else False

    def get_userdata(self, tag):
        return self.user_data.get(tag, 'unknown')

    def get_error_code(self):
        return self.user_data.get('error_code')



class Transformer():
    def __init__(self, service_object_tbl):
        self.services = service_object_tbl
        self.actions = {}
        self.error_table = {}


    def register_transform(self, type_name, input_shape, transform_func, mimetype):
        self.actions[type_name] = Action(input_shape, transform_func, mimetype)


    def register_error_code(self, exception_type, code):          
        self.error_table[exception_type.__name__] = code


    def target_mimetype_for_transform(self, type_name):
        action = self.actions.get(type_name)          
        if not action:              
             raise UnregisteredTransformException(type_name)
        return action.output_mimetype
      
          
    def transform(self, type_name, raw_input_data, **kwargs):
        if raw_input_data is None:
            raise NullTransformInputDataException(type_name)

        input_data = {}
        for key in raw_input_data:
            encoded_key = key
            encoded_value = raw_input_data[key]
            if key.__class__.__name__ == 'unicode':
                encoded_key = key.encode('utf-8')

            if encoded_value.__class__.__name__ == 'unicode':
                encoded_value = encoded_value.encode('utf-8')
            input_data[encoded_key] = encoded_value
          
        action = self.actions.get(type_name)          
        if not action:              
            raise UnregisteredTransformException(type_name)

        try:
            return action.execute(input_data, self.services, **kwargs)
        except Exception as err:
            error_type = err.__class__.__name__              
            if self.error_table.get(error_type):
                return TransformStatus(None, 
                                       False, 
                                       error_message=str(err),  
                                       error_code=self.error_table[error_type])
            # if we don't know what code to return for a given downstream exception, 
            # re-raise it and assume that someone will handle it upstream
            raise err







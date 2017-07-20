
import snap, core
import json
#_snap_transforms


def create_user_func(input_data, service_objects):
    #sample response
    result = json.dumps({'message': 'hello', 'content': 'world'})
    return core.TransformStatus(result)
 

def lookup_user_func(input_data, service_objects):
    #raise snap.TransformNotImplementedException('lookup_user_func')
    result = json.dumps({'message': 'hello', 'content': 'world'})
    return core.TransformStatus(result)


def delete_user_func(input_data, service_objects):
    raise core.TransformNotImplementedException('delete_user_func')


#_

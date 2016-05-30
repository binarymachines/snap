#!/usr/bin/env python

#
# Generated Flask routing module for SNAP microservice framework
#



from flask import Flask, request, Response
import snap
import core


app = Flask(__name__)
app = snap.setup(app)
logger = app.logger

# the container for all our data transforms
xformer = core.Transformer(app.config['services']) 


#_snap_transforms


def create_user_func(input_data, service_objects):
    raise snap.TransformNotImplementedException('create_user_func')

def lookup_user_func(input_data, service_objects):
    raise snap.TransformNotImplementedException('lookup_user_func')

def delete_user_func(input_data, service_objects):
    raise snap.TransformNotImplementedException('delete_user_func')


#_


#_snap_exception_handlers

xformer.register_error_code(snap.NullTransformInputDataException, snap.HTTP_BAD_REQUEST)
xformer.register_error_code(snap.MissingInputFieldException, snap.HTTP_BAD_REQUEST)
xformer.register_error_code(snap.TransformNotImplementedException, snap.HTTP_NOT_IMPLEMENTED)

#_



#_snap_data_shapes


create_user_shape = core.InputShape()
create_user_shape.add_field('candidate', False)
create_user_shape.add_field('first_name', False)
create_user_shape.add_field('last_name', False)
create_user_shape.add_field('email', False)

lookup_user_shape = core.InputShape()
lookup_user_shape.add_field('userid', True)
lookup_user_shape.add_field('candidate', True)

default_shape = core.InputShape()
default_shape.add_field('userid', True)
default_shape.add_field('candidate', True)


#_


#_snap_transform_loading
xformer.register_transform('create_user', create_user_shape, create_user_func, 'application/json')
xformer.register_transform('lookup_user', lookup_user_shape, lookup_user_func, 'application/json')
xformer.register_transform('delete_user', default_shape, delete_user_func, 'application/json')

#_



@app.route('/user', methods=['POST'])
def create_user():
    try:
        transform_status = xformer.transform('create_user', request.json)        
        output_mimetype = xformer.target_mimetype_for_transform('create_user')

        if transform_status.ok:
            return Response(transform_status.output_data, status=HTTP_OK, mimetype=output_mimetype)
        return Response(json.dumps(transform_status.user_data), status=transform_status.get_error_code() or HTTP_DEFAULT_ERRORCODE, mimetype=output_mimetype) 
    except Exception, err:
        logger.error("Exception thrown: ", exc_info=1)        
        raise err


@app.route('/user/<id>', methods=['GET'])
def lookup_user():
    try:        
        logger.info('inside lookup_user function...')
        input_data = {}
        input_data.update(request.args)        
        input_data['id'] = id
        
        transform_status = xformer.transform('lookup_user', convert_multidict(input_data))        
        output_mimetype = xformer.target_mimetype_for_transform('lookup_user')

        if transform_status.ok:
            return Response(transform_status.output_data, status=HTTP_OK, mimetype=output_mimetype)
        return Response(json.dumps(transform_status.user_data), status=transform_status.get_error_code() or HTTP_DEFAULT_ERRORCODE, mimetype=output_mimetype) 
    except Exception, err:
        logger.error("Exception thrown: ", exc_info=1)        
        raise err


@app.route('/user/<id>', methods=['DELETE'])
def delete_user():
    try:        
        input_data = {}
        input_data.update(request.args)        
        input_data['id'] = id
        
        transform_status = xformer.transform('delete_user', convert_multidict(input_data))        
        output_mimetype = xformer.target_mimetype_for_transform('delete_user')

        if transform_status.ok:
            return Response(transform_status.output_data, status=HTTP_OK, mimetype=output_mimetype)
        return Response(json.dumps(transform_status.user_data), status=transform_status.get_error_code() or HTTP_DEFAULT_ERRORCODE, mimetype=output_mimetype) 
    except Exception, err:
        logger.error("Exception thrown: ", exc_info=1)        
        raise err


@app.errorhandler(Exception)
def exception_handler(error):    
    return repr(error)


#!/usr/bin/env python

#
# Generated Flask routing module for SNAP microservice framework
#



from flask import Flask, request, Response
from snap import snap
from snap import core
import logging
import json
import argparse
import sys
from snap.loggers import request_logger as log

sys.path.append('/home/dtaylor/workshop/binary/snap/tests')
import test_transforms

f_runtime = Flask(__name__)

if __name__ == '__main__':
    print('starting SNAP microservice in standalone (debug) mode...')
    f_runtime.config['startup_mode'] = 'standalone'
    
else:
    print('starting SNAP microservice in wsgi mode...')
    f_runtime.config['startup_mode'] = 'server'

app = snap.setup(f_runtime)
xformer = core.Transformer(app.config.get('services'))


#-- snap exception handlers ---

xformer.register_error_code(snap.NullTransformInputDataException, snap.HTTP_BAD_REQUEST)
xformer.register_error_code(snap.MissingInputFieldException, snap.HTTP_BAD_REQUEST)
xformer.register_error_code(snap.TransformNotImplementedException, snap.HTTP_NOT_IMPLEMENTED)

#------------------------------



#-- snap data shapes ----------


default = core.InputShape("default")


#------------------------------


#-- snap transform loading ----
xformer.register_transform('home', default, test_transforms.home_func, 'application/json')

#------------------------------



@app.route('/', methods=['GET'])
def home():
    try:
        if app.debug:
            # dump request headers for easier debugging
            log.info('### HTTP request headers:')
            log.info(request.headers)

        input_data = {}                
        input_data.update(request.args)
        
        transform_status = xformer.transform('home',
                                             core.convert_multidict(input_data),
                                             headers=request.headers)        
        output_mimetype = xformer.target_mimetype_for_transform('home')

        if transform_status.ok:
            return Response(transform_status.output_data, status=snap.HTTP_OK, mimetype=output_mimetype)
        return Response(json.dumps(transform_status.user_data), 
                        status=transform_status.get_error_code() or snap.HTTP_DEFAULT_ERRORCODE, 
                        mimetype=output_mimetype) 
    except Exception as err:
        log.error("Exception thrown: ", exc_info=1)        
        raise err





if __name__ == '__main__':
    #
    # If we are loading from command line,
    # run the Flask app explicitly
    #
    app.run(host='0.0.0.0', port=5000)


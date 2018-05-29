#!/usr/bin/env python


INIT_FILE = """
# 
# YAML init file for SNAP microservice framework
#
#


globals:
        bind_host:                   {{ global_settings.data()['bind_host'] }}
        port:                        {{ global_settings.data()['port'] }}
        debug:                       {{ global_settings.data()['debug'] }}
        logfile:                     {{ global_settings.data()['logfile'] }}
        project_directory:           {{ global_settings.data()['project_directory'] }}
        transform_function_module:   {{ global_settings.data()['transform_module'] }}
        service_module:              {{ global_settings.data()['service_module'] }} 
        preprocessor_module:         {{ global_settings.data()['preprocessor_module'] }}


app_name: {{name}}

service_objects:
        {% for so in service_objects %}
        {{ so.name }}:
            class:
                {{ so.classname }}
            init_params:
                {% for p in so.init_params %}
                - name: {{ p['name'] }}
                  value: {{ p['value'] }}
                {% endfor %}
        {% endfor %}


data_shapes:
        {% for shape in data_shapes %}
        {{shape.name}}:
                fields:
                        {% for field in shape.fields %}
                        - name: {{ field.name }}
                          type: {{ field.data_type }}
                          required: {{ field.required }}
                        {% endfor %}
        {% endfor %}

transforms:
        {% for t in transforms %}
        {{ t.name }}:
            route:              {{ t.route }}
            method:             {{ t.method }}
            input_shape:        {{ t.input_shape }}
            output_mimetype:    {{ t.output_mimetype }}
        {% endfor %}

error_handlers:
        - error:                NoSuchObjectException
          tx_status_code:       HTTP_NOT_FOUND 
                
        - error:                DuplicateIDException
          tx_status_code:       HTTP_BAD_REQUEST
"""

ROUTES = """
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

sys.path.append('{{ project_dir }}')

{%- if transform_module %}
import {{ transform_module }} 
{%- endif %}

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

{% for transform in transforms.values() %}
{{ transform.input_shape.name }} = core.InputShape("{{transform.input_shape.name}}")
{%- for field in transform.input_shape.fields %}
{{ transform.input_shape.name }}.add_field('{{ field.name }}', {{ field.is_required }})
{%- endfor %}
{% endfor %}

#------------------------------


#-- snap transform loading ----

{%- for transform in transforms.values() %}
xformer.register_transform('{{transform.name}}', {{ transform.input_shape.name }}, {{ transform.function_name }}, '{{ transform.output_type }}')
{%- endfor %}

#------------------------------


{% for t in transforms.values() %}
@app.route('{{ t.route }}', methods=[{{ t.methods }}])
def {{t.name}}({{ ','.join(t.route_variables) }}):
    try:
        if app.debug:
            # dump request headers for easier debugging
            log.info('### HTTP request headers:')
            log.info(request.headers)

        input_data = {}
        {%- for route_variable in t.route_variables %}
        input_data['{{ route_variable }}'] = {{ route_variable }}
        {%- endfor %}

        {%- if t.methods == "'POST'" %}
        request.get_data()
        input_data.update(core.map_content(request))
        
        transform_status = xformer.transform('{{ t.name }}', input_data, headers=request.headers)
        {%- elif t.methods == "'GET'" or t.methods == "'DELETE'" %}                
        input_data.update(request.args)
        
        transform_status = xformer.transform('{{ t.name }}',
                                             core.convert_multidict(input_data),
                                             headers=request.headers)
        {%- else %}
        {%- endif %}        
        output_mimetype = xformer.target_mimetype_for_transform('{{ t.name }}')

        if transform_status.ok:
            return Response(transform_status.output_data, status=snap.HTTP_OK, mimetype=output_mimetype)
        return Response(json.dumps(transform_status.user_data), 
                        status=transform_status.get_error_code() or snap.HTTP_DEFAULT_ERRORCODE, 
                        mimetype=output_mimetype) 
    except Exception as err:
        log.error("Exception thrown: ", exc_info=1)        
        raise err

{% endfor %}



if __name__ == '__main__':
    #
    # If we are loading from command line,
    # run the Flask app explicitly
    #
    app.run(host='{{bind_host}}', port={{port}})

"""

NGINX_CONFIG = """
#
# Generated nginx config file for snap endpoints via uWSGI
#


user  nobody;
worker_processes  1;

error_log  logs/error.log;
pid        logs/nginx.pid;

events {
    worker_connections  1024;
}


http {
    include       mime.types;
    default_type  application/octet-stream;

    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  logs/access.log  main;
    tcp_nopush     on;
    keepalive_timeout  0;
    sendfile        on;
    client_max_body_size 75M;
    #keepalive_timeout  65;

    server {
        listen       {{ nginx_config.port }};
        server_name  {{ nginx_config.hostname }};

        location / {
            include uwsgi_params;
            uwsgi_pass unix:{{ nginx_config.uwsgi_sockfile }};
        }

        # redirect server error pages to the static page /50x.html
        #
        error_page   500 502 503 504  /50x.html;
        location = /50x.html {
            root   html;
        }
    }

    # HTTPS server
    #
    #server {
    #    listen       443 ssl;
    #    server_name  localhost;

    #    ssl_certificate      cert.pem;
    #    ssl_certificate_key  cert.key;

    #    ssl_session_cache    shared:SSL:1m;
    #    ssl_session_timeout  5m;

    #    ssl_ciphers  HIGH:!aNULL:!MD5;
    #    ssl_prefer_server_ciphers  on;

    #    location / {
    #        root   html;
    #        index  index.html index.htm;
    #    }
    #}

}
"""

TRANSFORM_BLOCK = """
{% for f in transform_functions %}
def {{ f }}(input_data, service_objects, **kwargs):
    raise snap.TransformNotImplementedException('{{f}}')
{% endfor %}
"""


TRANSFORMS = """
#!/usr/bin/env python

 
from snap import snap
from snap import core
import json
from snap.loggers import transform_logger as log


{% for f in transform_functions %}
def {{ f }}(input_data, service_objects, **kwargs):
    raise snap.TransformNotImplementedException('{{f}}')
{% endfor %}

"""

UWSGI = """
#
# Generated uWSGI init file for snap http endpoints
#
#


[uwsgi]
#application's base folder
base = {{ uwsgi_config.base_dir }}

#python module to import
app = main
module = %(app)

# the python home (if using virtualenvs, this should be your venv directory)
home = {{ uwsgi_config.python_home }}
pythonpath = %(base)

#socket file's location
socket = {{ uwsgi_config.socket_dir }}/%n.sock

#permissions for the socket file
chmod-socket    = 666

#the variable that holds a flask application inside the module imported at line #6
callable = app

#location of log files
logto = {{ uwsgi_config.log_dir }}/%n.log
"""


LOGGING_CONFIG = """
version: 1
disable_existing_loggers: False
formatters:
    simple:
        format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

handlers:
    console:
        class: logging.StreamHandler
        level: DEBUG
        formatter: simple
        stream: ext://sys.stdout

    file_handler:
        class: logging.handlers.RotatingFileHandler
        level: INFO
        formatter: simple
        filename: {{ log_filename }}
        maxBytes: 10485760 # 10MB
        backupCount: 20
        encoding: utf8

loggers:
    root:
        level: INFO
        handlers: [console]
        propagate: no

    sqlalchemy:
        level: ERROR
        handlers: [console]
        propagate: no

    request:
        level: INFO
        handlers: [console]
        propagate: no

    init:
        level: INFO
        handlers: [console]
        propagate: no

    service:
        level: INFO
        handlers: [console]
        propagate: no

    transform:
        level: INFO
        handlers: [console]
        propagate: no

root:
    level: INFO
    handlers: [console, file_handler]
"""
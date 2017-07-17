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

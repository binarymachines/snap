#!/usr/bin/env python

#
# Generated Flask routing module for SNAP microservice framework
#

from flask import Flask, request

# The order of these statements is important --
# do not change unless you know what you are doing
#
#
app = Flask(__name__)
import main


main.setup(app)
service_registry = app.config.get('services')
logger = app.logger


@app.route('/', methods=['GET'])
def default():
    return handlers.hello_world(request, service_registry, logger)


@app.route('/s3upload', methods=['GET'])
def route1():
    return handlers.load_s3_excelfile(request, service_registry, logger)



#!/usr/bin/env python


import json
import urllib
from urllib.parse import urlparse, parse_qs
from snap.loggers import request_logger as log


def decode_application_json(http_request):
    log.info('### Invoking application/json request decoder.')
    decoder_output = json.loads(http_request.data.decode())    
    return decoder_output


def decode_text_plain(http_request):
    log.info('### Invoking text/plain request decoder.')
    if not len(http_request.data):
        return {}
    return json.loads(http_request.data.decode())


def decode_text_plain_utf8(http_request):
    log.info('### Invoking text/plain; charset=UTF-8 request decoder.')
    if not len(http_request.data):
        return {}
    return json.loads(http_request.data.decode())


def decode_form_urlencoded(http_request):
    log.info('### invoking application/x-www-form-urlencoded request decoder.')
    raw_data = http_request.data.decode()
    fields = raw_data.split('&')    
    data = {}
    for f in fields:
        tokens = f.split('=')
        key = tokens[0]
        value = urllib.parse.unquote(tokens[1])
        data[key] = value
    return data

#!/usr/bin/env python


def decode_application_json(http_request):
    print('### decoder stub for application/json MIME type')
    return http_request.get_json()
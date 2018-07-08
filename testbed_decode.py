#!/usr/bin/env python


def decode_application_json(http_request):
    print('### decoder stub for application/json MIME type')
    decoder_output = {'test_decoder_called': True}
    decoder_output.update(http_request.get_json())
    return decoder_output

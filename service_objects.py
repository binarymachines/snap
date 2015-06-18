#!/usr/bin/env python




class DBServiceObject():
    def __init__(self, logger, **kwargs):
        logger.info('>>> initializing DBServiceObject with params: %s' % (kwargs))
        

    def stub_function(self):
        return 'this is a stub function from DBServiceObject.'

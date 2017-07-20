#!/usr/bin/env python


import common
import datetime, time
import threading

class Measurement(object):
    def __init__(self, value):
        self.value = value
        self.timestamp = datetime.datetime.now().isoformat()



class Instrument(object):
    def __init__(self):
        pass

    def prepare(self):
        pass

    def cleanup(self):
        pass

    def acquire(self):
        return None

    def read(self):
        self.prepare()
        result = self.acquire()
        self.cleanup()
        return result



class Condition(object):
    def __init__(self, name, function, **kwargs):
        self.name = name
        self.func = function
        self.args = kwargs


    def _eval(self, datapoint, previous_datapoint=None):
        '''Return boolean. Override in subclass.'''
        pass


    def evaluate(self, datapoint, previous_datapoint=None):
        if self._eval(datapoint, previous_datapoint):
            self.func(self.args)


MonitorMode = common.Enum(['ABSOLUTE', 'DELTA'])


class Monitor(threading.Thread):
    def __init__(self, name, instrument, interval_seconds, mode, log):
        threading.Thread.__init__(self)
        self.name = name
        self.instrument = instrument
        self.interval = interval_seconds
        self.mode = mode
        self.log = log
        self.on = False
        self.channels = {}

    
    def set_condition(self, name, condition):
        self.channels[name] = dict(channel_id=name, data=[], condition=condition)


    def run(self):
        if not self.channels:
            raise Exception('No conditions have been assigned to this Monitor.')

        self.on = True
        log.info('Monitor "%s" entering run mode at %s' % (self.name, datetime.datetime.now().isoformat()))
        while self.on:            
            current_datapoint = self.instrument.read()            
            for channel in self.channels:
                previous_datapoint = None
                data_queue = channel['data']
                data_queue.append(self.instrument.read())
                if len(data_queue) > 2:
                    del(data_queue[0])
                    previous_datapoint = data_queue[0]
                if len(data_queue) == 2:
                    previous_datapoint = data_queue[0]
                
                current_datapoint = data_queue[len(data_queue) - 1]
                channel['condition'].evaluate(current_datapoint, previous_datapoint)

            time.sleep(self.interval)

        self.cleanup()
        log.info('Monitor "%s" exiting run mode at %s.' % (self.name, datetime.datetime.now().isoformat()))
        

    def stop(self):
        self.on = False

    


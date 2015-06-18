#!/usr/bin/env python



class UnregisteredServiceObjectException(Exception):
      def __init__(self, alias):
            Exception.__init__(self, 'No ServiceObject registered under the alias "%s".' % alias)




class ServiceObjectRegistry():
      def __init__(self, service_object_dictionary):
        self.services = service_object_dictionary


      def lookup(self, service_object_name):
            sobj = self.services.get(service_object_name)
            if not sobj:
                  raise UnregisteredServiceObjectException(service_object_name)
            return sobj


import os 
import sys
import pyorient
reload(sys)
sys.setdefaultencoding('utf-8')



class OrientDBRecord(object):
    def __init__(self, type_name, record_id=None, **kwargs):
        self.type_name = type_name        
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

        
    def add_attribute(self, name, value):
        setattr(self, name, value)


    def json(self):
        pass # implement in subclasses


    
class VertexRecord(OrientDBRecord):
    def __init__(self, type_name, **kwargs):
        OrientDBRecord.__init__(self, type_name, **kwargs)


    def json(self):        
        return { '@%s' % self.type_name : self.__dict__ }

    
    
class EdgeRecord(OrientDBRecord):
    def __init__(self, type_name, from_vertex_id, to_vertex_id, **kwargs):
        OrientDBRecord.__init__(self, type_name, **kwargs)
        self.to_vertex_id = to_vertex_id
        self.from_vertex_id = from_vertex_id
        

    def json(self):        
        return { '@%s' % self.type_name : self.__dict__ }


    
class OrientDBRecordSet(object):
    def __init__(self, odb_resultset):
        pass

    


class OrientDatabase(object):
    def __init__(self, hostname, port):
        self.host = hostname
        self.port = port
        self.client = pyorient.OrientDB(self.host, 2424)
        self.session_id = None

        
    def connect(self, instance_admin_username, instance_admin_password):
        self.session_id = self.client.connect(instance_admin_username, instance_admin_password)

    
    def open(self, db_name, username, password):
        if not self.session_id:
            raise Exception('Cannot open database %s without first connecting to a server instance. Please call connect() first.' 
                            % db_name)
        self.client.db_open(db_name, username, password)


    def close(self):
        self.client.db_close()


    def open_transaction_context(self):
        return self.client.tx_commit()


    def create_new_record(self, orientdb_record):
        return self.client.record_create(-1, orientdb_record.json())

    
    def execute_query(self, query_string):
        if not self.session_id:
            raise Exception('Cannot execute query without first connecting to a server instance. Please call connect() first.')

        return self.client.command(query_string)
    
    

class OrientDBPersistenceManager(object):
    def __init__(self, orient_database):
        self.database = orient_database
        self.vertex_type_map = {}
        self.edge_type_map = {}

    # NOTE: do not try to create edges this way. The current client creates dangling edges
    # when you add them as first-class records inside a transaction context.
    def save_record_txn(self, odb_record):
        txn = self.database.open_transaction_context()
        txn.begin()
        try:
            rec_position = self.database.create_new_record(odb_record)            
            txn.attach(rec_position)        
            resultset = txn.commit()
            print('### resultset from TXN commit: %s' % str(resultset))
            
            if len(resultset.keys()):
                return resultset.keys()[0]
            return None
        except Exception, err:
            print 'Database error attempting to commit transaction. %s' % err.message
            txn.rollback()
            raise err

        
    def register_vertex_type(self, type_name, field_name_array):
        self.vertex_type_map[type_name] = field_name_array

        

    def register_edge_type(self, type_name, field_name_array):
        self.edge_type_map[type_name] = field_name_array

        
        
    def map_resultset_to_vertices(self, resultset, type_name):
        fields = self.vertex_type_map.get(type_name, [])
        if not len(fields):
            raise Exception('Vertex type "%s" has not been registered with this persistence manager.' % type_name)
        vertices = []
        for result in resultset:            
            data = {} 
            for fieldname in fields:
                data[fieldname] = result.oRecordData.get(fieldname)                
            data['rid'] = result._rid
            vertices.append(VertexRecord(type_name, **data))
            
        return vertices


    def map_resultset_to_edges(self, resultset, type_name):
        fields = self.edge_type_map.get(type_name)
        
        if fields is None:
            raise Exception('Edge type "%s" has not been registered with this persistence manager.' % type_name)
    
        edges = []
        for result in resultset:
            data = {}
            for fieldname in fields:
                data[fieldname] = result.oRecordData.get(fieldname)
            data['rid'] = result._rid
            edges.append(EdgeRecord(type_name, str(result._in), str(result._out), **data))
            
        return edges
                

        
    def save_batch_txn(self, odb_record_array):
        txn = self.database.open_transaction_context()
        txn.begin()
        try:
            for rec in odb_record_array:
                rec_position = self.database.create_new_record(rec)
                txn.attach(rec_position)
            
            return txn.commit()
        except Exception, err:
            txn.rollback()
            raise err

        
    def save_single_edge(self, edge_type_name, source_vertex_id, target_vertex_id):
        query = 'CREATE EDGE %s from %s to %s' % (edge_type_name, source_vertex_id, target_vertex_id)
        return self.database.execute_query(query)
        

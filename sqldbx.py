#!/usr/bin/env python

#------ Database module --------

import sqlalchemy as sqla
import sqlalchemy.orm
from sqlalchemy.orm import mapper, scoped_session, sessionmaker, relation, relationship, clear_mappers
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy_utils import UUIDType
from sqlalchemy.schema import Sequence
import uuid

Base = declarative_base()

import types
import os
import exceptions
import sys


class NoSuchTableError(Exception):
    def __init__(self, tableName, schemaName):
        Exception.__init__(self, "No table named '%s' exists in database schema '%s'." % (tableName, schemaName))


Session = scoped_session(sessionmaker(autoflush=False, autocommit=False, expire_on_commit=False))


class SQLDataTypeBuilder(object):
    def __init__(self, class_name, table_name, schema=None):
        self.name = class_name
        self.fields = []
        self.table_name = table_name
        self.schema = schema


    def add_primary_key_field(self, name, data_type, **kwargs):
        field = {}
        field['name'] = name
        if kwargs.get('sequence'):
            field['column'] = Column(data_type, Sequence(kwargs['sequence']), primary_key=True)
        else:
            field['column'] = Column(data_type, primary_key=True, **kwargs)
        self.fields.append(field)
        return self


    def add_foreign_key_field(self, 
                              name, 
                              data_type, 
                              parent_table_name, 
                              parent_table_pk_name):
        field = {}
        field['name'] = name
        fk_tokens = []
        if self.schema:
            fk_name = '%s.%s.%s' % (self.schema, parent_table_name, parent_table_pk_name)
        else:
            fk_name = '%s.%s' % (parent_table_name, parent_table_pk_name)

        field['column'] = Column(data_type, ForeignKey(fk_name))
        self.fields.append(field)
        return self


    def add_field(self, name, data_type, is_primary_key=False):
        field = {}
        field['name'] = name
        field['column'] = Column(data_type)
        self.fields.append(field)
        return self

    
    def add_relationship(self, relationship_name, related_type_name):
        field = {}
        field['name'] = relationship_name
        field['column'] = relationship(related_type_name)
        self.fields.append(field)
        return self


    def build(self):
        class_attrs = {}
        class_attrs['__tablename__'] = self.table_name
        if self.schema:
            class_attrs['__table_args__'] = {'schema': self.schema}

        for f in self.fields:
            class_attrs[f['name']] = f['column']
        klass = type(self.name, (Base,), class_attrs)
        return klass
        


class Database:
    """A wrapper around the basic SQLAlchemy DB connect logic.

    """

    def __init__(self, dbType, host, schema, port):
        """Create a Database instance ready for user login.

        Arguments:
        dbType -- for now, mysql and postgres only
        host -- host name or IP
        schema -- the database schema housing the desired tables
        """

        self.dbType = dbType
        self.host = host
        self.port = port
        self.schema = schema
        self.engine = None
        self.metadata = None
        
    

    def __createURL__(self, dbType, username, password):
        """Implement in subclasses to provide database-type-specific connection URLs."""
        pass


    def jdbcURL(self):
        """Return the connection URL without user credentials."""
        return 'jdbc:%s://%s:%s/%s' % (self.dbType, self.host, self.port, self.schema)

    
    def login(self, username, password, schema=None):    
        """Connect as the specified user."""

        url = self.__createURL__(self.dbType, username, password)
        self.engine = sqla.create_engine(url, echo=False)
        if schema:
            self.metadata = sqla.MetaData(self.engine, schema=schema)
        else:
            self.metadata = sqla.MetaData(self.engine)
        self.metadata.reflect(bind=self.engine)
        
        #self.sessionFactory.configure(bind=self.engine)
        Session.configure(bind=self.engine)        
        

    def getMetaData(self):
        return self.metadata

    def getEngine(self):
        return self.engine

    def getSession(self):        
        return Session()

    def listTables(self):
        return self.metadata.tables.keys()

    def getTable(self, name):
        """Passthrough call to SQLAlchemy reflection logic. 

        Arguments:
        name -- The name of the table to retrieve. Must exist in the current schema.

        Returns: 
        The requested table as an SQLAlchemy Table object.
        """

        if name not in self.metadata.tables:
            raise NoSuchTableError(name, self.schema)

        return self.metadata.tables[name]



class SQLServerDatabase(Database):
    '''Database type for connecting to Microsoft SQL Server instances
    '''

    def __init__(self, host, schema, port=1433):
        Database.__init__(self, 'mssql', host, schema, port)


    def __createURL__(self, dbtype, username, password):
        return '%s+pymssql://%s:%s@%s:%s/%s' % (self.dbType, username, password, self.host, self.port, self.schema)



class MySQLDatabase(Database):
    """A Database type for connecting to MySQL instances."""

    def __init__(self, host, schema, port=3306):        
        Database.__init__(self, "mysql", host, schema, port)
        
        
    def __createURL__(self, dbType, username, password):
        return "%s://%s:%s@%s:%d/%s" % (self.dbType, username, password, self.host, self.port, self.schema)


    
class PostgreSQLDatabase(Database):
    """A Database type for connecting to PostgreSQL instances."""

    def __init__(self, host, schema, port=5432):
        Database.__init__(self, "postgresql+psycopg2", host, schema, port)
        
        
    def __createURL__(self, dbType, username, password):
        return "%s://%s:%s@%s:%d/%s" % (self.dbType, username, password, self.host, self.port, self.schema)

        

class NoSuchPluginError(Exception):
    def __init__(self, pluginName):
        Exception.__init__(self, "No plugin registered under the name '%s'." % pluginName)


class PluginMethodError(Exception):
    def __init__(self, pluginName, pluginMethodName):
        Exception.__init__(self, "The plugin registered as '%s' does not contain an execute() method." % (pluginName))


class PersistenceManager:
    """A logic center for database operations in a Serpentine app. 

    Wraps SQLAlchemy lookup, insert/update, general querying, and O/R mapping facilities."""
    
    def __init__(self, database):
        self._typeMap = {}
        self.modelAliasMap = {}
        self.database = database
        self.metaData = self.database.getMetaData()
        self.pluginTable = {}
        self.mappers = {}


    def __del__(self):
        clear_mappers()

    def getSession(self):
        return self.database.getSession()

    def refreshMetaData(self):
        self.metaData = self.database.getMetaData()


    def loadTable(self, tableName):
        """Retrieve table data using SQLAlchemy reflection"""

        return sqlalchemy.schema.Table(tableName, self.metaData, autoload = True)

    
    def str_to_class(self, objectTypeName):
        """A rudimentary class loader function.

        Arguments: 
        objectTypeName -- a fully qualified name for the class to be loaded,
        in the form 'packagename.classname'. 

        Returns:
        a Python Class object.
        """

        if objectTypeName.count('.') == 0:
            moduleName = __name__
            typeName = objectTypeName
        else:
            tokens = objectTypeName.rsplit('.', 1)
            moduleName = tokens[0]
            typeName = tokens[1]

        try:
            identifier = getattr(sys.modules[moduleName], typeName)
        except AttributeError:
            raise NameError("Class %s doesn't exist." % objectTypeName)
        if isinstance(identifier, (types.ClassType, types.TypeType)):
            return identifier
        raise TypeError("%s is not a class." % objectTypeName)

    def query(self, objectType, session):
        """A convenience function to create an SQLAlchemy Query object on the passed DB session.

        Arguments:
        objectType -- a Python class object, most likely returned from a call to str_to_class(...)

        Returns:
        An SQLAlchemy Query object, ready for data retrieval or further filtering. See SQLAlchemy docs
        for more information on Query objects.
        """

        return session.query(objectType)


    def mapTypeToTable(self, modelClassName, tableName, **kwargs):
        """Call-through to SQLAlchemy O/R mapping routine. Creates an SQLAlchemy mapper instance.

        Arguments:
        modelClassName -- a fully-qualified class name (packagename.classname)
        tableName -- the name of the database table to be mapped to this class
        
        """

        dbTable = Table(tableName, self.metaData, autoload=True)        
        objectType = self.str_to_class(modelClassName)     
        if objectType not in self.mappers:
            self.mappers[objectType] = mapper(objectType, dbTable)

        if 'model_alias' in kwargs:
            modelAlias = kwargs['model_alias']
        else:
            modelAlias = modelClassName

        self.modelAliasMap[modelAlias] = modelClassName
        self._typeMap[modelClassName] = dbTable
        
    
    def mapParentToChild(self, parentTypeName, parentTableName, parentTypeRefName, childTypeName, childTableName, childTypeRefName, **kwargs):
        """Create a parent-child (one to many relationship between two DB-mapped entities in SQLAlchemy's O/R mapping layer.

        Arguments:

        Returns:
        """
    
        parentTable = Table(parentTableName, self.metaData, autoload=True)
        parentObjectType = self.str_to_class(parentTypeName)

        childTable = Table(childTableName, self.metaData, autoload=True)
        childObjectType = self.str_to_class(childTypeName)

        if childObjectType not in self.mappers:
            self.mappers[childObjectType] = mapper(childObjectType, childTable)

        self.mappers[parentObjectType] = mapper(parentObjectType, parentTable, properties={
                childTypeRefName : relation(childObjectType, backref = parentTypeRefName)})

        parentAlias = kwargs['parent_model_alias']
        childAlias = kwargs['child_model_alias']

        self.mapTypeToTable(parentTypeName, parentTable.name, model_alias = parentAlias)
        self.mapTypeToTable(childTypeName, childTable.name, model_alias = childAlias)
        

        
    def mapPeerToPeer(self, parentTypeName, parentTableName, parentTypeRefName, peerTypeName, peerTableName, peerTypeRefName, **kwargs):
        """Create a peer-peer (one to one) relationship between two DB-mapped entities in SQLAlchemy's O/R mapping layer.

        Arguments:

        Returns:
        """

        parentTable = Table(parentTableName, self.metaData, autoload=True)
        parentObjectType = self.str_to_class(parentTypeName)

        peerTable = Table(peerTableName, self.metaData, autoload=True)
        peerObjectType = self.str_to_class(peerTypeName)

        if peerObjectType not in self.mappers:
            self.mappers[peerObjectType] = mapper(peerObjectType, peerTable, non_primary=True)

        self.mappers[parentObjectType] = mapper(parentObjectType, parentTable, properties={
                peerTypeRefName : relation(peerObjectType, backref = parentTypeRefName, uselist = False), })

        parentAlias = kwargs['model_alias']
        peerAlias = kwargs['peer_model_alias']

        self.mapTypeToTable(parentTypeName, parentTable.name, model_alias = parentAlias)
        self.mapTypeToTable(peerTypeName, peerTable.name, model_alias = peerAlias)
       


    def getTableForType(self, modelName):
        if modelName not in self.modelAliasMap:
            raise NoTypeMappingError(modelName)
        
        return self._typeMap[self.modelAliasMap[modelName]]

    def retrieveAll(self, objectTypeName, session):
        objClass = self.str_to_class(objectTypeName)
        resultSet = session.query(objClass).all()
        return resultSet
    
    def insert(self, object, session):
        session.add(object)

    def update(self, object, session):
        session.flush()
        
    def delete(self, object, session):
        session.delete(object)

    def loadByKey(self, objectTypeName, objectID, session):
        query = session.query(self.str_to_class(objectTypeName)).filter_by(id = objectID)
        return query.first()

    def registerPlugin(self, plugin, name):
        self.pluginTable[name] = plugin

    def callPlugin(self, pluginName, targetObject):
        plugin = self.pluginTable[pluginName]
        if plugin == None:
            raise NoSuchPluginError(pluginName)
    
        try:
            return plugin.performOperation(self, targetObject)
        except AttributeError as err:
            raise PluginMethodError(pluginName, 'execute')

    
class PersistenceManagerPlugin:
    def __init__(self):
        pass
        
    def performOperation(self, persistenceMgr, object):
        method = getattr(self, 'execute')
        
        return method(persistenceMgr, object)

    def __execute__(persistenceMgr, object):  # override in subclasses
        pass





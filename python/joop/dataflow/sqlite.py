""" DataCatcher implementation for local SQLite DBs.
    SQLite looms large in the DataFlow module (even if the
    implemenations here are mostly wrappers for the parent classes)
    as it is primarly a local db. Accordingly, it is the go-to for
    the local cache of a DataCatcher, whether as a local-first dataflow
    or a caching dataflow that caches on failure to send to the primary.
    It's also very easy to test DataCatcher functionality integration
    using SQLite in this way.
"""
from joop.sql.sqlite import SQLiteDB
from joop.dataflow.catchers import CachingSQLDataCatcher, BasicSQLDataCatcher

class BasicSQLiteDataCatcher(BasicSQLDataCatcher):
    """Data stops here; there is no further caching."""
    caching: bool = False
    round_trip: bool = False
    sql_config : SQLiteDB

class SQLiteCacheDataCatcher(CachingSQLDataCatcher):
    """A local SQLite DB to cache data to before it goes elsewhere."""
    caching: bool = True
    round_trip: bool = False
    sql_config : SQLiteDB
    

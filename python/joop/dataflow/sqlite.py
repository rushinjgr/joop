""" DataCatcher implementation for local SQLite DBs.
    SQLite looms large in the DataFlow module (even if the
    implemenations here are mostly wrappers for the parent classes)
    as it is primarly a local db. Accordingly, it is the go-to for
    local storage in a DataCatcher, whether as a local-first dataflow
    or a queueing dataflow that queues on failure to send to the primary.
    It's also very easy to test DataCatcher functionality integration
    using SQLite in this way.
"""
from joop.sql.sqlite import SQLiteDB
from joop.dataflow.catchers import BasicSQLDataCatcher, CachingSQLDataCatcher, QueueingSQLDataCatcher

class BasicSQLiteDataCatcher(BasicSQLDataCatcher):
    """Data stops here; there is no further queueing."""
    queueing: bool = False
    round_trip: bool = False
    sql_config : SQLiteDB


class CachingSQLiteDataCatcher(CachingSQLDataCatcher):
    """A local SQLite DB that stores the latest inbound row by primary key."""
    queueing: bool = False
    round_trip: bool = False
    sql_config : SQLiteDB


class SQLiteQueueDataCatcher(QueueingSQLDataCatcher):
    """A local SQLite DB to queue data before it goes elsewhere."""
    queueing: bool = True
    round_trip: bool = False
    sql_config : SQLiteDB
    

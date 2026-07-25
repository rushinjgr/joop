""" An example to drive development by showing 
    what calling code should look like and
    creating a simple test we can run as we go
    and easily inspect the result.
    In its final form, it will serve as documentation.
"""

from joop.sql.sqlite import SQLiteDB
from joop.dataflow.sqlite import SQLiteQueueDataCatcher, BasicSQLiteDataCatcher
from joop.dataflow.model import OutboundUUIDModel
from joop.dataflow.link import DataLink

##########################
# Define DB configs
sqlite_config = SQLiteDB.from_path("example.db")
other_sqlite_config = SQLiteDB.from_path("other_example.db")

##########################

##########################
# Create a DataCatcher to control each DB:
class MyDataCatcher(SQLiteQueueDataCatcher):
    sql_config = sqlite_config

class MyOtherDataCatcher(BasicSQLiteDataCatcher):
    sql_config = other_sqlite_config
##########################


##########################
# Define your first model, using one of the available types.
class _MyUUIDModel(OutboundUUIDModel, table=False):
    message: str = "Hello, world!"
##########################

##########################
# Create a DataLink from two DataCatchers and your model.
# Depending on the rest of your implementation, this
#   can provide buffering of data locally when the remote
#   datastore is unavailable, or other features.
class MyDataLink(DataLink):
    datamodel = _MyUUIDModel
    local_type = MyDataCatcher
    remote_type = MyOtherDataCatcher

# `create_missing` tables are to be created if they don't
# already exist in SQL DataCatchers, etc. 

my_data_link = MyDataLink(create_missing=True)

##########################

# Now you're ready to send data.

datapoint = _MyUUIDModel()

my_data_link.publish(datapoint)
##########################

# You can use one DB with multiple datacatchers to go to different remotes.
# Even with the same model.
# Just don't name them the same.

class AnotherDataCatcher(SQLiteQueueDataCatcher):
    sql_config = sqlite_config

another_sqlite_config = SQLiteDB.from_path("another_example.db")

class YetAnotherDataCatcher(BasicSQLiteDataCatcher):
    sql_config = another_sqlite_config

class MyOtherDataLink(DataLink):
    datamodel = _MyUUIDModel
    local_type = AnotherDataCatcher
    remote_type = YetAnotherDataCatcher

datapoint = _MyUUIDModel()

my_other_data_link = MyOtherDataLink(create_missing=True)

my_data_link.publish(datapoint)
my_other_data_link.publish(datapoint)

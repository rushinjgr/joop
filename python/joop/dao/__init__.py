"""Data Access Object (DAO) module for joop.

This module provides abstract classes for creating Data Access Objects (DAOs) to manage
Pydantic and SQLModel-based models. DAOs provide a layer of abstraction between the
representation of the object (especially at the storage layer) and the business logic
code that uses or manipulates the object.

Classes:
    DAO:
        An abstract wrapper for a Pydantic model or any class derived from it.

    SQLDAO:
        An abstract class for SQL models, extending the DAO class.

"""

from typing import List, Type, Optional
from dataclasses import dataclass
import pydantic
import sqlmodel

class DAO():
    """
    An abstract wrapper for a Pydantic model or any class derived from it.

    The DAO class provides methods to interact with the underlying model, including
    converting it to a dictionary and retrieving its fields. It is typically constructed
    around an existing model using the `from_model` method.

    Attributes:
        _modeltype (Type): The type of the model, defaulting to `pydantic.BaseModel`.

    Properties:
        model (pydantic.BaseModel): The underlying Pydantic model instance.

    Methods:
        from_model(model: pydantic.BaseModel) -> 'DAO':
            Creates a DAO instance from a given Pydantic model.

        to_dict() -> dict:
            Converts the underlying model to a dictionary using aliases for field names.

        get_model_fields() -> List[str]:
            Retrieves the names of all fields defined in the `_modeltype`.
    """

    _modeltype : Type = pydantic.BaseModel

    @property
    def model(self) -> pydantic.BaseModel:
        return self._model
    
    @model.setter
    def model(self, value : pydantic.BaseModel):
        self._model = value

    @classmethod
    def from_model(cls, model : pydantic.BaseModel) -> 'DAO':
        if model is None:
            return None
        
        if isinstance(type(model), cls._modeltype):
            raise ("Invalid Model Supplied")
        
        res = cls()
        res._model = model
        return res
    
    def to_dict(self) -> dict:
        """
        Convert the underlying model to a dictionary, using aliases for field names.

        Returns:
            dict: A dictionary representation of the model with aliases as keys.

        Raises:
            ValueError: If no model is set for this DAO instance.
            TypeError: If the model does not have Pydantic fields.
        """
        if not hasattr(self, '_model') or self._model is None:
            raise ValueError("No model is set for this DAO instance.")
        
        # Ensure the model has the necessary fields and aliases
        if not hasattr(self._model, '__fields__'):
            raise TypeError("The model does not have Pydantic fields.")
        
        # Use SQLModel's/Pydantic basemodel's dict() method to get the base dictionary
        base_dict = self._model.dict()
        
        # Build the dictionary using aliases
        result = {}
        for field_name, field in self._model.__fields__.items():
            alias = field.alias or field_name  # Use alias if defined, otherwise fallback to field name
            result[alias] = base_dict[field_name]
        
        return result
    
    @classmethod
    def get_model_fields(cls) -> List[str]:
        """
        Get the names of all fields defined in the `_modeltype`.

        Returns:
            List[str]: A list of field names.

        Raises:
            TypeError: If `_modeltype` is not a subclass of `pydantic.BaseModel`.
        """
        if not issubclass(cls._modeltype, pydantic.BaseModel):
            raise TypeError("_modeltype must be a subclass of pydantic.BaseModel")

        res = [field.alias if field.alias else name for name, field in cls._modeltype.__fields__.items()]
        return res

class SQLDAO(DAO):
    """
    An abstract class for SQL models, extending the DAO class.

    The SQLDAO class provides additional methods for interacting with SQLModel-based
    models, such as retrieving all records from the database.

    Attributes:
        _modeltype (Type): The type of the model, defaulting to `sqlmodel.SQLModel`.

    Methods:
        get_all(session: sqlmodel.Session) -> List['SQLDAO']:
            Retrieves all records from the database for the given model type and returns
            them as a list of SQLDAO instances.
    """

    _modeltype : Type = sqlmodel.SQLModel

    @classmethod
    def get_all(cls, session: sqlmodel.Session) -> List['SQLDAO']:
        """
        Retrieve all records from the database for the given model type and return them as a list of SQLDAO instances.

        Args:
            session (sqlmodel.Session): The database session to use for the query.

        Returns:
            List[SQLDAO]: A list of SQLDAO instances for the model type.

        Raises:
            TypeError: If `_modeltype` is not a subclass of `sqlmodel.SQLModel`.
        """
        if not issubclass(cls._modeltype, sqlmodel.SQLModel):
            raise TypeError("_modeltype must be a subclass of sqlmodel.SQLModel")

        db_results = session.query(cls._modeltype).all()
        return [cls.from_model(result) for result in db_results]

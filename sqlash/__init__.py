# -*- coding:utf-8 -*-
import logging
logger = logging.getLogger(__name__)
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.base import ONETOMANY, MANYTOONE, MANYTOMANY
import sqlalchemy.types as t
from sqlalchemy.orm.mapper import configure_mappers
from .langhelpers import model_of
from collections import namedtuple
from functools import partial

p = Pair = namedtuple("Pair", "left, right")


class S(object):
    atom = "atom"
    array = "array"
    object = "object"


class Control(object):
    def __init__(self):
        self.mappers = {}  # class -> mapper

    def get_property_from_object(self, ob, k):
        return self.get_mapper_from_object(ob)._props[k]

    def get_relationship_from_object(self, ob, k):
        mapper = self.get_mapper_from_object(ob)
        if mapper.__class__._new_mappers:
            configure_mappers()
        return mapper._props[k]

    def get_mapper_from_object(self, ob):
        model = model_of(ob)
        try:
            return self.mappers[model]
        except KeyError:
            v = self.mappers[model] = inspect(model).mapper
            return v

    def get_type_from_property(self, prop):
        return prop.columns[0].type.__class__

    def get_shape_from_property(self, prop):
        direction = prop.direction
        if direction == ONETOMANY:
            return S.array
        elif direction == MANYTOONE:
            return S.object
        elif direction == MANYTOMANY:
            return S.array


class Abbreviation(object):
    def __init__(self, control):
        self.control = control

    def __call__(self, ob, name):
        if "*" == name:
            mapper = self.control.get_mapper_from_object(ob)
            for prop in mapper.column_attrs:
                if not any(c.foreign_keys for c in getattr(prop, "columns", Empty)):
                    yield prop.key
        else:
            yield name
Empty = ()


class Serializer(object):
    def __init__(self, convertions, control, factory, renaming_options, abbreviation):
        self.convertions = convertions
        self.control = control
        self.factory = factory

        self.abbreviation = abbreviation
        self.renaming_options = renaming_options

    def serialize(self, ob, q_collection, renaming_options=None):
        renaming_options = renaming_options or {}
        r = self.factory()
        for q in q_collection:
            for q in self.abbreviation(ob, q):
                self.build(r, *self.parse(ob, q))
        return r

    def parse(self, ob, q):
        if isinstance(q, Pair):
            k = q.left
            prop = self.control.get_property_from_object(ob, k)
            shape = self.control.get_shape_from_property(prop)
            if shape == S.array:
                sub_r = [self.serialize(sub, q.right) for sub in getattr(ob, k)]
                return (shape, k, prop, sub_r)
            elif shape == S.object:
                sub_r = self.serialize(getattr(ob, k), q.right)
                return (shape, k, prop, sub_r)
            else:
                raise NotImplemented(shape)
        else:
            return (S.atom, q, self.control.get_property_from_object(ob, q), getattr(ob, q))

    def add_result(self, r, k, v):
        r[self.renaming_options.get(k, k)] = v

    def build(self, r, shape, q, prop, val):
        if shape == S.atom:
            type_ = self.control.get_type_from_property(prop)
            convert = self.convertions.get(type_)
            if convert:
                self.add_result(r, q, convert(val, r))
            else:
                self.add_result(r, q, val)
        elif shape == S.array:
            self.add_result(r, q, val)
        elif shape == S.object:
            self.add_result(r, q, val)
        else:
            raise NotImplemented(shape)


default_column_to_schema = {
    t.String: "string",
    t.Text: "string",
    t.Integer: "integer",
    t.SmallInteger: "integer",
    t.BigInteger: "string",  # xxx
    t.Numeric: "integer",
    t.Float: "number",
    t.DateTime: "string",
    t.Date: "string",
    t.Time: "string",  # xxx
    t.LargeBinary: "xxx",
    t.Binary: "xxx",
    t.Boolean: "boolean",
    t.Unicode: "string",
    t.Concatenable: "xxx",
    t.UnicodeText: "string",
    t.Interval: "xxx",
    t.Enum: "string",
}


class JSONSchemaSerializer(Serializer):
    def serialize(self, ob, q_collection, renaming_options=None):
        renaming_options = renaming_options or {}
        r = self.factory()
        model = model_of(ob)
        r["title"] = model.__name__
        r["properties"] = properties = {}
        doc = getattr(ob, "__doc__")
        if doc:
            r["description"] = doc

        self.definitions = {}  # xxx

        for q in q_collection:
            for q in self.abbreviation(model, q):
                self.build(properties, *self.parse(model, q))

        if self.definitions:
            r["definitions"] = self.definitions

        # collect required
        r["required"] = required_list = []
        for k, v in properties.items():
            required = v.pop("required", None)
            if required:
                required_list.append(k)
        return r

    def detect_required(self, prop):
        columns = getattr(prop, "columns", Empty)
        return any(not c.nullable and c.default is None for c in columns)

    def add_result(self, r, k, prop, v):
        data = {}
        if v is None:
            column = prop.columns[0]
            columntype = column.type
            data["type"] = default_column_to_schema[columntype.__class__]
            if hasattr(columntype, "length"):
                data["maxLength"] = columntype.length
            if hasattr(columntype, "enums"):
                data["enum"] = list(columntype.enums)

            if isinstance(columntype, t.DateTime):
                data["format"] = "date-time"
            elif isinstance(columntype, t.Date):
                data["format"] = "date"
            elif isinstance(columntype, t.Time):
                data["format"] = "time"
            data["required"] = self.detect_required(prop)
        r[self.renaming_options.get(k, k)] = data

    def parse(self, ob, q):
        if isinstance(q, Pair):
            k = q.left
            relationship = self.control.get_relationship_from_object(ob, k)
            shape = self.control.get_shape_from_property(relationship)
            sub = relationship.mapper.class_
            sub_r = self.serialize(sub, q.right)
            return (shape, k, relationship, sub_r)
        else:
            return (S.atom, q, self.control.get_property_from_object(ob, q), None)

    def build(self, r, shape, q, prop, val):
        if shape == S.atom:
            type_ = self.control.get_type_from_property(prop)
            convert = self.convertions.get(type_)
            if convert:
                self.add_result(r, q, prop, convert(val, r))
            else:
                self.add_result(r, q, prop, val)
        elif shape == S.array:
            r[self.renaming_options.get(q, q)] = {"type": "array", "items": {"$ref": "#/definitions/{}".format(val["title"])}}
            val.pop("definitions", None)
            self.definitions[val["title"]] = val
        elif shape == S.object:
            r[self.renaming_options.get(q, q)] = {"type": "object", "$ref": "#/definitions/{}".format(val["title"])}
            val.pop("definitions", None)
            self.definitions[val["title"]] = val
        else:
            raise NotImplemented(shape)


class SerializerFactory(object):
    def __init__(self, convertions=None, control=Control(), factory=dict, Serializer=Serializer):
        self.convertions = convertions or {}
        self.control = control
        self.factory = factory
        self.Serializer = Serializer

    def __call__(self, renaming_options=None, abbreviation=Abbreviation):
        return self.Serializer(
            self.convertions,
            self.control,
            self.factory,
            renaming_options=renaming_options or {},
            abbreviation=abbreviation(self.control)
        )
JSONSchemaSerializerFactory = partial(SerializerFactory, Serializer=JSONSchemaSerializer)

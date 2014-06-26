# -*- coding:utf-8 -*-
import logging
logger = logging.getLogger(__name__)
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.base import ONETOMANY, MANYTOONE, MANYTOMANY
from .langhelpers import model_of
from collections import namedtuple

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


class SerializerFactory(object):
    def __init__(self, convertions=None, control=Control(), factory=dict):
        self.convertions = convertions or {}
        self.control = control
        self.factory = factory

    def __call__(self, renaming_options=None, abbreviation=Abbreviation):
        return Serializer(
            self.convertions,
            self.control,
            self.factory,
            renaming_options=renaming_options or {},
            abbreviation=abbreviation(self.control)
        )


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

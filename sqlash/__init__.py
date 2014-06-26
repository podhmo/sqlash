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

    def __call__(self, renaming=None, merging=None, abbreviation=Abbreviation):
        return Serializer(
            self.convertions,
            self.control,
            self.factory,
            renaming_options=renaming or {},
            merging_options=merging or {},
            abbreviation=abbreviation(self.control)
        )


class Serializer(object):
    def __init__(self, convertions, control, factory, renaming_options, merging_options, abbreviation):
        self.convertions = convertions
        self.control = control
        self.factory = factory

        self.abbreviation = abbreviation
        self.merging_options = merging_options
        self.merging_keys = {k: 1 for ks in merging_options for k in ks}
        self.renaming_options = renaming_options

        self._mstack = []

    def serialize(self, ob, q_collection, remove_on_merge=False):
        env = {"merging": set(), "used": {}}
        self._mstack.append(env)
        r = self.factory()

        for q in q_collection:
            for q in self.abbreviation(ob, q):
                self.consume(ob, q, r, env, remove_on_merge=remove_on_merge)

        merging_r = {}

        for q in env["merging"]:
            self.build(merging_r, *self.parse(ob, q))

        for ks, fn in self.merging_options.items():
            args = [merging_r.get(k) for k in ks]
            args.append(r)
            name, val = fn(*args)
            r[name] = val

        self._mstack.pop()
        return r

    def consume(self, ob, q, r, env, remove_on_merge=False):
        if isinstance(q, Pair):
            k = q.left
        else:
            k = q

        if k in env["used"]:
            return

        if k in self.merging_keys:
            env["used"][k] = 1
            env["merging"].add(q)
            if remove_on_merge:
                return

        env["used"][k] = 1
        self.build(r, *self.parse(ob, q))

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

# -*- coding:utf-8 -*-
from functools import partial
from sqlash.tests.models import (
    Group, User, A0, A1, A2, Team, Member
)


def _getTarget():
    from sqlash import SerializerFactory
    from sqlash import JSONSchemaSerializer
    return partial(SerializerFactory, Serializer=JSONSchemaSerializer)


def _makeOne(*args, **kwargs):
    return _getTarget()(*args, **kwargs)


def test_simple():
    target = _makeOne({})()
    result = target.serialize(Group, ["name"])
    assert result == {'title': 'Group', 'required': ['name'], 'properties': {'name': {'type': 'string', 'maxLength': 255}}}


def test_foreignkey():
    target = _makeOne({})()
    result = target.serialize(User, ["group_id"])
    assert result == {'title': 'User', 'required': [], 'properties': {'group_id': {'type': 'integer'}}}


def test_abbreviation():
    target = _makeOne()()
    result = target.serialize(User, ["*"])
    required = result.pop("required")
    assert result == {'properties': {'id': {'type': 'integer'},
                                     'name': {'type': 'string', 'maxLength': 255},
                                     'created_at': {'type': 'string', "format": "date-time"}},
                      'title': 'User'}
    assert sorted(required) == ["id", "name"]


def test_renaming():
    target = _makeOne()({"name": "Name", "created_at": "CreatedAt", "id": "Id"})
    result = target.serialize(User, ["*"])
    required = result.pop("required")
    assert result == {'properties': {'Id': {'type': 'integer'},
                                     'Name': {'type': 'string', 'maxLength': 255},
                                     'CreatedAt': {'type': 'string', "format": "date-time"}},
                      'title': 'User'}
    assert sorted(required) == ["Id", "Name"]


def test_relation_onetomany():
    from sqlash import Pair

    target = _makeOne()()
    result = target.serialize(Group, ["name", Pair("users", ["name"])])
    assert result == {'definitions': {'User': {'title': 'User', 'properties': {'name': {'type': 'string', 'maxLength': 255}}, 'required': ['name']}}, 'title': 'Group', 'properties': {'users': {'type': 'array', 'items': {'$ref': '#/definitions/User'}}, 'name': {'type': 'string', 'maxLength': 255}}, 'required': ['name']}


def test_relation_manytoone():
    from sqlash import Pair

    target = _makeOne()()
    result = target.serialize(User, ["name", Pair("group", ["name"])])
    assert result == {'required': ['name'], 'definitions': {'Group': {'required': ['name'], 'title': 'Group', 'properties': {'name': {'type': 'string', 'maxLength': 255}}}}, 'title': 'User', 'properties': {'group': {'type': 'object', '$ref': '#/definitions/Group'}, 'name': {'type': 'string', 'maxLength': 255}}}


def test_many_to_many():
    from sqlash import Pair

    target = _makeOne({})()

    result = target.serialize(Team, ["name", "created_at", Pair("members", ["name", "created_at"])])
    assert result == {'required': ['name'], 'definitions': {'Member': {'required': ['name'], 'title': 'Member', 'properties': {'created_at': {'format': 'date-time', 'type': 'string'}, 'name': {'maxLength': 255, 'type': 'string'}}}}, 'title': 'Team', 'properties': {'created_at': {'format': 'date-time', 'type': 'string'}, 'members': {'items': {'$ref': '#/definitions/Member'}, 'type': 'array'}, 'name': {'maxLength': 255, 'type': 'string'}}}


def test_many_to_many2():
    from sqlash import Pair

    target = _makeOne({})()

    result = target.serialize(Member, ["name", "created_at", Pair("teams", ["name", "created_at"])])
    assert result == {'definitions': {'Team': {'required': ['name'], 'title': 'Team', 'properties': {'created_at': {'type': 'string', 'format': 'date-time'}, 'name': {'type': 'string', 'maxLength': 255}}}}, 'title': 'Member', 'required': ['name'], 'properties': {'teams': {'type': 'array', 'items': {'$ref': '#/definitions/Team'}}, 'created_at': {'type': 'string', 'format': 'date-time'}, 'name': {'type': 'string', 'maxLength': 255}}}


def test_deep_nested():
    from sqlash import Pair

    target = _makeOne()()
    result = target.serialize(A2, ["*", Pair("a1", ["*", Pair("a0", ["*"])])])
    expected = {'required': ['id', 'created_at'],
                'definitions': {'A1': {'required': ['id', 'created_at'],
                                       'title': 'A1',
                                       'properties': {'id': {'type': 'integer'},
                                                      'created_at': {'format': 'date-time', 'type': 'string'},
                                                      'a0': {'$ref': '#/definitions/A0', 'type': 'object'}}},
                                'A0': {'required': ['id', 'created_at'],
                                       'title': 'A0',
                                       'properties': {'id': {'type': 'integer'},
                                                      'created_at': {'format': 'date-time', 'type': 'string'}}}},
                'title': 'A2',
                'properties': {'id': {'type': 'integer'},
                               'created_at': {'format': 'date-time', 'type': 'string'},
                               'a1': {'$ref': '#/definitions/A1', 'type': 'object'}}}
    assert result == expected

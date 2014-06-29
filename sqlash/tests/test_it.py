# -*- coding:utf-8 -*-
from sqlash.tests.models import (
    Group, User, A0, A1, A2, Team, Member
)


def _getTarget():
    from sqlash import SerializerFactory
    return SerializerFactory


def _makeOne(*args, **kwargs):
    return _getTarget()(*args, **kwargs)


def datetime_for_human(dt, r):
    return dt.strftime("%Y/%m/%d %H:%M:%S")


def int_for_human(v, r):
    return "this is {}".format(v)


def test_simple():
    target = _makeOne({})()
    group = Group(name="foo")
    result = target.serialize(group, ["name"])
    assert result == {"name": "foo"}


def test_convert():
    from datetime import datetime
    from sqlalchemy import types as t

    target = _makeOne({t.DateTime: datetime_for_human})()
    group = Group(name="foo", created_at=datetime(2000, 1, 1))
    result = target.serialize(group, ["created_at"])
    assert result == {'created_at': '2000/01/01 00:00:00'}


def test_foreignkey():
    from sqlalchemy import types as t

    user = User(group_id=1)
    target = _makeOne({t.Integer: int_for_human})()
    result = target.serialize(user, ["group_id"])
    assert result == {'group_id': 'this is 1'}


def test_abbreviation():
    from datetime import datetime
    from sqlalchemy import types as t

    user = User(group_id=1, name="foo", created_at=datetime(2000, 1, 1))
    target = _makeOne({t.Integer: int_for_human, t.DateTime: datetime_for_human})()
    result = target.serialize(user, ["*"])
    assert result == {'name': 'foo', 'created_at': '2000/01/01 00:00:00', 'id': 'this is None'}


def test_renaming():
    from datetime import datetime
    from sqlalchemy import types as t

    user = User(group_id=1, name="foo", created_at=datetime(2000, 1, 1))
    factory = _makeOne({t.Integer: int_for_human, t.DateTime: datetime_for_human})
    target = factory({"name": "Name", "created_at": "CreatedAt", "id": "Id"})
    result = target.serialize(user, ["*"])
    assert result == {'Name': 'foo', 'CreatedAt': '2000/01/01 00:00:00', 'Id': 'this is None'}


def test_relation_onetomany():
    from datetime import datetime
    from sqlash import Pair

    target = _makeOne()()
    users = [
        User(name="boo", created_at=datetime(2000, 1, 1)),
        User(name="yoo", created_at=datetime(2000, 1, 1)),
    ]
    group = Group(name="foo", users=users)
    result = target.serialize(group, ["name", Pair("users", ["name"])])
    assert result == {'users': [{'name': 'boo'}, {'name': 'yoo'}], 'name': 'foo'}


def test_relation_manytoone():
    from datetime import datetime
    from sqlash import Pair

    target = _makeOne()()
    group = Group(name="foo")
    user = User(name="boo", created_at=datetime(2000, 1, 1), group=group)
    result = target.serialize(user, ["name", Pair("group", ["name"])])
    assert result == {'group': {'name': 'foo'}, 'name': 'boo'}


def test_deep_nested():
    from sqlalchemy import types as t
    from datetime import datetime
    from sqlash import Pair

    target = _makeOne({t.DateTime: datetime_for_human})()
    a2 = A2(a1=A1(a0=A0(created_at=datetime(2000, 1, 1))))
    result = target.serialize(a2, [Pair("a1", [Pair("a0", ["created_at"])])])
    assert result == {'a1': {'a0': {'created_at': '2000/01/01 00:00:00'}}}


def test_many_to_many():
    from sqlash import Pair

    target = _makeOne({})()

    team0 = Team(name="foo")
    team1 = Team(name="boo")
    member0 = Member(name="x")
    member1 = Member(name="y")
    member2 = Member(name="z")
    team0.members.append(member0)
    team0.members.append(member1)
    team1.members.append(member1)
    team1.members.append(member2)

    result = target.serialize(team0, ["name", "created_at", Pair("members", ["name", "created_at"])])
    assert result == {'created_at': None, 'name': 'foo',
                      'members': [{'created_at': None, 'name': 'x'},
                                  {'created_at': None, 'name': 'y'}]}


def test_many_to_many2():
    from sqlash import Pair

    target = _makeOne({})()

    team0 = Team(name="foo")
    team1 = Team(name="boo")
    member0 = Member(name="x")
    member1 = Member(name="y")
    member2 = Member(name="z")
    team0.members.append(member0)
    team0.members.append(member1)
    team1.members.append(member1)
    team1.members.append(member2)

    result = target.serialize(member1, ["name", "created_at", Pair("teams", ["name", "created_at"])])
    assert result == {'created_at': None, 'name': 'y',
                      'teams': [{'created_at': None, 'name': 'foo'},
                                {'created_at': None, 'name': 'boo'}]}

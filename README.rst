sqlash
========================================

sqlalchemy short hand (dict from object)

sqlash is simple query language for dict creation from model object.


OneToMany or ManyToOne Relation exmaple
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

models definition

.. code:: python

    import sqlalchemy as sa
    import sqlalchemy.orm as orm
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()


    class User(Base):
        __tablename__ = "users"
        id = sa.Column(sa.Integer, primary_key=True)
        name = sa.Column(sa.String(255), nullable=False)
        created_at = sa.Column(sa.DateTime())
        group_id = sa.Column(sa.Integer, sa.ForeignKey("groups.id"))
        group = orm.relationship("Group", backref="users", uselist=False)


    class Group(Base):
        __tablename__ = "groups"
        id = sa.Column(sa.Integer, primary_key=True)
        name = sa.Column(sa.String(255), nullable=False)
        created_at = sa.Column(sa.DateTime())


    # create serializer

    from sqlash import Pair, SerializerFactory

    def datetime_for_human(dt, r):
        return dt.strftime("%Y/%m/%d %H:%M:%S")

    def int_for_human(v, r):
        return "this is {}".format(v)

    factory = SerializerFactory({t.Integer: int_for_human, t.DateTime: datetime_for_human})
    serializer = factory()

Serializer object is main of sqlash.
constructor of this object takes a mapping of sqlalchemy's field type to convertion function.
and call Serializer.serialize() method for dict creation (e.g. json)


one to many example

.. code:: python

    users = [
        User(name="boo", created_at=datetime(2000, 1, 1)),
        User(name="yoo", created_at=datetime(2000, 1, 1)),
    ]
    group = Group(name="foo", users=users)
    print(serializer.serialize(group, ["name", Pair("users", ["name"])]))
    # {'users': [{'name': 'boo'}, {'name': 'yoo'}], 'name': 'foo'}

call Serializer.serialize() with ["name", Pair("users", ["name"])]. 
so return dict including only names.

many to one

.. code:: python

    user = User(name="boo", created_at=datetime(2000, 1, 1), group=group)
    print(serializer.serialize(user, ["name", Pair("group", ["name"])]))
    # {'group': {'name': 'foo'}, 'name': 'boo'}

passed query(["name", Pair("group", ["name"])]) is almost same that one to many relation case.
this is detecting direction of relationship by serializer object, automatically.

ManyToMany relation example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

may to many relation is also support.

models definition

.. code:: python

    members_to_teams = sa.Table(
        "members_to_teams", Base.metadata,
        sa.Column("member_id", sa.Integer, sa.ForeignKey("members.id")),
        sa.Column("team_id", sa.Integer, sa.ForeignKey("teams.id")),
    )


    class Member(Base):
        __tablename__ = "members"
        id = sa.Column(sa.Integer, primary_key=True)
        name = sa.Column(sa.String(255), nullable=False)
        created_at = sa.Column(sa.DateTime())
        teams = orm.relationship("Team", backref="members", secondary=members_to_teams)


    class Team(Base):
        __tablename__ = "teams"
        id = sa.Column(sa.Integer, primary_key=True)
        name = sa.Column(sa.String(255), nullable=False)
        created_at = sa.Column(sa.DateTime())


many to many exmaples

.. code:: python

    team0 = Team(name="foo")
    team1 = Team(name="boo")
    member0 = Member(name="x")
    member1 = Member(name="y")
    member2 = Member(name="z")
    team0.members.append(member0)
    team0.members.append(member1)
    team1.members.append(member1)
    team1.members.append(member2)

    print(serializer.serialize(team0, ["name", "created_at", Pair("members", ["name", "created_at"])]))
    # {'created_at': None, 'name': 'foo',
    #  'members': [{'created_at': None, 'name': 'x'},
    #              {'created_at': None, 'name': 'y'}]}

call with ["name", "created_at", Pair("members", ["name", "created_at"])]. so, collecting name and created.

abbreviation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

"*" is all of fields, but excludes relationships and foreignkeys

.. code:: python

    user = User(group_id=1, name="foo", created_at=datetime(2000, 1, 1))
    result = serializer.serialize(user, ["*"])
    assert result == {'name': 'foo', 'created_at': '2000/01/01 00:00:00', 'id': 'this is None'}

renaming
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

passing renaming options call factory, then renaming key-name of dict.

.. code:: python

    factory = SerializerFactory({t.Integer: int_for_human, t.DateTime: datetime_for_human})
    target = factory({"name": "Name", "created_at": "CreatedAt", "id": "Id"})
    result = target.serialize(user, ["*"])
    assert result == {'Name': 'foo', 'CreatedAt': '2000/01/01 00:00:00', 'Id': 'this is None'}

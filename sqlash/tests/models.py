# -*- coding:utf-8 -*-
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


# many to many
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


# more nested


class A0(Base):
    __tablename__ = "a0"
    id = sa.Column(sa.Integer, primary_key=True)
    created_at = sa.Column(sa.DateTime(), nullable=False)


class A1(Base):
    __tablename__ = "a1"
    id = sa.Column(sa.Integer, primary_key=True)
    created_at = sa.Column(sa.DateTime(), nullable=False)
    a0_id = sa.Column(sa.Integer, sa.ForeignKey("a0.id"))
    a0 = orm.relationship(A0, backref="children")


class A2(Base):
    __tablename__ = "a2"
    id = sa.Column(sa.Integer, primary_key=True)
    created_at = sa.Column(sa.DateTime(), nullable=False)
    a1_id = sa.Column(sa.Integer, sa.ForeignKey("a1.id"))
    a1 = orm.relationship(A1, backref="children")

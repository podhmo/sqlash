# -*- coding:utf-8 -*-
import logging
logger = logging.getLogger(__name__)
from sqlalchemy.ext.declarative.api import DeclarativeMeta


def model_of(object_or_class):
    if isinstance(object_or_class, DeclarativeMeta):
        return object_or_class  # class
    elif isinstance(object_or_class, type):
        return object_or_class
    else:
        return object_or_class.__class__  # object

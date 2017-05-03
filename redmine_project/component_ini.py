#!/usr/bin/env python
# -*- coding: utf-8 -*-
import redis
from redminelib import Redmine
import ConfigParser
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

PROJECT_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir))
REDMINE_ROOT = os.path.join(PROJECT_ROOT, 'redmine_project')

app = Flask('__main__')
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://wechat:password@127.0.0.1/wechat'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

config = ConfigParser.RawConfigParser()
config.read('{}{}'.format(REDMINE_ROOT, '/config.ini'))
redmine = Redmine(url=config.get('redmine', 'url'),
                  key=config.get('redmine', 'key'),
                  version=config.get('redmine', 'version'))
redis_handler = redis.StrictRedis(host='localhost', port=6379, db=0)

#!/usr/bin/env python3.5
# -*- coding: utf-8 -*-

__author__ = 'Changxun Fan'

from wsgiref.handlers import CGIHandler
from matelook import app

CGIHandler().run(app)

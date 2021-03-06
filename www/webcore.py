#!/usr/bin/env python3
# -*- coding: utf-8 -*-
<<<<<<< HEAD
import asyncio, os, inspect, logging, functools

#define decorator @get('/path') 
def get(path):
	def decorator(func):
		@functools.wraps(func)
		def wapper(*args, **kw):
			return func(*args, **kw)
		func.__method__ = 'GET'
		func.__route__ = path
		return wapper
	return decorator

#define decorator @post('/path') 
def post(path):
	def decorator(func):
		@functools.wraps(func)
		def wapper(*args, **kw): 
			return func(*args, **kw)
		func.__method__ = 'POST'
		func.__route__ = path
		return wapper
	return decorator
=======
import logging; logging.basicConfig(level=logging.INFO)
import asyncio, os, inspect, functools

def add_static(app):
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
	app.router.add_static('/static/', path)
	logging.info('add static %s => %s' % ('/static/',path))

def add_route(app, fn):
	method = getattr(fn, '__method__', None)
	path = getattr(fn, '__route__', None)
	if path is None or method is None:
		raise ValueError('@get or @post not defined in %s.' % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)
	logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
	app.router.add_route(method, path, RequestHandler(app, fn))

def add_routes(app, module_name):
	n = module_name.rfind('.')
	if n == (-1):
		mod = __import__(module_name, globals(), locals())
	else:
		name = module_name[n+1:]
		mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
	for attr in dir(mod):
		if attr.startswith('__'):
			continue
		fn = getattr(mod, attr)
		if callable(fn):
			method = getattr(fn, '__method__', None)
			path = getattr(path, '__route__', None)
			if method and path:
				add_route(app, fn)

def add_static(app):
	spath = os.path.join(os.path.dirname(__file__), 'static')
	app.router.add_static('/static/', spath)
	logging.info('add static %s => %s' % ('/static/', spath))
	add_route(app, fn)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio, logging; 
import aiomysql
logging.basicConfig(level=logging.INFO)

def log(sql, args=()):
    logging.info('SQL: %s' % sql)

async def Create_Pool(loop,**kw):
	logging.info('create database connection pool..')
	global __pool
	__pool = await aiomysql.create_pool(
		host=kw.get('host','localhost'),
		port=kw.get('port',3306),
		user=kw['user'],
		password=kw['password'],
		db=kw['db'],
		charset=kw.get('charset','utf8'),
		autocommit=kw.get('autocommit',True),
		maxsize=kw.get('maxsize',10),
		minsize=kw.get('minsize',1),
		loop=loop
		)

async def select(sql,args,size=None):
	log(sql,args)
	global __pool
	async with __pool.acquire() as conn:
		async with conn.cursor(aiomysql.DictCursor) as cur:
			await cur.execute(sql.replace('?','%s'), args or ())
			#await cur.execute(sql)
			if size:
				rs = await cur.fetchmany(size)
			else:
				rs = await cur.fetchall()
		logging.info('rows return: %s'%len(rs))
		return rs

async def execute(sql, args, autocommit=True):
	log(sql)
	
	async with __pool.acquire() as conn:
		if not autocommit:
			await conn.begin()
		try:
			async with conn.cursor(aiomysql.DictCursor) as cur:
				await cur.execute(sql.replace('?','%s'),args)
				affected = cur.rowcount
			if not autocommit:
				await conn.commit()

		except BaseException as e:
			if not autocommit:
				await conn.rollback()
			raise
		return affected

class Field(object):
	def __init__(self, name, column_type, primary_key, default):
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default
	def __str__(self):
		return '<%s,%s:%s>'%(self.__class__.__name__,self.column_type,self.name)

class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

class ModelMetaclass(type):
	def __new__(cls, name, bases, attrs):
		if name=='Model':
			return type.__new__(cls, name, bases, attrs)
		tableName = attrs.get('__table__', None or name)
		logging.info('found model:%s (table: %s)'%(name, tableName))
		mappings = dict()
		fields = []
		primary_key = None
		for k,v in attrs.items():
			if isinstance(v, Field):
				logging.info(' found mapping:%s==>%s'%(k,v))
				mappings[k] = v
				if v.primary_key:
					if primary_key:
						raise StandardError('duplicate primary_key for field:%s' % k)
					primary_key = k
				else:
					fields.append(k)
		if not primary_key:
			raise StandardError('primary_key not found')
		for k in mappings.keys():
			attrs.pop(k)
		escaped_fields = list(map(lambda f: '`%s`'% f, fields))
		def create_args_string(lens):
			L = []
			for x in range(lens):
				L.append('?')
			return ','.join(L)
		attrs['__mappings__']=mappings
		attrs['__table__']=tableName
		attrs['__primary_key__']=primary_key
		attrs['__fields__']=fields
		attrs['__select__']='select `%s`, %s from `%s`' % (primary_key, ', '.join(escaped_fields), tableName)
		attrs['__insert__']='insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primary_key, create_args_string(len(escaped_fields) + 1))
		attrs['__update__']='update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primary_key)
		attrs['__delete__']='delete from `%s` where `%s`=?' % (tableName, primary_key)
		return type.__new__(cls, name, bases, attrs)

class Model(dict, metaclass=ModelMetaclass):
	def __init__(self, **kw):
		super(Model,self).__init__(**kw)

	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError as e:
			raise AttributeError(r'Model object has no attr %s' % key)
	def __setattr__(self, key):
		self[key] = value

	def getvalue(self, key):
		return getattr(self, key, None)

	def getValueOrDefault(self, key):
		value = getattr(self, key, None)
		if value is None:
			field = self.__mappings__[key]
			if field.default is not None:
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s: %s' % (key, str(value)))
				setattr(self, key, value)
		return value
	@classmethod
	async def findall(cls, where=None, args=None, **kw):
		sql = [cls.__select__]
		if where:
			sql.append('where')
			sql.append(where)
		if args is None:
			args = []
		orderby = kw.get('orderby',None)
		if orderby:
			sql.append('order by')
			sql.append(orderby)
		limit = kw.get('limit',None)
		if limit:
			sql.append('limit')
			if isinstance(limit,int):
				sql.append('?')
				args.append(limit)
			elif isinstance(limit,tuple) and len(limit) == 2:
				sql.append('limit ?,?')
				args.extend(limit)
			else:
				raise ValueError('Invalid limit value:(%s)' % limit)
		rs = await select(' '.join(sql), args)
		return [cls(**r) for r in rs]

	@classmethod
	async def findbypk(cls, pk):
		rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
	__table__ = 'user'

	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	name = StringField(ddl='varchar(50)')

async def start():
	rs=await select('select * from user',args=())
	logging.info(rs)

async def start2():
	user = await User.findbypk('123456')
	logging.info(user)
if __name__ == '__main__':
	loop = asyncio.get_event_loop()
	loop.run_until_complete(Create_Pool(loop=loop,host='172.16.87.157',user='dbUser',password='dbuser',db='test'))
	loop.run_until_complete(start2())
	loop.run_forever()
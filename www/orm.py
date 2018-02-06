import asyncio, logging; logging.basicConfig(level=logging.INFO)
import aiomysql

def log(sql, args=()):
    logging.info('SQL: %s' % sql)

async def Create_Pool(loop,**kw):
	logging.info('create database connection pool..')
	global __pool
	__pool = await aiomysql.create_pool(
		host=kw.get('host','localhost'),
		port=kw.get('port','3306'),
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

class ModelMetaclass(type):
	def __new__(cls, name, bases, attrs):
		if name=='Model':
			return type.__new__(cls, name, bases, attrs)
		tableName = attrs.get('__table__', None or name)
		logging('found model:%s (table: %s)'%(name, tableName))
		mappings = dict()
		fields = []
		primary_key = None
		for k,v in attrs.items():
			if isinstance(v, Field):
				logging.info(' found mapping:%s==>%s'%(k,v))
				mappings[key] = v
				if v.primary_key:
					if primary_key:
						raise StandardError('duplicate primary_key for field:%s'%k)
					else:
						fields.append(k)
					primary_key = k
		if not primary_key:
			raise StandardError('primary_key not found')
		for k in mappings.keys():
			attrs.pop(k)
		escaped_fields = list(map(lambda f:'`%s`') % f, fields)
		attrs['__mappings__']=mappings
		attrs['__table__']=tableName
		attrs['__primary_key__']=primary_key
		attrs['__fields__']=fields
		attrs['__select__']='select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
		attrs['__insert__']='insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
		attrs['__update__']='update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
		attrs['__delete__']='delete from `%s` where `%s`=?' % (tableName, primaryKey)
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


class Field(object):
	def __init__(self, name, column_type, primary_key, default):
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default
	def __str__(self):
		return '<%s,%s:%s>'%(self.__class__.__name__,self.column_type,self.name)


def start(loop):
	logging.INFO('create pool')
	yield from Create_Pool(loop=loop,host='192.168.0.221',user='root',password='wjdh849283999',db='test')
	rs=yield from select('select * from user',args=())
	print(rs)

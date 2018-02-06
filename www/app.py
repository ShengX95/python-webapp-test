import logging; logging.basicConfig(level=logging.INFO)
import asyncio, os, json, time
from aiohttp import web
import orm
#index
def index(request):
	return web.Response(body=b'<h1>Awesome<h1/>',content_type='text/html')

@asyncio.coroutine
def init(evnet_loop):
	app = web.Application(loop=evnet_loop)
	app.router.add_route('GET','/',index)
	srv = yield from evnet_loop.create_server(app.make_handler(), '127.0.0.1', 8080)
	logging.info('server start at http://127.0.0.1:8080..')
	return srv
loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
orm.start(loop)
loop.run_forever()
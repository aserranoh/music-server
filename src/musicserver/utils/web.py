
'''Web server and web service utilities.'''

import json
import logging
import socket
import tornado.httpclient
import tornado.web

__author__ = 'Antonio Serrano Hernandez'
__copyright__ = 'Copyright 2021'
__license__ = 'proprietary'
__version__ = '0.1'
__maintainer__ = 'Antonio Serrano Hernandez'
__email__ = 'toni.serranoh@gmail.com'
__status__ = 'Development'


class BaseHandler(tornado.web.RequestHandler):

    def initialize(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class WebServer:

    _MAX_LISTEN_RETRIES = 10
    _LISTEN_RETRY_SLEEP_TIME = 0.1

    def __init__(self, handlers, port=8888, **kwargs):
        tornado.httpclient.AsyncHTTPClient.configure(
            'tornado.curl_httpclient.CurlAsyncHTTPClient')
        self._port = port
        self._closing = False
        self._ready = False
        self._app = tornado.web.Application(handlers, **kwargs)

    async def _stop_callback(self):
        if self._closing:
            self._stopcb.stop()
            self._is_ready = False
            self._httpserver.stop()
            await self._httpserver.close_all_connections()            
            tornado.ioloop.IOLoop.current().stop()

    def addhandler(self, pattern, handler, data=None):
        if data is not None:
            t = (pattern, handler, data)
        else:
            t = (pattern, handler)
        self._app.add_handlers(r'.*', [t])

    def run(self):
        logging.info('starting web.Server')
        self._httpserver = self._app.listen(self._port, no_keep_alive=True)
        self._ready = True
        self._stopcb = tornado.ioloop.PeriodicCallback(
            self._stop_callback, 1000)
        self._stopcb.start()
        tornado.ioloop.IOLoop.current().start()
        logging.info('exiting web.Server')

    def stop(self):
        self._closing = True

    def ready(self):
        '''Return whether the server is ready or not.'''
        return self._ready

class ServiceHandler(BaseHandler):

    async def _execute_method(self, method):
        '''Execute the given web service method.'''
        # Get the function attributes
        attrs = {k: v[0].decode('utf-8')
            for k, v in self.request.query_arguments.items()}

        # Call the webservice method
        try:
            result = WebServiceResult(await method.execute(**attrs))
        except Exception as e:
            result = WebServiceErrorResult(e)

        # Return the result serialized
        self.write(result.tojson())

    def _error(self, errormsg):
        '''Return an error.'''
        result = WebServiceErrorResult(errormsg)
        self.write(result.tojson())

    async def get(self, method):
        '''Serve webservice functions as get.'''
        # Get the method to execute
        try:
            m = self.webservice.getmethod(method, self.request)
            await self._execute_method(m)
        except KeyError:
            # The method doesn't exist
            self._error(f'unknown method {method}')

    async def post(self, method):
        '''Serve webservice functions as post.'''
        # Get the method to execute
        try:
            m = self.webservice.postmethod(method, self.request)
            await self._execute_method(m)
        except KeyError:
            # The method doesn't exist
            self._error(f'unknown method {method}')

class WebService:

    GET, POST = range(2)

    def __init__(self, base, server, data=None):
        server.addhandler(r'/{}/(.*)'.format(base), ServiceHandler,
            data={'webservice': self})
        self._data = data
        self._get = {}
        self._post = {}

        # Prepare a dictionary with the different types to the right methods
        self._methods = [
            self._get, self._post
        ]

    def addmethods(self, methods):
        '''Add methods to the web service.'''
        for name, handler, type_ in methods:
            self._methods[type_][name] = handler

    def getmethod(self, method, request):
        '''Return a get method given its name.'''
        return self._get[method](request, self._data)

    def postmethod(self, method, request):
        '''Return a post method given its name.'''
        return self._post[method](request, self._data)

class WebServiceMethod:
    '''Base class for all web service methods.'''

    def __init__(self, request, data):
        self.request = request
        self.data = data

class WebServiceResult:
    '''Contains the value returned by a web service method.'''

    def __init__(self, data):
        self._data = data

    def tojson(self):
        '''Return the data of the result serialized as json.'''
        return json.dumps({'error': False, 'data': self._data})

class WebServiceErrorResult:
    '''Represents an error result.'''

    def __init__(self, error):
        self._errorstr = str(error)

    def tojson(self):
        '''Return the data of the result serialized as json.'''
        return json.dumps({'error': True, 'errmsg': self._errorstr})


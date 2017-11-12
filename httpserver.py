import logging
import http.server
import socketserver
import os
import lttngust

class LoggingHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self._logger = logging.getLogger('HTTP-logger')
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self._logger.debug('begin GET')
        super().do_GET()
        self._logger.debug('end GET')

    def log_request(self, code='-', size='-'):
        self._logger.debug('{} request: {}, code: {}, size: {}'.format(
            self.address_string(), self.requestline, code, size))

    def log_error(self, format, *args):
        self._logger.error('%s - %s' %
                           (self.address_string(),
                            format%args))

    def log_message(self, format, *args):
        self._logger.info('%s - %s' %
                          (self.address_string(),
                           format%args))


logging.basicConfig()

PORT = 8000
print('Server PID: {}'.format(os.getpid()))

httpd = socketserver.TCPServer(("", PORT), LoggingHTTPRequestHandler)
httpd.allow_reuse_address = True
httpd.serve_forever()
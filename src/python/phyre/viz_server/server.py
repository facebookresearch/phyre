#!/usr/bin/env python
# Copyright (c) Facebook, Inc. and its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
import logging
import time

from thrift.server import TServer
import thrift.transport
import thrift.protocol.TJSONProtocol
import tornado.ioloop
import tornado.web

import phyre.interface.task.TaskService
from phyre import settings
import phyre.viz_server.handler

# Local path to static HTML files to serve.
HTML_PATH = str(settings.HTML_DIR)

# URL path to server config at.
PHYRE_CONFIG_PATH = '/phyre_config.js'

MAX_BALLS_DEMO_MODE = 5


class Processor(phyre.interface.task.TaskService.Processor):

    def __init__(self, handler):
        super().__init__(handler)
        self._processMap = {k: _time_me(v) for k, v in self._processMap.items()}


class RequestHandler(tornado.web.RequestHandler, TServer.TServer):

    def initialize(self, processor, prot_factory):
        TServer.TServer.__init__(self, processor, None, None, None,
                                 prot_factory, prot_factory)

    def options(self):
        self.set_header('Access-Control-Allow-Headers', 'Content-Type')
        self.set_header('Access-Control-Allow-Methods', 'OPTIONS, POST, GET')
        self.set_header('Access-Control-Allow-Origin', '*')

    def post(self):
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Content-Type', 'application/x-thrift')
        self.write(self.handle_request(self.request.body))

    def on_message(self, message):
        self.write_message(self.handle_request(message))

    def handle_request(self, data):
        itrans = thrift.transport.TTransport.TMemoryBuffer(data)
        otrans = thrift.transport.TTransport.TMemoryBuffer()
        iprot = self.inputProtocolFactory.getProtocol(itrans)
        oprot = self.outputProtocolFactory.getProtocol(otrans)
        self.processor.process(iprot, oprot)
        return otrans.getvalue()


class ConfigHandler(tornado.web.RequestHandler):

    def initialize(self, config):
        self._config = config

    def options(self):
        self.set_header('Access-Control-Allow-Headers', 'Content-Type')
        self.set_header('Access-Control-Allow-Methods', 'OPTIONS, GET')

    def get(self):
        body = 'window.phyre_config = %s\n' % json.dumps(self._config)
        self.set_header('Cache-control', 'no-cache')
        self.set_header('Content-Type', 'text/javascript')
        self.write(body)


class StaticFileHandler(tornado.web.StaticFileHandler):

    def set_extra_headers(self, path):
        del path  # Not used.
        self.set_header('Cache-control', 'no-cache')


def _time_me(f):

    def new_f(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        print('%s took %.3fs' % (f.__name__, time.time() - start))
        return result

    return new_f


def main_with_args(port, mode):
    assert port != 3000, 'Cannot start on port 3000 as it used for React dev server'
    config = dict(mode=mode)
    config[
        'max_balls'] = MAX_BALLS_DEMO_MODE if mode == phyre.viz_server.handler.DEMO_MODE else 0
    handler = phyre.viz_server.handler.ServiceHandler(config)
    processor = Processor(handler)
    pfactory = thrift.protocol.TJSONProtocol.TJSONProtocolFactory()

    handlers = [(r'/rpc(?:.*)', RequestHandler, {
        'processor': processor,
        'prot_factory': pfactory
    }), (PHYRE_CONFIG_PATH, ConfigHandler, {
        'config': config
    }),
                (r'/(.*)', StaticFileHandler, {
                    'path': HTML_PATH,
                    'default_filename': 'index.html',
                })]
    application = tornado.web.Application(handlers)

    print(f'I\'m {__file__}')
    print(f'Config: {config}')
    print(f'Going to read tasks from {settings.TASK_DIR}')
    print(f'Going to serve static HTML from {HTML_PATH}')
    print(f'Starting server on port {port}')
    application.listen(port)
    tornado.ioloop.IOLoop.current().start()


def main():
    logging.basicConfig(format=('%(asctime)s %(levelname)-8s'
                                ' {%(module)s:%(lineno)d} %(message)s'),
                        level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=30303)
    parser.add_argument('--mode',
                        choices=(
                            phyre.viz_server.handler.PROD_MODE,
                            phyre.viz_server.handler.DEV_MODE,
                            phyre.viz_server.handler.DEMO_MODE,
                        ),
                        default=phyre.viz_server.handler.DEMO_MODE)
    main_with_args(**vars(parser.parse_args()))


if __name__ == '__main__':
    main()

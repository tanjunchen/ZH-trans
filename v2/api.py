#!/usr/bin/python
# -*- coding: utf-8 -*-
from wsgiref.simple_server import make_server
import json
from urlparser import urlparser


def application(start_response):
    start_response('200 OK', [('Content-Type', 'text/html')])
    # params = urlparser(environ['QUERY_STRING'])
    # name = params.get('name', [''])[0]
    # no = params.get('no', [''])[0]
    dic = {'name': 'a', 'no': 'b'}
    return [json.dumps(dic)]


if __name__ == "__main__":
    url = '127.0.0.1'
    port = 8081
    httpd = make_server(url, port, application)
    print("serving http on port {0}...".format(str(port)))
    httpd.serve_forever()

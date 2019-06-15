__author__ = 'FOCUS'

from flask import Flask, render_template, request
import os, sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

from threading import Thread, Timer, Lock, Event

try:
    from templates import cmu_graphics
except Exception as e:
    print(e)

"""
useless stuff
BROWSER_OPEN = True

class MyRequestHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        relpath = os.path.relpath(path, os.getcwd())
        fullpath = os.path.join(self.server.base_dir, relpath)
        return fullpath

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super(MyRequestHandler, self).end_headers()

    def log_message(self, format, *args):
        return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True  # comment to keep threads alive until finished

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
"""

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('simple-af.html')

@app.route('/', methods=['POST'])
def run_code():
    code = request.form['text']
    header="from templates import cmu_graphics\ncmu_graphics.Rect(100, 100, 100, 100)\ncmu_graphics.run()"
    #try:
    #    exec(code)
    #except Exception as e:
    #    print(e)
    exec(header)
    ## TO-DO: complete
    #print(first_name)
    #return 'Hello %s %s have fun learning python <br/> <a href="/">Back Home</a>' % (first_name, last_name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1000)

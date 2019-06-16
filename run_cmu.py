__author__ = 'FOCUS'

from flask import Flask, render_template, request
import os, sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

from threading import Thread, Timer, Lock, Event


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('osama.html')


@app.route('/', methods=['POST'])
def run_code():
    code = request.form['text']
    header = "from templates import cmu_graphics\ncmu_graphics.Rect(100, 100, 100, 100)\ncmu_graphics.run()"
    exec(header)
    return('', 204)
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1000)

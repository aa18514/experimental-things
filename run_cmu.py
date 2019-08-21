__author__ = 'FOCUS'

from flask import Flask, render_template, request
import os, sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from flask_restful import Resource, Api
from threading import Thread, Timer, Lock, Event
from flask_cors import CORS, cross_origin

app = Flask(__name__)
api = Api(app)
app.debug = True
CORS(app)

@app.route('/')
def index():
    return render_template('osama.html')


@app.route('/', methods=['POST'])
def run_code():
    code = request.form['text']
    code = "from templates.cmu_graphics import *\nresetGlobals()\n" + code + "\nrun()\n"
    print(code)
    try:
        exec(code)
    except Exception as e:
        print(e)
    return('', 204)
    
@app.route('/IFrameCodeRun', methods=['POST'])
def SolutionCode():
	print("came in")
	if request.method == "POST":
		content = request.get_json()
		code = content['code']
		code = "from templates.cmu_graphics import *\nresetGlobals()\n" + code + "\nrun()\n"
		print(code)
		try:
			exec(code)
		except Exception as e:
			print(e)
		jsonify({'result':'testing'})
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1000)

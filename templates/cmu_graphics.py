# pylint: disable= too-few-public-methods, missing-docstring, superfluous-parens, invalid-name, too-many-arguments, broad-except, bare-except, len-as-condition, too-many-instance-attributes

from datetime import date
expiry = date(2019, 8, 31)
if date.today() > expiry:
    print("This beta version of Local CMU Graphics has expired")
    print("Please contact support@csacademy.freshdesk.com for a current version.")
    os._exit(1)

from random import random, randrange, choice, seed  # pylint: disable=unused-import
import math
import traceback

IS_BRYTHON = True
try:
    from browser import window  # pylint: disable=import-error
except:
    IS_BRYTHON = False

IS_INTERACTIVE = False
try:
    import __main__ as main
    IS_INTERACTIVE = not hasattr(main, '__file__')
except:
    IS_INTERACTIVE = True

########################################
### Local AF Server
########################################

class struct(object): pass

def structify(d):
    if isinstance(d, dict):
        for key in d:
            d[key] = structify(d[key])
        s = struct()
        s.__dict__.update(d)
        return s
    return d

if (not IS_BRYTHON):
    import os, sys
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    from socketserver import ThreadingMixIn

    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        allow_reuse_address = True
        daemon_threads = True  # comment to keep threads alive until finished

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        """Handle requests in a separate thread."""

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

def initLocalAfServer():
    def client_left(client, server):
        global BROWSER_OPEN
        BROWSER_OPEN = False
        server.shutdown()

    def message_received(client, server, message):
        msgData = json.loads(message)
        if (msgData['type'] == 'functionReturn'):
            server.window.fnReturnValues[msgData['returnId']] = msgData['returnValue']
            server.window.fnEvents[msgData['returnId']].set()

    def event_message_received(client, server, message):
        msgData = json.loads(message)
        if (msgData['type'] == 'handleMessage'):
            msg = structify(window.cleanReturnValue(msgData['msg']))
            handleMessage(msg)

    server = WebsocketServer(9001)
    server.set_fn_message_received(message_received)
    server.set_fn_client_left(client_left)

    event_server = WebsocketServer(9002)
    event_server.set_fn_message_received(event_message_received)
    event_server.set_fn_client_left(client_left)

    http_server = ThreadedHTTPServer(('localhost', 3000), MyRequestHandler)

    def serve_until_close(server):
        while BROWSER_OPEN:
            server.handle_request()

    server.own_thread = Thread(target = server.serve_forever)
    server.own_thread.start()
    event_server.own_thread = Thread(target = event_server.serve_forever)
    event_server.own_thread.start()
    http_server.own_thread = Thread(target = lambda : serve_until_close(http_server))
    http_server.own_thread.start()

    return server, event_server, http_server

########################################
### Create window
########################################

if (not IS_BRYTHON):
    from threading import Thread, Timer, Lock, Event
    from .websocket_server import WebsocketServer
    from urllib import request
    import webbrowser
    import json
    import time
    import uuid

    GRAPHICS_READY = Event()
    BROWSER_OPEN = True
    IN_EVENT = True
    FN_SERVER, EVENT_SERVER, HTTP_SERVER = initLocalAfServer()

    windowFunctions = {'jsSet', 'jsGet', 'jsGetPositionsAttrs',
                       'jsNew', 'jsApply', 'jsGetJsAppGroup',
                       'jsSetAppProperty', 'jsGetAppProperty',
                       'jsSetBackground', 'jsGetBackground',
                       'activateDrawing', 'doUpdate',
                       'jsSetInterval', 'jsClearInterval', 'sendJSEvent'}

    class Utils(object):
        @staticmethod
        def checkArgCount(clsName, fnName, argNames, args):
            if (len(argNames) != len(args)):
                callSpec = f'{clsName}.{fnName}' if (clsName and fnName) else (clsName or fnName)
                raise Exception(f'Arg Count Error: {callSpec}() takes {len(argNames)} arguments ({",".join(argNames)}), not {len(args)}')

        @staticmethod
        def typeError(obj, attr, value, typeName):
            callSpec = (f'{attr} in {obj}') if (type(obj) == str) else (f'{obj.__class__.__name__}.{attr}')
            valueType = type(value).__name__
            err = f'Type Error: {callSpec} should be {typeName} (but {value} is of type {valueType})';
            raise Exception(err)

        @staticmethod
        def checkNumber(obj, attr, value):
            if type(value) != int and type(value) != float:
                Utils.typeError(obj, attr, value, 'Number')

        @staticmethod
        def checkShape(obj, attr, value):
            if not isinstance(value, Shape):
                Utils.typeError(obj, attr, value, 'Shape')

        @staticmethod
        def polygonContainsPoint(pts, px, py):
            # based on: https://github.com/mathigon/fermat.js/blob/master/src/geometry.js
            n = len(pts)
            inside = False
            for i in range(n):
                q1 = pts[i]
                q2 = pts[(i + 1) % n]
                q1x = q1[0]
                q1y = q1[1]
                q2x = q2[0]
                q2y = q2[1]
                x = (q1y > py) != (q2y > py)
                if (q2y - q1y == 0):
                    y = True
                else:
                    y = px < (q2x - q1x) * (py - q1y) / (q2y - q1y) + q1x
                if (x and y): inside = not inside
            return inside

        @staticmethod
        def pointNearPolygonBorder(pts, x, y, d):
            # does not check if the polygon contains the point!
            d2 = d ** 2
            n = len(pts)
            for i in range(n):
                p1 = pts[i]
                p2 = pts[(i + 1) % n]
                x1 = p1[0]
                y1 = p1[1]
                x2 = p2[0]
                y2 = p2[1]
                if (Utils.distanceToLineSegment2(x, y, x1, y1, x2, y2) <= d2):
                    return True
            return False

        @staticmethod
        def distance2(x1, y1, x2, y2):
            return (x2 - x1) ** 2 + (y2 - y1) ** 2

        @staticmethod
        def distanceToLineSegment2(x, y, x1, y1, x2, y2):
            # return square of distance from (x,y) to ((x1,y1),(x2,y2))
            # inspired by https://stackoverflow.com/questions/849211/shortest-distance-between-a-point-and-a-line-segment/24913403
            l2 = Utils.distance2(x1, y1, x2, y2)
            if (l2 == 0): return distance(x, y, x1, y1)
            t = ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / l2
            t = max(0, min(1, t))
            return Utils.distance2(x, y, x1 + t * (x2 - x1), y1 + t * (y2 - y1))

        @staticmethod
        def segmentsIntersect(x1, y1, x2, y2, x3, y3, x4, y4):
            dxa = x2 - x1
            dya = y2 - y1
            dxb = x4 - x3
            dyb = y4 - y3
            s = (-dya * (x1 - x3) + dxa * (y1 - y3)) / (-dxb * dya + dxa * dyb)
            t = (+dxb * (y1 - y3) - dyb * (x1 - x3)) / (-dxb * dya + dxa * dyb)
            return (s >= 0 and s <= 1 and t >= 0 and t <= 1)

        @staticmethod
        def getChildShapes(shape):
            result = []
            if isinstance(shape, Group):
                for s in shape.children:
                    result += Utils.getChildShapes(s)
            else:
                result = [shape]
            return result

    class Interval(object):
        def __init__(self, fn, delay):
            self.fn = fn
            self.delay = delay
            self.is_active = True
            self.msg = json.dumps({
                'type': 'timerSet',
                'delay': self.delay,
                'fn': window.cleanArguments(self.fn),
                'interval': window.cleanArguments(self)
            })
            self.set()

        def set(self):
            if self.is_active:
                try:
                    FN_SERVER.send_message_to_all(self.msg)
                except:
                    pass

    class jsObject(object):
        def __init__(self, id, constructorInfo=None):
            self._id = id
            self._constructorInfo = constructorInfo

        def dict_repr(self):
            return {'type':'jsObject', 'id':self._id, 'constructorInfo':self._constructorInfo}
        def __getattr__(self, attr):
            if (attr[0] == '_'):
                return self.__dict__[attr]
            else:
                return jsGet(self.dict_repr(), attr)
        def __setattr__(self, attr, val):
            if (attr[0] == '_'):
                self.__dict__[attr] = val
            else:
                jsSet(self.dict_repr(), attr, val)
            return val

        def __repr__(self):
            self.__repr__ = jsGet(self.dict_repr(), 'toString')
            return self.__repr__()

    class Window(object):
        def __init__(self, server):
            self.server = server
            self.server.window = self
            self.fnReturnValues = dict()
            self.fnEvents = dict()

            self.console = struct()
            self.console.log = lambda *args: None

        def printToTextArea(self, line):
            print(line)

        def isClose(self, u, v):
            return abs(u - v) < 10e-8;

        def toDegrees(self, radians):
            return radians * 180 / math.pi

        def toRadians(self, degrees):
            return degrees * math.pi / 180

        def distance(self, x1, y1, x2, y2):
            return math.sqrt((x2-x1)**2 + (y2-y1)**2)

        def fromPythonAngle(self, radians):
            return (90 - self.toDegrees(radians)) % 360

        def toPythonAngle(self, degrees):
            return (self.toRadians(90 - degrees)) % (2 * math.pi)

        def angleTo(self, x1, y1, x2, y2):
            dx = x2 - x1
            dy = y2 - y1
            return self.fromPythonAngle(math.atan2(-dy, dx))

        def getPointInDir(self, x1, y1, degrees, d):
            A = self.toPythonAngle(degrees)
            return [x1 + d * math.cos(A), y1 - d * math.sin(A)]

        def setInterval(self, fn, delay):
            #return self.jsSetInterval(fn, delay)
            return Interval(fn, delay)

        def clearInterval(self, i):
            #self.jsClearInterval(i)
            i.is_active = False
            return None

        def gradient(self, *args):
            return jsObject(str(uuid.uuid4()), ['gradient', args])

        def jsInitShape(self, *args):
            return jsObject(str(uuid.uuid4()), ['jsInitShape', args])

        def rgb(self, *args):
            return jsObject(str(uuid.uuid4()), ['rgb', args])

        def sendJSEvent(*args, **kwargs):
            pass

        def generateJSFunction(self, name=None, id=None, clearCache=False):
            def jsFn(*args):
                returnId = str(uuid.uuid4())
                data = {
                    'type': 'functionCall',
                    'args': self.cleanArguments(list(args)),
                    'returnId': returnId,
                }

                if name is not None:
                    data['name'] = name
                if id is not None:
                    data['id'] = id

                if (clearCache):
                    Shape.dirtyShapesLock.acquire()
                    if (len(Shape.setArgsList) > 0):
                        data['setUpdates'] = self.cleanArguments([Shape.setArgsList])
                        Shape.setArgsList = []

                self.fnEvents[returnId] = Event()
                #print(json.dumps(data))
                try:
                    self.server.send_message_to_all(json.dumps(data))
                except:
                    pass

                if (clearCache):
                    Shape.dirtyShapesLock.release()

                if not self.fnEvents[returnId].wait(1):
                    # The browser closed in the middle of this request
                    sys.exit()

                returnValue = self.fnReturnValues[returnId]
                del self.fnReturnValues[returnId]
                del self.fnEvents[returnId]
                return self.cleanReturnValue(json.loads(returnValue))
            return jsFn

        def cleanArguments(self, v):
            if (isinstance(v, list)):
                return list(map(self.cleanArguments, v))
            if (isinstance(v, tuple)):
                return tuple(map(self.cleanArguments, v))
            if (isinstance(v, int) or isinstance(v, float)
                or isinstance(v, str) or isinstance(v, bool)
                or v is None):
                return v
            if (isinstance(v, dict)):
                newDict = dict()
                for key in v:
                    newDict[key] = self.cleanArguments(v[key])
                return newDict
            if isinstance(v, jsObject):
                partial = v.dict_repr()
                if 'constructorInfo' in partial:
                    partial['constructorInfo'] = self.cleanArguments(partial['constructorInfo'])
                return partial
            if isinstance(v, Shape):
                return self.cleanArguments(v._shape)
            else:
                idMap[id(v)] = v
                return {'type': 'pythonObject', 'id': id(v)}

        def cleanReturnValue(self, v):
            if (isinstance(v, dict)):
                if ('type' in v):
                    if (v['type'] == 'jsObject'):
                        return jsObject(v['id'])
                    elif (v['type'] == 'pythonObject'):
                        return idMap[v['id']]
                    elif (v['type'] == 'null'):
                        return None
                    elif (v['type'] == 'functionCallback'):
                        return self.generateJSFunction(id=v['id'], clearCache=True)
                return {key: self.cleanReturnValue(v[key]) for key in v}
            elif (isinstance(v, list)):
                return list(map(self.cleanReturnValue, v))
            else:
                return v

        def __getattr__(self, attr):
            if (attr in windowFunctions):
                return self.generateJSFunction(name=attr)
            else:
                return self.__dict__[attr]

    window = Window(FN_SERVER)

    def updateDrawing():
        try:
            FN_SERVER.send_message_to_all(json.dumps({'type': 'update'}))
        except:
            pass

    def bulkJsSet(*args):
        try:
            FN_SERVER.send_message_to_all(json.dumps({'type': 'bulkJsSet', 'args': window.cleanArguments(list(args))}))
        except:
            pass

    def run():
        if (codeHasEventHandlers(['onStep', 'onKeyHold'])):
            startTimerEvents(CURRENT_APP_STATE)
        with Shape.dirtyShapesLock:
            Shape.setArgsList.append(["doUpdate"])

        for _ in range(3):
            try:
                FN_SERVER.own_thread.join()
                EVENT_SERVER.own_thread.join()
                request.urlopen('http://localhost:3000/simple-af.html')
                HTTP_SERVER.own_thread.join()
                break
            except KeyboardInterrupt:
                print()
                print("CMU Graphics received KeyboardInterrupt... quitting")
                os._exit(1)

    def startGraphics():
        webbrowser.open('http://localhost:3000/simple-af.html')
        GRAPHICS_READY.wait()
        global CURRENT_APP_STATE
        CURRENT_APP_STATE = APP_STATES['userCanvas'] = AppState('userCanvas')
        import __main__
        CURRENT_APP_STATE.userGlobals = __main__.__dict__
        window.jsSetAppProperty('stopped', False)
        window.jsSetAppProperty('paused', False)
        callUserFn('onStart')

########################################
### Clear Local Shape Cache
########################################
if (not IS_BRYTHON):
    def clearShapeCache(oneTime = False, lock=True):
        argsList = []
        if lock:
            Shape.dirtyShapesLock.acquire()

        if len(Shape.setArgsList) > 0:
            # If we're changing shape properties from functions outside of
            # the CMU Graphics functions, update the drawing on all bulk sets
            if not IN_EVENT or IS_INTERACTIVE:
                Shape.setArgsList.append(['doUpdate'])
            bulkJsSet(Shape.setArgsList)
            Shape.setArgsList = []

        if lock:
            Shape.dirtyShapesLock.release()

        if (BROWSER_OPEN and not oneTime):
            Timer(0.001, clearShapeCache).start()

    Timer(0.001, clearShapeCache).start()

try:
    # slight speedup storing these in globals:
    jsSet = window.jsSet;
    jsGet = window.jsGet; jsGetPositionsAttrs = window.jsGetPositionsAttrs;
    jsNew = window.jsNew; jsApply = window.jsApply; jsInitShape = window.jsInitShape
    rgb = window.rgb; distance = window.distance
    toPythonAngle = window.toPythonAngle; fromPythonAngle = window.fromPythonAngle
    angleTo = window.angleTo; getPointInDir = window.getPointInDir
except AttributeError as e:
    # Catch this error so that this module can be imported to call compilePyCode()
    # without setting up all the JS helper functions.
    print('Ok (ignoring error setting up js globals):', e)

def makeTopLevelGroup():
    return Group()
window.makeTopLevelGroup = makeTopLevelGroup

CMU_GRAPHICS_IMPORT_LINE = (
    '''from cmu_graphics_bry import %s
try:
    from cmu_graphics_bry import assertEqual
except:
    pass
''' % ', '.join([
    'almostEqual',
    'angleTo',
    'app',
    'Arc',
    'choice',
    'Circle',
    'distance',
    'fromPythonAngle',
    'getPointInDir',
    'gradient',
    'Group',
    'Image',
    'input',
    'Label',
    'Line',
    'makeList',
    'Oval',
    'onCheckpointResult',
    'onSteps',
    'onKeyHolds',
    'Polygon',
    'print',
    'pythonRound',
    'random',
    'randrange',
    'Rect',
    'registerGlobals',
    'RegularPolygon',
    'rgb',
    'round',
    'rounded',
    'seed',
    'Star',
    'toPythonAngle',
    ]))
CMU_GRAPHICS_IMPORT_LINE_COUNT = len(CMU_GRAPHICS_IMPORT_LINE.split('\n')) - 1


class CMUGraphicsAssertion(Exception): pass


def assertEqual(actual, expected):
    if actual != expected:
        raise CMUGraphicsAssertion(f'{actual} != {expected}')


def makeList(rows, cols, value=None):
    if rows < 0 or cols < 0:
        raise Exception('Both rows and cols must be >= 0')
    return [[value for _ in range(cols)] for _ in range(rows)]


def compilePyCode(code):
    return window.__BRYTHON__.python_to_js(
        CMU_GRAPHICS_IMPORT_LINE
        + code
        + "\n\n" + "registerGlobals(globals())",
        "__main_soln__")

APP_STATES = {} # canvasId: AppState
CURRENT_APP_STATE = None

pythonRound = round


EPSILON = 10e-7
def almostEqual(x, y, epsilon=EPSILON):
    return abs(x - y) <= epsilon

def rounded(d):
    sign = 1 if (d >= 0) else -1
    d = abs(d)
    n = int(d)
    if (d - n >= 0.5): n += 1
    return sign * n

def round(*args):
    raise Exception("Use our rounded(n) instead of Python 3's round(n)\n"
                    "  Python 3's round(n) does not work as one might expect!\n"
                    "  If you still want Python 3's round, use pythonRound")

if (IS_BRYTHON):
    def input(*args, **kwargs):
        raise Exception("Sorry, you cannot use Python's input function in CMU CS Academy")
else:
    input = input

def gradient(*colors, start=None):
    return window.gradient(colors, 'center' if start is None else start)

idMap = dict()
shapeAttrs = {'left', 'top', 'centerX', 'centerY', 'right', 'bottom', 'width',
              'height', 'fill', 'border', 'borderWidth', 'dashes', 'opacity',
              'align', 'rotateAngle', 'radius', 'points', 'roundness', 'x1',
              'y1', 'x2', 'y2', 'arrowStart', 'arrowEnd', 'lineWidth',
              'initialPoints', 'closed', 'startAngle', 'sweepAngle', 'value',
              'font', 'size', 'bold', 'italic', 'visible', 'url', 'db', 'children',
              '_toString'}

positionAttrs = {
    'centerX': {'left', 'right', 'centroid', 'x1', 'x2', 'pointList', 'centerX'},
    'centerY': {'top', 'bottom', 'centroid', 'y1', 'y2', 'pointList', 'centerY'},
    'left': {'centerX', 'right', 'centroid', 'x1', 'x2', 'pointList', 'left'},
    'top': {'centerY', 'bottom', 'centroid', 'y1', 'y2', 'pointList', 'top'},
    'right': {'centerX', 'left', 'centroid', 'x1', 'x2', 'pointList', 'right'},
    'bottom': {'centerY', 'top', 'centroid', 'y1', 'y2', 'pointList', 'bottom'},
    'rotateAngle': {'left', 'top', 'right', 'bottom', 'x1', 'x2', 'y1', 'y2', 'width', 'height', 'pointList', 'rotateAngle'},
    'centroid': {'centerX', 'centerY', 'left', 'top', 'right', 'bottom', 'x1', 'x2', 'y1', 'y2', 'pointList', 'centroid'},
    'width': {'centerX', 'left', 'right', 'centroid', 'width', 'pointList', 'rotateAngle'},
    'height': {'centerY', 'top', 'bottom', 'centroid', 'height', 'pointList', 'rotateAngle'},
    'x1': {'centerX', 'top', 'bottom', 'centroid', 'pointList', 'x1'},
    'x2': {'centerX', 'top', 'bottom', 'centroid', 'pointList', 'x2'},
    'y1': {'centerY', 'left', 'right', 'centroid', 'pointList', 'y1'},
    'y2': {'centerY', 'left', 'right', 'centroid', 'pointList', 'y2'},
    'pointList': {'centerX', 'centerY', 'left', 'top', 'right', 'bottom', 'x1', 'x2', 'y1', 'y2', 'centroid', 'pointList'},
}

class Shape(object):
    if (not IS_BRYTHON):
        dirtyShapesLock = Lock()
        setArgsList = []

    def __init__(self, clsName, argNames, args, kwargs):
        self._shape = jsInitShape(clsName, argNames, args, kwargs)
        if (not IS_BRYTHON):
            # Manually set brythonShape so we don't clean the argument back
            # into self._shape
            idMap[id(self)] = self
            self._shape.brythonShape = {'type': 'pythonObject', 'id': id(self)}
            self._position_is_dirty = False
            self._cached_attrs = dict()
            self._parent_group = None
        else:
            self._shape.brythonShape = self

    def __setattr__(self, attr, val):
        if (attr[0] == '_' or attr not in shapeAttrs):
            self.__dict__[attr] = val
        else:
            if (not IS_BRYTHON):
                with Shape.dirtyShapesLock:
                    if (attr in positionAttrs):
                        self._position_is_dirty = True
                        for positionAttr in positionAttrs[attr]:
                            if positionAttr in self._cached_attrs:
                                del self._cached_attrs[positionAttr]

                    if (attr == 'visible' and self._parent_group is not None):
                        self._parent_group.bustCache(lock=False)

                    Shape.setArgsList.append([self._shape, attr, val])
                    self._cached_attrs[attr] = val
            else:
                jsSet(self._shape, attr, val)
        return val

    def __getattr__(self, attr):
        if (attr in shapeAttrs or attr not in self.__dict__):
            if (not IS_BRYTHON):
                with Shape.dirtyShapesLock:
                    if attr in self._cached_attrs:
                        return self._cached_attrs[attr]
                    elif attr in positionAttrs:
                        clearShapeCache(oneTime = True, lock = False)
                        position_attrs = jsGetPositionsAttrs(self._shape)
                        self._cached_attrs.update(position_attrs)
                        self._position_is_dirty = False
                        return self._cached_attrs[attr]
                    else:
                        result = jsGet(self._shape, attr)
                        self._cached_attrs[attr] = result
                        return result
            else:
                return jsGet(self._shape, attr)
        else:
            return self.__dict__[attr]

    def __repr__(self): return self._toString()

    # # Collision duplicated from cmu-graphics.js
    # if (not IS_BRYTHON):
    #     def contains(self, *arguments): # contains(x,y)
    #         Utils.checkArgCount(self.__class__.__name__, 'contains', ['x', 'y'], arguments)
    #         x, y = arguments
    #         Utils.checkNumber('contains(x, y)', 'x', x)
    #         Utils.checkNumber('contains(x, y)', 'y', y)
    #         return Utils.polygonContainsPoint(self.pointList, x, y)
    #
    #     def hits(self, *arguments): # hits(x,y)
    #         Utils.checkArgCount(self.__class__.__name__, 'hits', ['x', 'y'], arguments)
    #         x, y = arguments
    #         Utils.checkNumber('hits(x, y)', 'x', x)
    #         Utils.checkNumber('hits(x, y)', 'y', y)
    #         pts = self.pointList;
    #         if (not Utils.polygonContainsPoint(pts, x, y)): return False;
    #         if (self.fill): return True
    #         border = self.border
    #         if (not border): return False;
    #         # ok, so we have a border, but no fill, so we 'hit' if we
    #         # are within a borderWidth of the border
    #         bw = self.borderWidth if border else 0
    #         return Utils.pointNearPolygonBorder(pts, x, y, bw)
    #
    #     def edgesIntersect(self, shape):
    #         pts1 = self.pointList
    #         pts2 = shape.pointList
    #         k = None
    #         for i in range(len(pts1)):
    #             x1, y1 = pts1[i];
    #             k = (i + 1) % (len(pts1));
    #             x2, y2 = pts1[k];
    #             for j in range(len(pts2)):
    #                 x3, y3 = pts2[j];
    #                 k = (j + 1) % (len(pts2))
    #                 x4, y4 = pts2[k];
    #                 if (Utils.segmentsIntersect(x1, y1, x2, y2, x3, y3, x4, y4)):
    #                     return True
    #         return False
    #
    #     def containsShape(self, targetShape):
    #         Utils.checkArgCount(self.__class__.__name__, 'containsShape', ['targetShape'], arguments);
    #         Utils.checkShape('containsShape(targetShape)', 'targetShape', targetShape);
    #
    #         if (isinstance(targetShape, Group)):
    #             return all([self.containsShape(shape) for shape in targetShape.children])
    #
    #         # This shapes fully contains the target shape if their
    #         # edges do not intersect, but (any point of / all points of)
    #         # the targetShape are inside this shape
    #         x = targetShape.centerX
    #         y = targetShape.centerY
    #         return (not self.edgesIntersect(targetShape) and self.contains(x, y))
    #
    #     def getBounds(self):
    #         return { left: self.left, top: self.top, width: self.width, height: self.height }
    #
    #     def boundsIntersect(self, targetShape, margin = None):
    #         # Symmetric.  Fast pre-test for hitsShape.  If this is False, hitsShape
    #         # must be False.  If this is True, hitsShape *may* be True.
    #         if (margin is None): margin = 0
    #         b1 = self.getBounds()
    #         b2 = targetShape.getBounds()
    #         return ((b1.left + margin <= b2.left + b2.width) and
    #                 (b2.left + margin <= b1.left + b1.width) and
    #                 (b1.top  + margin <= b2.top + b2.height) and
    #                 (b2.top  + margin <= b1.top + b1.height))
    #
    #     def hitsShape(self, *arguments):
    #         Utils.checkArgCount(self.__class__.__name__, 'hitsShape', ['targetShape'], arguments);
    #         (targetShape,) = arguments
    #         Utils.checkShape('hitsShape(targetShape)', 'targetShape', targetShape);
    #         # Symmetric.  Two shapes hit each other if any of their
    #         # vertices hit the other or their edges intersect.
    #         myShapes = Utils.getChildShapes(self);
    #         targetShapes = Utils.getChildShapes(targetShape);
    #
    #         for i in range(len(myShapes)):
    #             for j in range(len(targetShapes)):
    #                 if (myShapes[i].edgesIntersect(targetShapes[j])):
    #                     return True
    #
    #         for i in range(len(myShapes)):
    #             for j in range(len(targetShapes)):
    #                 shape1 = myShapes[i]
    #                 shape2 = targetShapes[j]
    #                 if any((shape2.hits(pt[0], pt[1]) for pt in shape1.pointList)):
    #                     return True
    #                 if any((shape1.hits(pt[0], pt[1]) for pt in shape2.pointList)):
    #                     return True
    #                 if myShapes[i].edgesIntersect(targetShapes[i]):
    #                     return True
    #
    #         return False

class Rect(Shape):
    def __init__(self, *args, **kwargs):
        super().__init__('Rect', ['left', 'top', 'width', 'height'], args, kwargs)

class Image(Shape):
    def __init__(self, *args, **kwargs):
        super().__init__('Image', ['url', 'left', 'top'], args, kwargs)

class Oval(Shape):
    def __init__(self, *args, **kwargs):
        super().__init__('Oval', ['centerX', 'centerY', 'width', 'height'], args, kwargs)

class Circle(Shape):
    def __init__(self, *args, **kwargs):
        super().__init__('Circle', ['centerX', 'centerY', 'radius'], args, kwargs)

class RegularPolygon(Shape):
    def __init__(self, *args, **kwargs):
        super().__init__('RegularPolygon', ['centerX', 'centerY', 'radius', 'points'], args, kwargs)

class Star(Shape):
    def __init__(self, *args, **kwargs):
        super().__init__('Star', ['centerX', 'centerY', 'radius', 'points'], args, kwargs)

class Line(Shape):
    def __init__(self, *args, **kwargs):
        super().__init__('Line', ['x1', 'y1', 'x2', 'y2'], args, kwargs)

class Polygon(Shape):
    def __init__(self, *args, **kwargs):
        super().__init__('Polygon', [ 'initialPoints' ], [args], kwargs)

class Arc(Shape):
    def __init__(self, *args, **kwargs):
        super().__init__('Arc', ['centerX', 'centerY', 'width', 'height',
                                 'startAngle', 'sweepAngle'], args, kwargs)

class Label(Shape):
    def __init__(self, *args, **kwargs):
        super().__init__('Label', ['value', 'centerX', 'centerY'], args, kwargs)

class Group(Shape):
    def __init__(self, *args, **kwargs):
        super().__init__('Group', [ ], [ ], kwargs)

        if (not IS_BRYTHON):
            self.initMethods()

        for shape in args:
            self.add(shape)

    if (not IS_BRYTHON):
        def initMethods(self):
            self._jsAdd = jsGet(self._shape, 'add')
            self._jsRemove = jsGet(self._shape, 'remove')
            self._jsClear = jsGet(self._shape, 'clear')

        def bustCache(self, lock=True):
            if lock:
                Shape.dirtyShapesLock.acquire()

            if 'children' in self._cached_attrs:
                del self._cached_attrs['children']
            self._position_is_dirty = True
            for positionAttr in positionAttrs:
                if positionAttr in self._cached_attrs:
                    del self._cached_attrs[positionAttr]

            if lock:
                Shape.dirtyShapesLock.release()

        def add(self, *args):
            self._jsAdd(*args)
            for shape in args:
                shape._parent_group = self
            self.bustCache()

        def remove(self, *args):
            self._jsRemove(*args)
            for shape in args:
                shape._parent_group = None
            self.bustCache()

        def clear(self, *args):
            self._jsClear(*args)
            for shape in args:
                shape._parent_group = None
            self.bustCache()

        # # Duplicated from cmu-graphics.js
        # def hits(self , x, y):
        #     return self.hitTest(x, y) is not None
        #
        # def hitTest(self, x, y):
        #     for i in range(len(self.children) - 1, -1, -1):
        #         if (self.children[i].hits(x, y)):
        #             return self.children[i]
        #
        # def contains(self, x, y):
        #     return any((shape.contains(x, y) for shape in self.children))
        #
        # def containsShape(self, target):
        #     return any((shape.containsShape(target) for shape in self.children))
        #
        # # End duplicated

        def __iter__(self):
            return iter(self.children)

        def __setattr__(self, attr, val):
            if (attr[0] == '_' or attr not in shapeAttrs):
                self.__dict__[attr] = val
            else:
                super().__setattr__(attr, val)
                with Shape.dirtyShapesLock:
                    if (attr in positionAttrs):
                        children = []
                        if 'children' in self._cached_attrs:
                            children = self._cached_attrs['children']
                        else:
                            children = jsGet(self._shape, 'children')
                            self._cached_attrs['children'] = children
                        for child in children:
                            child._position_is_dirty = True
                            for positionAttr in positionAttrs[attr]:
                                if positionAttr in child._cached_attrs:
                                    del child._cached_attrs[positionAttr]
            return val


def registerGlobals(globalVars):
    for name in globalVars:
        CURRENT_APP_STATE.userGlobals[name] = globalVars[name]

def onSteps(n):
    for _ in range(n):
        callUserFn('onStep')

def onKeyHolds(keys, n):
    assert isinstance(keys, list), 'keys must be a list'
    for _ in range(n):
        callUserFn('onKeyHold', keys)

if (IS_BRYTHON):
    def print(*args, end=None, sep=None):
        printLine(*args, end=end, sep=sep)
else:
    print = print

class App(object):
    def __init__(self):
        self.left = self.top = 0
        self.centerX = self.centerY = 200
        self.right = self.width = self.bottom = self.height = 400
        self._stepsPerSecond = 30
        self._allKeysDown = set()
        window.jsSetAppProperty('stopped', True)
        self.paused = False
        self._paused = False
        self.textInputs = []

        if (not IS_BRYTHON):
            self._group = None

    def getTextInput(self, promptText=''):
        if self.textInputs:
            return self.textInputs.pop(0)
        if (IS_BRYTHON):
            return window.jsGetTextInput(promptText)
        else:
            return input(promptText)

    def setTextInputs(self, *args):
        for arg in args:
            if not isinstance(arg, str):
                raise Exception('Arguments to setTextInputs must be strings. %r is not a string.' % arg)
        self.textInputs = list(args)

    def getStepsPerSecond(self):
        return self._stepsPerSecond
    def setStepsPerSecond(self, value):
        self._stepsPerSecond = value
        stopTimerEvents()
        startTimerEvents(CURRENT_APP_STATE)
    stepsPerSecond = property(getStepsPerSecond, setStepsPerSecond)

    def getGroup(self):
        if (IS_BRYTHON):
            return window.jsGetAppGroup()
        else:
            if (self._group is None):
                self._group = Group()
                self._group._shape = window.jsGetJsAppGroup()
                self._group.initMethods()

            return self._group

    def setGroup(self, _):
        raise Exception('App.group is readonly')
    group = property(getGroup, setGroup)

    def getPaused(self):
        if (IS_BRYTHON):
            return window.jsGetAppProperty('paused')
        else:
            return self._paused
    def setPaused(self, value):
        self._paused = value
        window.jsSetAppProperty('paused', value)
        if (IS_BRYTHON):
            if not self.stopped:
                window.sendJSEvent('frameworkPaused' if value else 'frameworkUnpaused')
    paused = property(getPaused, setPaused)

    def getBackground(self):
        return window.jsGetBackground()
    def setBackground(self, value):
        window.jsSetBackground(value)
    background = property(getBackground, setBackground)

    def getStopped(self):
        return window.jsGetAppProperty('stopped')
    def setStopped(self, _):
        raise Exception('App.stopped is readonly')
    stopped = property(getStopped, setStopped)

    def getMaxShapeCount(self):
        return window.jsGetAppProperty('maxShapeCount')
    def setMaxShapeCount(self, value):
        return window.jsSetAppProperty('maxShapeCount', value)
    maxShapeCount = property(getMaxShapeCount, setMaxShapeCount)

    def stop(self):
        stopCode(notifyIDE=True)

    def step(self):
        onStepButton()

class AppState(object):
    def __init__(self, canvasId):
        self.canvasId = canvasId
        self.code = None
        self.currentTimer = None
        self.app = App()
        self.userGlobals = {}

class Snippet(object):
    def __init__(self, code, mode):
        self.code = code
        self.mode = mode

def dbprint(*args):
    window.console.log('py dbprint:', *args)

def printLine(*args, end=None, sep=None):
    if end is None:
        end = '\n'
    if sep is None:
        sep = ' '
    line = sep.join(map(str, args)) + end
    window.printToTextArea(line)

def printException(e, code):
    args = e.args
    lineOffset = CMU_GRAPHICS_IMPORT_LINE_COUNT if code.startswith(CMU_GRAPHICS_IMPORT_LINE) else 0
    if (isinstance(e, SyntaxError)):
        (desc, module, line, offset, lineCode) = (args[0], args[1], args[2],
                                                  args[3], args[4])
        printLine('\nSyntaxError at line %s: %s' % (line - lineOffset, desc))
        printLine('  ' + lineCode)
        printLine('  ' + offset*' ' + '^')
    else:
        printLine('\n%s: %s' % (e, args[0]))

def printTraceback(tb, code):
    dbprint('printTraceback:')
    dbprint(tb)
    print(tb)
    lines = tb.splitlines()
    errorLine = lines.pop(-1)
    if errorLine.strip() == '':
        errorLine = lines.pop(-1)
    stars = '*****************************'
    printLine(stars)
    if (lines[0].startswith('Traceback (most recent call last):')):
        lines.pop(0)
        printLine('An error occurred. Here is the stack trace:')
    hadSourceLines = False
    allLines = code.splitlines()

    while (lines):
        try:
            line = lines.pop(0)
            if ', in ' in line:
                line = line[:line.index(', in ')]
            lineNumberLineParts = line.split()
            module = lineNumberLineParts[1]
            lineNumber = int(lineNumberLineParts[-1])
            lineNumberToShow = lineNumber
            if code.startswith(CMU_GRAPHICS_IMPORT_LINE):
                # Adjust the line number to match the code the user typed
                lineNumberToShow = lineNumber - CMU_GRAPHICS_IMPORT_LINE_COUNT
            if (lines and lines[0].startswith('    ')):
                lines.pop(0)
            if '<string>' in module:
                codeLine = allLines[lineNumber - 1] if lineNumber <= len(allLines) else ''
                hadSourceLines = True
                printLine('  line %d:\n    %s' % (lineNumberToShow, codeLine))
        except:
            pass
    report = ((not hadSourceLines)
        or ('CMUGraphicsInternalError' in errorLine)
        or ('<Javascript' in errorLine))
    if not hadSourceLines:
        # Check to see if the error is that one of their callbacks has
        # too few or too many positional arguments
        for handlerName in ['onStep', 'onMousePress', 'onMouseRelease',
                            'onMouseDrag', 'onMouseMove', 'onKeyPress', 'onKeyRelease',
                            'onKeyHold']:
            if (('%s() takes' % handlerName) in errorLine
                    or ('%s() missing' % handlerName) in errorLine):
                report = False
    if report:
        dbprint('Reporting error to Rollbar')
        window.sendJSEvent('rollbarError', {
            'message': 'Error with no user source',
            'detail': tb,
        })
    # Remove 'cmu_graphics_bry.' from the name of any exceptions being printed
    errorLine = errorLine.replace('cmu_graphics_bry.', '')
    printLine(errorLine)
    printLine(stars)

def onError(tb=None, exception=None, stopOnError=True, code=None):
    if code is None:
        code = CURRENT_APP_STATE.code
    if code is None:
        code = ''
    try:
        if (exception not in [None, '']):
            printException(exception, code=code)
        if (tb != None):
            printTraceback(tb, code=code)
        if (stopOnError):
            stopCode()
    except:
        printLine('**** Error in onError()!!! ****')
        window.sendJSEvent('rollbarError', {
            'message': 'Error in onError()',
            'detail': traceback.format_exc(),
        })
        traceback.print_exc()

    if (not IS_BRYTHON and stopOnError):
        os._exit(1)

def execCode1(code, mode, stopOnError, okCallback, errCallback):
    try:
        if mode == 'py':
            code = CMU_GRAPHICS_IMPORT_LINE + code
            CURRENT_APP_STATE.code = code
            exec(code, CURRENT_APP_STATE.userGlobals)
        else:
            window.eval(code)
        okCallback()
        return True
    except Exception as e:
        if isinstance(e, SyntaxError):
            onError(exception=e, stopOnError=stopOnError)
        else:
            tbLines = traceback.format_exc()
            if (mode == 'js'):
                window.sendJSEvent('rollbarError', {
                    'message': 'Error executing solution code',
                    'detail': tbLines,
                })
            onError(tb=tbLines, stopOnError=stopOnError)
        errCallback(e)
        return False

def execCode(snippets, stopOnError, okCallback, errCallback):
    def runSnippets(i):
        if (i >= len(snippets)):
            okCallback()
        else:
            snippet = snippets[i]
            execCode1(snippet.code, snippet.mode, stopOnError,
                      lambda: runSnippets(i+1), errCallback)
    runSnippets(0)

def evalOrExecCode(code, stopOnError, okCallback, errCallback):
    if 'Polygon' not in CURRENT_APP_STATE.userGlobals:
        exec(CMU_GRAPHICS_IMPORT_LINE, CURRENT_APP_STATE.userGlobals)
    try:
        printLine(repr(eval(code, CURRENT_APP_STATE.userGlobals)))
        okCallback()
    except Exception as e:
        snippets = [Snippet(code, 'py')]
        if (str(e) == 'eval() argument must be an expression'):
            execCode(snippets, stopOnError, okCallback, errCallback)
        else:
            if (isinstance(e, SyntaxError)):
                onError(exception=e, stopOnError=stopOnError, code=code)
            else:
                tbLines = traceback.format_exc()
                onError(tb=tbLines, stopOnError=stopOnError, code=code)
            errCallback(e)

def onShellInput(event):
    def okCallback():
        pass
    def errCallback(err):
        pass
    evalOrExecCode(event.detail.input, False, okCallback, errCallback)

def makeSafeFn(fn):
    def safeFn(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            tbLines = traceback.format_exc()
            if (isinstance(e, SyntaxError)):
                onError(exception=e)
            else:
                onError(tb=tbLines)
    return safeFn

def onAutogradeButton(event):
    userCode = event.detail.userCode
    solnCode = event.detail.solnCode
    testCases = getattr(event.detail, 'testCases', None)
    agId = event.detail.agId
    # dbprint('onAutogradeButton', event)
    if testCases is not None and len(testCases) > 0:
        Autograder.runNested(agId, userCode, solnCode, testCases)
    else:
        Autograder.runNotNested(agId, userCode, solnCode)

def callUserFn(fnName, *args):
    userGlobals = CURRENT_APP_STATE.userGlobals
    if (fnName in userGlobals):
        try:
            userGlobals[fnName](*args)
            with Shape.dirtyShapesLock:
                Shape.setArgsList.append(["doUpdate"])
        except Exception as e:
            tbLines = traceback.format_exc()
            if (isinstance(e, SyntaxError)):
                onError(exception=e)
            else:
                onError(tb=tbLines)

def resetGlobals():
    stopTimerEvents()
    CURRENT_APP_STATE.userGlobals = {}
    CURRENT_APP_STATE.app = App()

def runCode(snippets, okCallback, errCallback, shouldResetGlobals=True):
    if (shouldResetGlobals):
        window.clearDrawing()
        resetGlobals()
        if app.stopped:
            window.jsSetAppProperty('stopped', False)
        if app.paused:
            window.jsSetAppProperty('paused', False)
    execCode(snippets, True, okCallback, errCallback)

def stopTimerEvents():
    if (CURRENT_APP_STATE.currentTimer is not None):
        window.clearInterval(CURRENT_APP_STATE.currentTimer)
    CURRENT_APP_STATE.currentTimer = None

def startTimerEvents(appState):
    def setIntervalFn():
        if (IS_BRYTHON):
            global CURRENT_APP_STATE
            CURRENT_APP_STATE = appState
            window.activateDrawing(appState.canvasId)
            if not CURRENT_APP_STATE.app.paused and not CURRENT_APP_STATE.app.stopped:
                doStep()
                window.doUpdate()
        else:
            if not CURRENT_APP_STATE.app.paused:
                doStep()
    stopTimerEvents()
    if (codeHasEventHandlers(['onStep', 'onKeyHold']) and (CURRENT_APP_STATE.app.stepsPerSecond > 0)):
        CURRENT_APP_STATE.currentTimer = window.setInterval(
            makeSafeFn(setIntervalFn), 1000/CURRENT_APP_STATE.app.stepsPerSecond)

def codeHasEventHandlers(handlers):
    for handler in handlers:
        if (handler in CURRENT_APP_STATE.userGlobals):
            return True
    return False

def onCompileCode(event):
    code_to_compile = event.detail.code

    try:
        compiled_code = compilePyCode(code_to_compile)
    except:
        return

    window.sendJSEvent('codeCompiled', {'code': compiled_code})

def onRunButton(event):
    if (not IS_BRYTHON):
        GRAPHICS_READY.set()
        return
    snippets = event.detail.snippets
    shouldResetGlobals = ('resetGlobals' in event.detail) and event.detail.resetGlobals
    def okCallback():
        callUserFn('onStart')
        if (codeHasEventHandlers(['onStep', 'onKeyHold'])):
            startTimerEvents(CURRENT_APP_STATE)
    def errCallback(err):
        stopCode()
        window.sendJSEvent('frameworkErrored')
    runCode(snippets, okCallback, errCallback, shouldResetGlobals=shouldResetGlobals)

def stopCode(msg=None, notifyIDE=True):
    if (IS_BRYTHON):
        window.jsSetAppProperty('stopped', True)
        stopTimerEvents()
        if (msg != None):
            printLine(msg)
        if (notifyIDE):
            window.sendJSEvent('frameworkStop')

def doStep():
    if CURRENT_APP_STATE.app._allKeysDown:
        callUserFn('onKeyHold', list(CURRENT_APP_STATE.app._allKeysDown))
    callUserFn('onStep')

def onStepButton(*args):
    CURRENT_APP_STATE.app.paused = True
    doStep()

def onPauseButton(_):
    CURRENT_APP_STATE.app.paused = True

def onUnpauseButton(_):
    CURRENT_APP_STATE.app.paused = False

def onStopButton(_):
    resetGlobals()
    window.sendJSEvent('onStopButtonComplete')

def onMouse(event):
    assert event.detail.subtype in ['onMousePress', 'onMouseDrag', 'onMouseMove', 'onMouseRelease']
    if IS_BRYTHON:
        if CURRENT_APP_STATE.app.paused and event.detail.subtype == 'onMouseMove':
            return
        if CURRENT_APP_STATE.app.stopped:
            return
    callUserFn(event.detail.subtype, event.detail.x, event.detail.y)

def onKey(event):
    assert event.detail.subtype in ['onKeyPress', 'onKeyRelease']
    if CURRENT_APP_STATE.app.stopped:
        return
    callUserFn(event.detail.subtype, event.detail.key)
    if event.detail.subtype == 'onKeyPress':
        CURRENT_APP_STATE.app._allKeysDown.add(event.detail.key)
    else:
        CURRENT_APP_STATE.app._allKeysDown -= {event.detail.key.upper(), event.detail.key.lower()}

def onInterval(event):
    event.detail.fn()
    event.detail.interval.set()

def onThrow(event):
    raise Exception(event.detail.msg)

def onCheckpointResult(ok):
    window.sendJSEvent('checkpointResult', {'ok': ok})

EVENT_TO_HANDLER = {
    'compileCode': onCompileCode,
    'brythonPause': onPauseButton,
    'brythonRunCode': onRunButton,
    'brythonShellInput': onShellInput,
    'brythonStep': onStepButton,
    'brythonStop': onStopButton,
    'brythonUnpause': onUnpauseButton,
    'onKey': onKey,
    'onMouse': onMouse,
    'onInterval': onInterval,
    'onThrow': onThrow,
}

def makeEventHandlerFn(fn):
    safeFn = makeSafeFn(fn)
    def eventHandlerFn(event):
        return safeFn(event)
    return eventHandlerFn

for eventName in EVENT_TO_HANDLER:
    EVENT_TO_HANDLER[eventName] = makeEventHandlerFn(EVENT_TO_HANDLER[eventName])

def handleMessage(msg):
    global CURRENT_APP_STATE
    if (msg.type not in EVENT_TO_HANDLER
        or (not IS_BRYTHON and msg.type not in ['onKey', 'onMouse', 'onInterval', 'onThrow', 'brythonRunCode'])):
        print('ignoring event type %s' % msg.type)
    else:
        canvasId = msg.detail.canvasId
        CURRENT_APP_STATE = APP_STATES.get(canvasId)
        if CURRENT_APP_STATE is None:
            CURRENT_APP_STATE = APP_STATES[canvasId] = AppState(canvasId)

        if (not IS_BRYTHON):
            global IN_EVENT
            IN_EVENT = True
            EVENT_TO_HANDLER[msg.type](msg)
            IN_EVENT = False
        else:
            EVENT_TO_HANDLER[msg.type](msg)

class AppWrapper(object):
    def __getattr__(self, attr):
        return getattr(CURRENT_APP_STATE.app, attr)

    def __setattr__(self, attr, value):
        setattr(CURRENT_APP_STATE.app, attr, value)

app = AppWrapper()

###############################
## Exports to JS
###############################

window.handleMessage = handleMessage

###############################
## Local Auto-run Code
###############################

if (not IS_BRYTHON):
    startGraphics()

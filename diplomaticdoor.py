import sys
import diplomaticfingerprintreader
import userstore

import json
import tempfile
import os
import requests
import threading
import re
import functools
import waitress

import mimetypes
from flask_batch import add_batch_route
from flask import Flask, send_from_directory, send_file, request, Response, jsonify
app = Flask(__name__)
add_batch_route(app)

ADMIN_MODE=False 

def admin_mode_only(func):
    @functools.wraps(func)
    def wrapper(user_id):
        result = func(user_id)
        if not ADMIN_MODE and (int(user_id) in diplomatic_door.get_permitted_users()):
            return {"result": "Admin mode is disabled."}
        return result

    return wrapper

def mimetype(mimetype):
    def decorator(func):
        func.mimetype = mimetype
        return func
    return decorator

def jsonator(func):
    @functools.wraps(func)
    @mimetype("application/json")
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        result = {"result": result} if type(result) is not dict else result
        fp = tempfile.TemporaryFile()
        json.dump(result, fp)
        return fp
    return wrapper

def extract_range(header=None):
    if header is None:
        header = request.headers.get('Range', None)
    if header is None:
        return None
    match = re.search('(\d*)-(\d*)', header)
    if match is None:
        return None
    start, end = match.groups()
    start = int(start) if start else None
    end = int(end) if end else None
    return (start, end)

def rangorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        f = func(*args, **kwargs)
        if f is None:
            return Response('', 404)

        mimetype = func.func_dict.get('mimetype', 'application/octet-stream')
        range_header = extract_range()
        if not range_header:
            f.seek(0)
            data = f.read()
            return Response(data, 200, mimetype=mimetype)

        start, end = range_header
        size = None
        if start is not None:
            f.seek(start)
            if end is not None:
                size = max((end + 1 - start, 0))
        elif end is not None:
            f.seek(0, os.SEEK_END)
            end = min((end, f.tell()))
            f.seek(-end, os.SEEK_CUR)
            size = end

        offset = f.tell()
        data = f.read(size) if size is not None else f.read()

        rv = Response(data, 206, mimetype=mimetype)
        rv.headers.add('Content-Range', 'bytes {0}-{1}/*'.format(offset, offset + len(data) - 1))
        rv.headers.add('Accept-Ranges', 'bytes')
        return rv

    return wrapper

class DiplomaticDoor(object):
    def __init__(self, db_folder="db"):
        # load user view 
        self.db_folder = db_folder
        self._user_store = userstore.UserStore(self.db_folder)

    def get_user_summary(self, user_id):
        user_object = self._user_store.get_user(user_id)
        if user_object is None:
            return None
                
        summary = {}
        summary['first_name'] = user_object.first_name
        summary['last_name'] = user_object.last_name
        summary['comments'] = user_object.comments
        return summary
    
    def get_fingerprint_filename(self, user_id):
        user_object = self._user_store.get_user(user_id)
        if user_object is None:
            return None

        return user_object.fingerprint_bmp

    def get_permitted_users(self):
        return self._user_store.permitted_user_ids

diplomatic_door = None
fingerprint_readers = list()

@app.route("/")
@rangorator
@jsonator
def index():
    global diplomatic_door
    return "Welcome to the Diplomatic Door entry system."

@app.route("/user/<user_id>")
@rangorator
@jsonator
def user(user_id):
    global diplomatic_door
    summary = diplomatic_door.get_user_summary(user_id)
    if summary is None:
        return "User id is not enrolled..."
    return summary 

@app.route("/fingerprint/<user_id>")
@admin_mode_only
@rangorator
@mimetype("image/bmp")
def fingerprint(user_id):
    fingerprint_file = diplomatic_door.get_fingerprint_filename(user_id)
    if fingerprint_file is None:
        return None

    fingerprint_folder = userstore.UserStore.FINGERPRINT_PATH
    bmp_path = os.path.join(diplomatic_door.db_folder, fingerprint_folder, fingerprint_file)
    return open(bmp_path, "rb")


@app.route("/enroll/<user_id>")
@rangorator
@jsonator
@admin_mode_only
def enroll(user_id):
    # TODO
    return {}

def main(args):
    global diplomatic_door
    global fingerprint_readers
    diplomatic_door = DiplomaticDoor()
    serial_ports = args[1:]
    for sp in serial_ports:
        print("Setting up reader on port %s" % (sp,))

        fp = diplomaticfingerprintreader.DiplomaticFingerprintReader(sp, diplomatic_door.get_permitted_users())
        if not fp.setup():
            print("Could not open device on port %s" % (sp,))
            continue
        fingerprint_readers.append(fp)
        fp.start()

    if len(fingerprint_readers) == 0:
        print("Could not set up any fingerprint readers, door cannot open.")
        return -1

    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        pass

    for fp in fingerprint_readers:
        fp.stop()
        fp.close()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
    

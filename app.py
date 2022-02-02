from flask import Flask, request
from queue import Queue
import logging
import sys
import os
app = Flask(__name__)
app.mp_queue = Queue()
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
@app.route('/auth', methods=['GET','POST'])
def get_auth():
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    d = {'oauth_token':oauth_token,'oauth_verifier':oauth_verifier}
    # print(f'Received auth token and verifier: {d}')
    app.mp_queue.put(d)
    
    return "Received auth token, you may close this window"

@app.route('/')
def default():
    return "This is a temporary server"
def start_server(queue):
    app.mp_queue = queue
    oldstdout = sys.stdout
    with open(os.devnull, 'w') as f:
        sys.stdout = f
        app.run()
    sys.stdout = oldstdout
import os
import os.path
import requests
import json
from flask import Flask, request, render_template, abort
from werkzeug import secure_filename

ALLOWED_IMG_EXTENSIONS = set(['tiff', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'ico', 'pbm', 'pgm', 'ppm'])
UPLOAD_FOLDER = '/tmp/smash/uploads'
HOD_APIKEY_PATH = '/home/james/smash/hod.apikey'
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

def load_apikey():
    with open(HOD_APIKEY_PATH, 'r') as f:
        apikey = f.read()
    return apikey.rstrip("\n\r")

@app.route('/')
def hello_world():
    return render_template('index.html')

@app.route('/upload')
def upload():
    return render_template('upload.html')



def allowed_img_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_IMG_EXTENSIONS

def wait_for_async_job(async_response):
    apikey = load_apikey()
    jobid = async_response.json()['jobID']

    unfinished = True
    while unfinished:
        s = requests.get('https://api.havenondemand.com/1/job/status/{0}'.format(jobid), params={'apikey': apikey})
        status = s.json()['status']
        unfinished = True if status not in ['finished', 'failed'] else False
    return s

def do_ocr(filepath):
    apikey = load_apikey()
    params = {'apikey': apikey, 
              'job': '{ "actions": [ { "name": "ocrdocument", "version": "v1", "params": {"file": "doc", "mode": "document_photo"} } ] }' }
    files = {'doc': open(filepath, 'rb') }
    r = requests.post('https://api.havenondemand.com/1/job/', params=params, files=files)
    jobid = r.json()['jobID']
    s = wait_for_async_job(r)

    texts = []
    if s.json()['status'] == 'finished':
        for action in s.json()['actions']:
            for text_block in action['result']['text_block']:
                texts.append(text_block['text'])
    return texts

def index(filename, title, text):
    apikey = load_apikey()
    document = {'title': title, 'reference': filename, 'content': text}
    documents = [document]
    j = { 'document' : documents }
    params = {'apikey': apikey, 'index': 'smash', 'json': json.dumps(j)}
    r = requests.post('https://api.havenondemand.com/1/api/async/addtotextindex/v1/', params=params)
    status = wait_for_async_job(r)

    


@app.route('/doupload', methods=['POST'])
def do_upload():
    title = request.form['title']
    f = request.files['doc']
    if f and allowed_img_file(f.filename):
        filename = secure_filename(f.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(filepath)
        texts = do_ocr(filepath)
        os.remove(filepath)
        text = ' '.join(texts)
        index(f.filename, title, text)
        return render_template('doupload.html')

    else:
        abort(400)

@app.route('/query', methods=['GET'])
def query():
    return render_template('query_form.html')

@app.route('/doquery', methods=['POST'])
def doquery():
    apikey = load_apikey()
    querytext = request.form['querytext']
    params = {'apikey': apikey, 'text': querytext, 'indexes':'smash', 'print':'all'}
    r = requests.get('https://api.havenondemand.com/1/api/sync/querytextindex/v1', params=params)
    documents = [ {'title': d['title'], 'content': d['content']} for d in r.json()['documents'] ]
    return render_template('queryresults.html', documents=documents)

if __name__ == '__main__':
    app.run(host='0.0.0.0')

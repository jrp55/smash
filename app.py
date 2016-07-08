import argparse
import sys
import os
import os.path
import requests
import json
from flask import Flask, request, render_template, abort
from werkzeug import secure_filename

ALLOWED_IMG_EXTENSIONS = set(['tiff', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'ico', 'pbm', 'pgm', 'ppm'])
UPLOAD_FOLDER = '/tmp/smash/uploads'
HOD_APIKEY_FILENAME = 'hod.apikey'
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

def load_apikey():
    """
    Loads the HoD API key from the configured apikeys directory
    :returns: the HoD API key string
    """
    with open(os.path.join(app.config['APIKEY_DIR'], HOD_APIKEY_FILENAME), 'r') as f:
        apikey = f.read()
    return apikey.rstrip("\n\r")

@app.route('/')
def hello_world():
    """
    Implements the homepage
    """
    return render_template('index.html')

@app.route('/upload', methods=['GET'])
def upload():
    """
    Implements the upload page form
    """
    return render_template('upload.html')

def allowed_img_file(filename):
    """
    Is the image file being uploaded of an acceptable type?
    :param filename: filename of the file being uploaded
    :returns: True if the filename is acceptable, False otherwise
    """
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_IMG_EXTENSIONS

def wait_for_async_job(async_response):
    """
    Waits for an asynchronous HoD job to finish
    :param async_response: The response of an asynchronous request to HoD, obtained via the requests library
    :returns: The response of the job status call when the status is a final one, obtained via the requests library
    """
    apikey = load_apikey()
    jobid = async_response.json()['jobID']

    unfinished = True
    while unfinished:
        s = requests.get('https://api.havenondemand.com/1/job/status/{0}'.format(jobid), params={'apikey': apikey})
        status = s.json()['status']
        unfinished = True if status not in ['finished', 'failed'] else False
    return s

def do_ocr(filepath):
    """
    Does OCR on the provided filepath
    :param filepath: Path of a file to do OCR on
    :returns: All the OCR'd text from the document, concatenated into one string
    """
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

def does_index_exist(index_name):
	"""
	Checks whether a given index exists
	:param index_name: The name of the index to check for
	:returns: True if index exists, False otherwise
	"""
	apikey = load_apikey()
	params = {'apikey': apikey}
	r = requests.get('https://api.havenondemand.com/1/api/sync/listresources/v1', params=params)
	for private_resource in r.json()['private_resources']:
		if private_resource['resource'] == index_name:
			return True
	return False

def create_index(index_name):
	"""
	Creates an index with the given name
	:param index_name: The name of the index to create
	"""
	apikey = load_apikey()
	params = {'apikey': apikey, 'index': index_name, 'flavor': 'explorer'}
	r = requests.get('https://api.havenondemand.com/1/api/sync/createtextindex/v1', params=params)

def check_smash_index():
	smash_index_name = 'smashdata'
	if not does_index_exist(smash_index_name):
		create_index(smash_index_name)

def index(filename, title, text):
    """
    Indexes a document into the HoD text index
    :param filename: The name of the file represented by title and text - becomes the reference of the indexed document
    :param title: The title of the indexed document
    :param text: The content of the indexed document
    """
    apikey = load_apikey()
    document = {'title': title, 'reference': filename, 'content': text}
    documents = [document]
    j = { 'document' : documents }
    params = {'apikey': apikey, 'index': 'smash', 'json': json.dumps(j)}
    r = requests.post('https://api.havenondemand.com/1/api/async/addtotextindex/v1/', params=params)
    status = wait_for_async_job(r)

@app.route('/upload', methods=['POST'])
def do_upload():
    """
    Implements the action completed by submitting the upload form.
    Conducts OCR on the submitted image file and indexes the resulting text
    Renders a new webpage 
    """
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
    """
    Renders a webpage with the initial state of the query form
    """
    return render_template('query_form.html')

@app.route('/query', methods=['POST'])
def doquery():
    """
    Gets the query results from the submitted query via HoD and renders the results
    """
    apikey = load_apikey()
    querytext = request.form['querytext']
    params = {'apikey': apikey, 'text': querytext, 'indexes':'smash', 'print':'all'}
    r = requests.get('https://api.havenondemand.com/1/api/sync/querytextindex/v1', params=params)
    documents = [ {'title': d['title'], 'content': d['content']} for d in r.json()['documents'] ]
    return render_template('queryresults.html', documents=documents)

def configure_app(args):
    """
    Configures the app from the command line arguments
    :params args: Arguments obtained from argparse
    """
    app.config['APIKEY_DIR'] = args.apikeydir

# Let's get to work!
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run SMASH')
    parser.add_argument('--apikeydir', '-a', nargs=1, default='.apikeys')
    args = parser.parse_args()
    configure_app(args)
	check_smash_index()
    app.run(host='0.0.0.0')

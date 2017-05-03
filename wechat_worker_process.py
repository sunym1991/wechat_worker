from flask import jsonify
from flask import request

import process_message
from redmine_project.component_ini import app


@app.route('/wechat/text', methods=['POST'])
def process_text():
    success, resp = process_message.process_text(request.json)
    payload = {'success': success, 'response': resp}
    return jsonify(payload)


@app.route('/wechat/file', methods=['POST'])
def process_file():
    success, resp = process_message.process_file(request.json)
    payload = {'success': success, 'response': resp}
    return jsonify(payload)


if __name__ == '__main__':
    app.run(host='localhost', port=8999)

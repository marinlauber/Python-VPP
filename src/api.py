"""
API for calling VPPMod

"""
from flask import Flask, request, redirect, url_for, flash, jsonify
import numpy as np
import json

app = Flask(__name__)

@app.route('/api/sum/', methods=['POST'])
def makecalc():
    data = request.get_json()
    prediction = np.array2string(np.sum(data))
    return jsonify(prediction)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
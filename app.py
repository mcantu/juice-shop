from flask import Flask, jsonify
import importlib

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Juice Shop!"})

if __name__ == '__main__':
    validate_dependencies = importlib.import_module('lib.startup.validateDependenciesBasic').default
    validate_dependencies()
    server = importlib.import_module('server')
    server.start()

import argparse

from funcx.serialize import FuncXSerializer
from flask import Flask, current_app as app, jsonify, request, abort, g

app = Flask(__name__)


@app.route('/ping', methods=['GET'])
def ping():
    """ Minimal liveness test
    """
    return "pong"


def serialize_fx_inputs(*args, **kwargs):
    """Pack and serialize inputs using the funcX serializer.
    """
    fx_serializer = FuncXSerializer()
    ser_args = fx_serializer.serialize(args)
    ser_kwargs = fx_serializer.serialize(kwargs)
    payload = fx_serializer.pack_buffers([ser_args, ser_kwargs])
    return payload


@app.route('/serialize', methods=['POST'])
def serialize():
    """Serialized the inputs and return the packed buffer.
    """
    ret_package = None
    inputs = request.json
    try:
        ret_package = serialize_fx_inputs(inputs)
    except Exception as e:
        return jsonify(repr(e)), 500
    return jsonify(ret_package), 200


@app.route('/deserialize', methods=['POST'])
def deserialize():
    """Deserialize the buffer and return the result. Return the 
    stringified exception if one is raised.
    """

    fx_serializer = FuncXSerializer()
    # Return a failure message if all else fails
    ret_package = None
    try:
        inputs = request.json
        res = fx_serializer.deserialize(inputs)
        ret_package = jsonify(res)
    except Exception as e:
        print(e)
        return jsonify(repr(e)), 200
    return ret_package, 200


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default=5000,
                        help="Port at which the service will listen on")
    parser.add_argument("-d", "--debug", action='store_true',
                        help="Enables debug logging")

    args = parser.parse_args()

    try:
        print("Starting serializer!")
        app.run(host='0.0.0.0', port=int(args.port), threaded=True)
    except Exception as e:
        # This doesn't do anything
        print("Caught exception : {}".format(e))
        exit(-1)


if __name__ == '__main__':
    cli()

from flask import jsonify

class Response:
    @staticmethod
    def success(message: str):
        return jsonify({
            'code': 1,
            'message': message
        })

    @staticmethod
    def success_with_data(message: str, data: dict):
        return jsonify({
            'code': 1,
            'message': message,
            'data': data
        })

    @staticmethod
    def error(message: str):
        return jsonify({
            'code': 0,
            'message': message
        })
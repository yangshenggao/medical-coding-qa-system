"""
统一响应格式封装
所有API接口使用统一的JSON响应结构
"""
from flask import jsonify


def success(data=None, message='操作成功'):
    response = jsonify({
        'code': 200,
        'message': message,
        'data': data
    })
    response.status_code = 200
    return response


def error(message='操作失败', code=400):
    response = jsonify({
        'code': code,
        'message': message,
        'data': None
    })
    response.status_code = code
    return response


def page_response(items, total, page, page_size):
    response = jsonify({
        'code': 200,
        'message': '查询成功',
        'data': {
            'list': items,
            'total': total,
            'page': page,
            'page_size': page_size
        }
    })
    response.status_code = 200
    return response

"""
统一响应格式封装
所有API接口使用统一的JSON响应结构
"""
import logging
from flask import jsonify

logger = logging.getLogger(__name__)


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


def safe_error(user_message, exception=None, code=400):
    """
    安全错误响应：返回通用提示给用户，详细异常只记日志
    :param user_message: 面向用户的错误提示
    :param exception: 原始异常对象（仅记录日志）
    :param code: HTTP 状态码
    """
    if exception:
        logger.error(f'{user_message}: {exception}', exc_info=True)
    return error(user_message, code)


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

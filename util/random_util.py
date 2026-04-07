import string
import random

def string_random(length=6):
    """
    随机生成N位字母 + 数字的字符串
    :param length:
    :return:
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def number_random(length=6):
    """
    随机生成N位数字
    :param length:
    :return:
    """
    return ''.join(random.choices(string.digits, k=length))


def interval_number_random(start=10000, end=15000):
    """
    随机生成 指定某个区间 的一个数字
    :param start:
    :param end:
    :return:
    """
    return random.randint(start, end)
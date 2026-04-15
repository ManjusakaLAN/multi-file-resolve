import re
from pypinyin import pinyin, Style


def validate_name_string(value):
    pattern = r"^[A-Za-z_][A-Za-z0-9_]*$"
    if re.match(pattern, value) is not None:
        return value
    raise ValueError("非法输入：不能以数字开头，且只能包含字母、数字和下划线")


# 传入中文 例如： 服装设计01 转换为 -> fu_zhuang_she_ji_01 只允许字母、数字、下划线，且长度不超过128，且不能以数字开头
def convert_cn_to_pinyin(cn_word: str):
    # 取出cn_word 的所有空格
    cn_word = cn_word.replace(" ", "")

    # 如果输入全是数字，则添加前缀
    if cn_word.isdigit():
        cn_word = "num_" + cn_word

    # 中文转拼音
    result = pinyin(cn_word, style=Style.NORMAL)
    # 空格变为_
    full_pinyin = '_'.join([i[0] for i in result])

    # 如果结果仍以数字开头，添加前缀
    if full_pinyin and full_pinyin[0].isdigit():
        full_pinyin = "num_" + full_pinyin

    if len(full_pinyin) > 128:
        full_pinyin = full_pinyin[:128]

    # full_pinyin 不能以数字开头 只能包含字母、数字、下划线
    validate_name_string(full_pinyin)

    return full_pinyin

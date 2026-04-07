import base64
import binascii
import hashlib
import logging
import re
from PIL.Image import Resampling
import jwt
from core.config import settings
from core.exception.auth_exception import UserRegisterException
from core.exception.security_exception import TokenException

logger = logging.getLogger(__name__)


def valid_password(password):
    """
    校验密码是否合规
    :param password:
    :return:
    """
    # 定义正则模式
    pattern = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"
    # 匹配字符串
    if re.match(pattern, password) is not None:
        return
    raise UserRegisterException("密码必须包括数字和字母,并且长度需要大于等于8")


def hash_password(password_str, salt_byte):
    """
    进行密码加密加盐
    :param password_str:
    :param salt_byte:
    :return:
    """
    dk = hashlib.pbkdf2_hmac("sha256", password_str.encode("utf-8"), salt_byte, 10000)
    return binascii.hexlify(dk)


def compare_password(password_str, password_hashed_base64, salt_base64):
    """
    传入密码盐 进行密码对比
    :param password_str:
    :param password_hashed_base64:
    :param salt_base64:
    :return:
    """
    return hash_password(password_str, base64.b64decode(salt_base64)) == base64.b64decode(password_hashed_base64)


import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def generate_captcha_image(text: str, width=160, height=60, font_size=38):
    """
    修复 Unresolved reference 'bbox' 并优化字符间距与居中
    """
    # 1. 准备画布
    bg_color = (random.randint(240, 255), random.randint(240, 255), random.randint(240, 255))
    image = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(image)

    # 2. 加载字体
    try:
        # 生产环境建议使用绝对路径，例如 os.path.join(base_dir, "assets/arial.ttf")
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception as e:
        logger.error(f"无法加载字体: {e}")
        font = ImageFont.load_default()

    # 3. 计算槽位 (核心逻辑：平分宽度确保不重合)
    count = len(text)
    slot_width = width // count

    for i, char in enumerate(text):
        # A. 为每个字符创建独立的透明层
        # 层大小设为字体的1.5倍，确保旋转空间
        temp_size = int(font_size * 1.5)
        char_layer = Image.new('RGBA', (temp_size, temp_size), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_layer)

        # B. 获取字符的精确大小 (修复 bbox 未定义问题)
        char_bbox = font.getbbox(char)  # (left, top, right, bottom)
        c_w = char_bbox[2] - char_bbox[0]
        c_h = char_bbox[3] - char_bbox[1]

        # C. 随机深色
        char_color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))

        # D. 在临时层居中绘制字符
        # 计算在 temp_size 内部的居中坐标
        draw_x = (temp_size - c_w) // 2 - char_bbox[0]
        draw_y = (temp_size - c_h) // 2 - char_bbox[1]
        char_draw.text((draw_x, draw_y), char, fill=char_color, font=font)

        # E. 随机旋转 (歪歪扭扭的关键)
        angle = random.randint(-25, 25)
        # expand=True 会自动扩大图层以容纳旋转后的转角
        rotated = char_layer.rotate(angle, resample=Resampling.BILINEAR, expand=True)

        # F. 计算粘贴到主图的位置 (确保在槽位内居中)
        rw, rh = rotated.size

        # 槽位中心点 X
        slot_center_x = i * slot_width + (slot_width // 2)
        # 图片中心点 Y
        center_y = height // 2

        # 加入微小的随机抖动 (Jitter)，但限制在槽位宽度的 10%，保证不重合
        jitter_x = random.randint(-int(slot_width * 0.05), int(slot_width * 0.05))
        jitter_y = random.randint(-5, 5)

        paste_x = slot_center_x - (rw // 2) + jitter_x
        paste_y = center_y - (rh // 2) + jitter_y

        # 使用 rotated 作为 mask 处理透明通道
        image.paste(rotated, (paste_x, paste_y), rotated)

    # 4. 添加干扰（适量，不影响识别）
    for _ in range(3):
        line_color = (random.randint(150, 200), random.randint(150, 200), random.randint(150, 200))
        draw.line([random.randint(0, width), random.randint(0, height),
                   random.randint(0, width), random.randint(0, height)], fill=line_color, width=1)

    # 5. 最后润色：轻微平滑处理
    image = image.filter(ImageFilter.SMOOTH)

    # 保存返回
    img_bytes = BytesIO()
    image.save(img_bytes, format='PNG')
    return img_bytes.getvalue()


class PassportService:
    def __init__(self):
        self.sk = settings.TOKEN_SECRET_KEY

    def generate_token(self, payload):
        return jwt.encode(payload, self.sk, algorithm="HS256")

    def verify_token(self, token):
        try:
            return jwt.decode(token, self.sk, algorithms=["HS256"])
        except jwt.exceptions.InvalidSignatureError:
            raise TokenException("Token签名不合法")
        except jwt.exceptions.DecodeError:
            raise TokenException("非法的Token")
        except jwt.exceptions.ExpiredSignatureError:
            raise TokenException("Token已经过期")

from cryptography.fernet import Fernet

from core.config import settings


class ApiKeyCipher:
    def __init__(self, key: bytes = None):
        """
        初始化 Cipher 工具类。

        :param key: 加密/解密使用的密钥（32字节 base64 编码），若不传则生成新的密钥
        """
        self.cipher = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """
        加密 API Key

        :param plaintext: 明文 API Key
        :return: Base64 编码的密文字符串
        """
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        解密 API Key

        :param ciphertext: Base64 编码的密文字符串
        :return: 原始明文 API Key
        """
        return self.cipher.decrypt(ciphertext.encode()).decode()

    @staticmethod
    def generate_key() -> str:
        """
        生成一个新的密钥（Base64 编码字符串）
        """
        return Fernet.generate_key().decode()

cipher_client = ApiKeyCipher(settings.CIPHER_SECRET_KEY.encode())
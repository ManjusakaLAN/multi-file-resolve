from pydantic_settings import BaseSettings


class SecuritySettings(BaseSettings):
    """
    应用安全相关配置
    """
    # 密钥配置
    CIPHER_SECRET_KEY: str = "ZLRh1ct6KiAoMxpIbBAQFxUyGXlE_s2EhaUQMWXp6aQ="
    TOKEN_SECRET_KEY: str = ""

    # 令牌与登录控制
    RESET_PASSWORD_TOKEN_EXPIRY_MINUTES: int = 5
    LOGIN_ENABLED: bool = True

    # 验证码配置
    CAPTCHA_ENABLED: bool = False
    CAPTCHA_STR_LEN: int = 6
    CAPTCHA_TEXT_EXPIRE_TIME: int = 180

    class Config:
        env_file = ".env"
        extra = "ignore"


class AuthSettings(BaseSettings):
    """
    JWT 认证相关配置
    """
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_ENABLED: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"
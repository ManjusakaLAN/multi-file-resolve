# 使用官方的Python基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置非交互模式，避免安装过程中卡住
ENV DEBIAN_FRONTEND=noninteractive

# 更新源并安装 LibreOffice 以及必要的开源中文字体（防止中文乱码）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    fonts-arphic-ukai \
    fonts-arphic-uming \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 配置pip使用阿里云镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 复制依赖文件到工作目录
COPY requirements.txt requirements.txt

# 安装依赖
RUN pip install -r requirements.txt

# 复制项目文件到工作目录
COPY . .

# 暴露应用的端口
EXPOSE 9500

# 设置环境变量
#ENV FLASK_ENV=production

# 运行应用
CMD ["python","app.py"]

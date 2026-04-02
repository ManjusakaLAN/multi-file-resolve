FROM ubuntu:latest
LABEL authors="zshoyo"

ENTRYPOINT ["top", "-b"]
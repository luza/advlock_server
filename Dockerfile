FROM alpine:latest

MAINTAINER Denis Girko <denis.girko@lamoda.ru>

ENV ROOT_DIR /advlock_server

RUN apk add --no-cache python

COPY advlock_server.py $ROOT_DIR/

WORKDIR $ROOT_DIR

EXPOSE 49915

CMD ["python", "advlock_server.py", "0.0.0.0", "49915"]


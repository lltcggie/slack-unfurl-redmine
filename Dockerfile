FROM python:3.9

RUN apt-get update
RUN apt-get -y install locales && \
    localedef -f UTF-8 -i ja_JP ja_JP.UTF-8

ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8
ENV TZ JST-9
ENV TERM xterm

RUN mkdir /src
COPY src /src/

RUN pip install -r /src/requirements.txt

WORKDIR /src
ENTRYPOINT [ "python", "app.py" ]

FROM python:3.7

RUN addgroup uwsgi && useradd -g uwsgi uwsgi

WORKDIR /opt/funcx-serialization-service

COPY ./requirements.txt .

RUN pip install -r requirements.txt
RUN pip install --disable-pip-version-check uwsgi

COPY uwsgi.ini .
COPY ./funcx_serialization_service/ ./funcx_serialization_service/
COPY entrypoint.sh .

USER uwsgi
EXPOSE 5000

CMD sh entrypoint.sh


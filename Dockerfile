FROM python:3.7-alpine

RUN apk update && \
    apk add --no-cache gcc musl-dev linux-headers libffi-dev libressl-dev make g++

# Create a group and user
RUN addgroup -S uwsgi && adduser -S uwsgi -G uwsgi
RUN pip install --disable-pip-version-check uwsgi

COPY . /opt/funcx-serialization-service
WORKDIR /opt/funcx-serialization-service
RUN pip install --disable-pip-version-check -q -r ./requirements.txt
ENV PYTHONPATH "${PYTHONPATH}:/opt/funcx-serialization-service"

USER uwsgi
EXPOSE 55000-56000
EXPOSE 3031
CMD sh entrypoint.sh


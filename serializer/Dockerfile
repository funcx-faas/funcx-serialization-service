FROM funcx-web-base
WORKDIR /opt/serializer
ENV FLASK_APP service.py
ENV FLASK_RUN_HOST 0.0.0.0
COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY entrypoint.sh /entrypoint.sh
CMD sh /entrypoint.sh

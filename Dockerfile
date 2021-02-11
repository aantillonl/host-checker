FROM debian

RUN apt-get update -y && apt-get install -y python3.7 python3-pip
COPY ./src /app
RUN python3 -m pip install /app/.
COPY ./certs /certs
CMD host-metrics produce -c /app/config
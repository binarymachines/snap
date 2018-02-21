FROM python:3.6
#RUN pip install --upgrade pip
ENV PYTHONPATH=/opt/binary/snap/snap
WORKDIR /opt/binary/
COPY src/requirements.txt /opt/binary/requirements.txt
RUN pip install -r requirements.txt
RUN apt-get update
RUN apt-get install -y mysql-client
ARG SNAP_BUILD_VERSION
ENV SNAP_BUILD_VERSION="${SNAP_BUILD_VERSION}"



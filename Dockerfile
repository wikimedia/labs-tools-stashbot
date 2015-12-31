FROM debian:jessie
MAINTAINER Bryan Davis <bd808@bd808.com>

ENV CONFIG config.yaml

RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get \
     -o Dpkg::Options::='--force-confdef' \
     -o Dpkg::Options::='--force-confold' \
     -o Dpkg::Options::='--force-unsafe-io' \
     install --fix-broken --auto-remove --yes --quiet \
     python \
     python-pip \
     python-yaml \
  && DEBIAN_FRONTEND=noninteractive apt-get clean autoclean \
  && DEBIAN_FRONTEND=noninteractive apt-get autoremove --yes --purge \
  && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
  && rm -rf /var/lib/{apt,dpkg,cache,log}/

RUN ln -sf /usr/share/zoneinfo/Universal /etc/localtime

ADD . /app
RUN pip install -r /app/requirements.txt

RUN useradd --system stashbot
USER stashbot
WORKDIR /app
CMD python stashbot.py --config ${CONFIG}

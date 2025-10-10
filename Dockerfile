FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y git curl screen && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone https://github.com/monkins1010/VerusCoinMiner.git
WORKDIR /opt/VerusCoinMiner
RUN chmod +x install.sh

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]

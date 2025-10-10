FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y git cmake build-essential libssl-dev libcurl4-openssl-dev curl screen python3 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone https://github.com/VerusCoin/nheqminer.git

WORKDIR /opt/nheqminer
RUN mkdir build && cd build && cmake .. && make -j$(nproc)

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]

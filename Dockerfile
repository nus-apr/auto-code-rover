# for building auto-code-rover:latest
FROM yuntongzhang/swe-bench:latest

RUN git config --global user.email acr@nus.edu.sg
RUN git config --global user.name acr

ENV DEBIAN_FRONTEND=noninteractive
RUN apt install -y vim build-essential libssl-dev

COPY . /opt/auto-code-rover
WORKDIR /opt/auto-code-rover
RUN conda env create -f environment.yml

ENTRYPOINT [ "/bin/bash" ]

# for building auto-code-rover:latest
FROM yuntongzhang/swe-bench:latest

COPY . /opt/auto-code-rover
WORKDIR /opt/auto-code-rover
RUN conda env create -f environment.yml

ENTRYPOINT [ "/bin/bash" ]

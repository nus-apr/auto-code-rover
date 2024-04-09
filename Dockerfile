# for building auto-code-rover:latest
FROM yuntongzhang/swe-bench:latest

RUN git config --global user.email acr@nus.edu.sg
RUN git config --global user.name acr

COPY . /opt/auto-code-rover
WORKDIR /opt/auto-code-rover
RUN conda env create -f environment.yml

ENTRYPOINT [ "/bin/bash" ]

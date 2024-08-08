# for building auto-code-rover:latest
FROM yuntongzhang/swe-bench:latest

RUN git config --global user.email acr@nus.edu.sg
RUN git config --global user.name acr

ENV DEBIAN_FRONTEND=noninteractive
RUN apt update && apt install -y vim build-essential libssl-dev

COPY . /opt/auto-code-rover

WORKDIR /opt/auto-code-rover/demo_vis/front
RUN sed -i 's/\r$//' /opt/auto-code-rover/demo_vis/run.sh
RUN apt install -y curl
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
RUN apt-get install nodejs -y
RUN npm i
RUN npm run build

WORKDIR /opt/auto-code-rover
RUN conda env create -f environment.yml

EXPOSE 3000 5000
ENTRYPOINT [ "/bin/bash" ]

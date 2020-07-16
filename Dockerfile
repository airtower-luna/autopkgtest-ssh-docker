FROM debian:sid
RUN apt-get update && apt-get install -y \
    apt-utils \
    bsdextrautils \
    dpkg-dev \
    openssh-server \
    sudo \
    systemctl \
    && rm -rf /var/lib/apt/lists/*
COPY init.bash /
RUN echo LANG=C.UTF-8 >/etc/default/locale
RUN adduser --disabled-password --gecos Test,,, test && \
    echo 'test ALL = (ALL:ALL) NOPASSWD: ALL' >/etc/sudoers.d/testenv && \
    mkdir /home/test/.ssh/ && chown test:test /home/test/.ssh/
ENTRYPOINT ["/init.bash"]

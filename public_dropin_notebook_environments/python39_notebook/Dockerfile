ARG WORKDIR=/nbx
ARG AGENTDIR=/agent
ARG VENV_PATH=${WORKDIR}/.venv

ARG UNAME=nbx
ARG UID=90909
ARG GID=90909

ARG PYTHON_VERSION=39
ARG PYTHON_EXACT_VERSION=3.9.13

FROM registry.access.redhat.com/ubi8/ubi-minimal:8.7 AS base
# some globally required dependencies

ARG UNAME
ARG UID
ARG GID
ARG WORKDIR
ARG AGENTDIR
ARG VENV_PATH
ARG PYTHON_VERSION
ARG PYTHON_EXACT_VERSION

RUN microdnf update \
    && microdnf install -y python$PYTHON_VERSION-$PYTHON_EXACT_VERSION python$PYTHON_VERSION-devel-$PYTHON_EXACT_VERSION \
      gcc-8.5.0 glibc-devel-2.28 libffi-devel-3.1 graphviz-2.40.1 \
      openblas-0.3.15 python$PYTHON_VERSION-scipy shadow-utils-2:4.6 passwd-0.80 git-2.31.1 openssh-server tar-2:1.30 gzip-1.9 unzip-6.0 zip-3.0 wget-1.19.5 \
    && pip3 install -U --no-cache-dir pip==21.3.1 \
    && microdnf clean all

RUN pip3 install --no-cache-dir pip==22.3.1

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VENV_PATH=${VENV_PATH}

ENV PATH="$VENV_PATH/bin:$PATH"
ENV PYTHONPATH="/home/nbx/.ipython/extensions"

RUN python3 -m venv ${VENV_PATH}
WORKDIR ${WORKDIR}

COPY ./extensions /home/nbx/.ipython/extensions
COPY ./jupyter_kernel_gateway_config.py ./start_server.sh ${WORKDIR}/
COPY ./agent/agent.py ${WORKDIR}${AGENTDIR}/
COPY ./agent/cgroup_monitor.py ${WORKDIR}${AGENTDIR}/
COPY ./ipython_config.py /etc/ipython/

COPY ./sshd_config /etc/ssh/
RUN cp -a /etc/ssh /etc/ssh.cache && rm -rf /var/cache/apk/*
RUN mkdir /etc/authorized_keys

# Removing pip leftovers to not have trivy complain
RUN rm -rf /lib/python3.9/site-packages/pip-20.2.4.dist-info && \
    rm -rf /nbx/.venv/lib/python3.9/site-packages/pip-20.2.4.dist-info && \
    rm -rf /lib/python3.8/site-packages/pip-19.3.1.dist-info && \
    rm -rf /nbx/.venv/lib/python3.8/site-packages/pip-19.3.1.dist-info

# Custom user to run the image from

RUN groupadd -g $GID -o $UNAME && \
    useradd -l -m -u $UID -g $GID -o -s /bin/bash $UNAME

RUN chown -R $UNAME:$UNAME ${WORKDIR} ${VENV_PATH} /home/nbx /etc/ssh /etc/authorized_keys

USER $UNAME

# Jupyter Gateway port
EXPOSE 8888
# sshd port
EXPOSE 22

FROM base AS minimal
# this stage has only bare minimal of dependencies installed to optimize build time for the local development

ARG WORKDIR
ARG VENV_PATH

COPY ./dr_requirements.txt ./agent/requirements-agent.txt ${WORKDIR}/
RUN pip3 install --no-cache-dir -r ${WORKDIR}/dr_requirements.txt \
    && pip3 install --no-cache-dir -r ${WORKDIR}/requirements-agent.txt \
    && rm ${WORKDIR}/dr_requirements.txt \
    && rm ${WORKDIR}/requirements-agent.txt \
    && rm ${VENV_PATH}/share/jupyter/kernels/python3/kernel.json \
    && chmod a+x ${WORKDIR}/start_server.sh

# Monitoring agent port
EXPOSE 8889

FROM minimal AS builder
# this stage includes all data science dependencies we want to have in the kernel runtime out of the box

ARG WORKDIR
ARG VENV_PATH
ARG PYTHON_VERSION

COPY ./kernel.json ${VENV_PATH}/share/jupyter/kernels/python3/
COPY ./requirements.txt ${WORKDIR}/
RUN pip3 install --no-cache-dir -r ${WORKDIR}/requirements.txt \
  && rm ${WORKDIR}/requirements.txt

FROM base AS kernel
# this stage is what actually going to be run as kernel image and it's clean from all build junks

ARG UNAME

ARG WORKDIR

# Removing pip leftovers to not have trivy complain
RUN rm -rf /lib/python3.9/site-packages/pip-20.2.4.dist-info && \
    rm -rf /nbx/.venv/lib/python3.9/site-packages/pip-20.2.4.dist-info && \
    rm -rf /lib/python3.8/site-packages/pip-19.3.1.dist-info && \
    rm -rf /nbx/.venv/lib/python3.8/site-packages/pip-19.3.1.dist-info

RUN chown -R $UNAME:$UNAME ${WORKDIR} /home/nbx

COPY --from=builder --chown=$UNAME $WORKDIR $WORKDIR

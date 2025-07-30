FROM python:3.9

ENV http_proxy=http://proxy.query.consul:80
ENV https_proxy=http://proxy.query.consul:80

COPY product/requirements.txt .

RUN apt update && \
    apt install -y -q openssh-client snmp mariadb-client dnsutils net-tools iputils-ping nano
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /etc/ssh && \
    ssh-keygen -t rsa -b 2048 -f /etc/ssh/ssh_host_rsa_key -N "" && \
    ssh-keygen -t ecdsa -f /etc/ssh/ssh_host_ecdsa_key -N "" && \
    ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -N ""

WORKDIR /app
COPY product .

EXPOSE 5000

CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0"]

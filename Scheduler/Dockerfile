FROM python:3.9

WORKDIR /Scheduler

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        iputils-ping \
        wget \
        snmp \
        dnsutils \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --default-timeout=300 --retries=5 -r requirements.txt

COPY . .

CMD ["python", "StartScheduler.py"]
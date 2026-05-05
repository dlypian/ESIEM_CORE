FROM python:3.9

WORKDIR /Scheduler

COPY requirements.txt .

RUN pip install --default-timeout=300 --retries=5 -r requirements.txt

COPY . .

CMD ["python", "StartScheduler.py"]
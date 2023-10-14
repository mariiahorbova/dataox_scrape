FROM python:3.9.6-slim-buster

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ./requirements.txt .
RUN apt update && apt install postgresql postgresql-contrib -y
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

CMD ["python", "scrape.py"]
FROM python:3.11-slim

WORKDIR /zocalo

RUN python -m pip install --upgrade pip

COPY . .

RUN python -m pip install --no-cache-dir .

CMD ["zocalo.service"]

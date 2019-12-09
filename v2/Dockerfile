FROM python:3.7

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

COPY analysis.py /trans_analysis/

WORKDIR /trans_analysis

CMD ["python3", "./analysis.py"]

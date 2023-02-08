FROM continuumio/anaconda3
EXPOSE 80

WORKDIR /

COPY . .
RUN pip install -r requirements.txt

CMD ["python","coba.py"]
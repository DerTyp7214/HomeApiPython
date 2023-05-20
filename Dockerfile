FROM python:3.11

COPY . .
RUN ./setup.sh
CMD ["python3", "main.py"]
EXPOSE 8000
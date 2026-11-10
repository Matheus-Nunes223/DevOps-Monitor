FROM python:3.12-slim
WORKDIR /app
COPY server.py ./server.py
USER 0:0
EXPOSE 2375
HEALTHCHECK --interval=10s --timeout=3s --retries=3 CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:2375/health', timeout=2)"
ENTRYPOINT ["python", "-u", "server.py"]

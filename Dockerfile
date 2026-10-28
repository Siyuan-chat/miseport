FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --create-home miseport
COPY examples /app/examples
USER miseport
ENV MISEPORT_CATALOG=/app/examples/products.json
ENTRYPOINT ["miseport-mcp"]

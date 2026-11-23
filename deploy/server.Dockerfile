FROM python:3.12.13-slim
RUN pip install --no-cache-dir uv==0.5.11
WORKDIR /srv
COPY server/pyproject.toml server/uv.lock ./server/
RUN cd server && uv sync --frozen --no-dev
COPY contracts ./contracts
COPY config ./config
COPY server ./server
WORKDIR /srv/server
USER 65534
CMD ["uv", "run", "--no-dev", "uvicorn", "app.wiring.main:api_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

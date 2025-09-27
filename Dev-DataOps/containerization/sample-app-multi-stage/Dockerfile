# ---- Builder Stage ----
FROM python:3.7-slim AS builder

WORKDIR /app

RUN groupadd -r webservice && useradd --no-log-init -r -g webservice webservice

# Install dependencies
RUN pip install --user networkx dash plotly

# Copy application code
COPY . .

# ---- Final Stage ----
FROM python:3.7-slim

WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /app /app

# Copy installed Python packages from builder 
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

USER webservice:webservice

EXPOSE 8050

ENTRYPOINT ["python", "GraphAnalysis.py"]

CMD ["obj_dependency_data.csv"]

FROM node:20-slim

# Install git (needed to read PR diffs / clone repo history) and Python 3
# (needed to run the MCP servers under mcp/ -- storage_server.py and
# retrieval_server.py -- see docs/mcp-configuration.md)
RUN apt-get update && apt-get install -y git curl python3 python3-pip && rm -rf /var/lib/apt/lists/*

# Retrieval server uses scikit-learn (TF-IDF + cosine similarity) for
# local, offline vector search -- no external embeddings API required.
RUN pip install --break-system-packages --no-cache-dir scikit-learn numpy

# Install the agent runtime CLI (Claude Code)
RUN npm install -g @anthropic-ai/claude-code

# Create a non-root user so the agent isn't running as root inside the container
RUN useradd -m agent
USER agent

WORKDIR /workspace

# Only copy in what the agent needs to see - not your whole machine
COPY --chown=agent:agent . /workspace

# Credentials are NOT baked in here - they get passed in at runtime
# via environment variables (see docker-compose.yml / .env.example)

CMD ["bash"]
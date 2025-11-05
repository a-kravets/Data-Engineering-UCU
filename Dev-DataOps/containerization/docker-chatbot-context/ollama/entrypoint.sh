#!/bin/sh
set -e

# Start Ollama in background
ollama serve &
sleep 8

# Pull the model (only if missing)
ollama pull smollm3 || true

# Keep Ollama in the foreground
wait

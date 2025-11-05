FROM ollama/ollama:0.3.14

# Preload the model
RUN ollama pull gemma:2b

EXPOSE 11434
ENTRYPOINT ["ollama", "serve"]
#ENTRYPOINT ["bash", "-c", "ollama serve & sleep 5 && ollama pull tinyllama && wait"]

# Python-based LLM Chatbot

It's a simple LLM-powered Python-based chatbot

* [Streamlit.io](https://streamlit.io/) is used for Web UI
* Web UI is exposed on port 8050
* The application communicates with LLM-model ([ai/smollm2](https://hub.docker.com/r/ai/smollm2))

## How to ran it

* `git clone https://github.com/a-kravets/Data-Engineering-UCU/tree/main/Dev-DataOps/containerization/docker-chatbot`
* cd inside the folder
* `docker compose up --build`
* The Web UI will be at `http://localhost:8050/`

## Useful docs & articles

* [How to Build, Run, and Package AI Models Locally with Docker Model Runner](https://www.docker.com/blog/how-to-build-run-and-package-ai-models-locally-with-docker-model-runner/)
* [Define AI Models in Docker Compose applications](https://docs.docker.com/ai/compose/models-and-compose/)
* [Running AI Models with Docker Compose](https://dev.to/pradumnasaraf/running-ai-models-with-docker-compose-27ng)
* [Run AI Models Locally with Ease Using Docker Model Runner](https://thelearningfellow.medium.com/run-ai-models-locally-with-ease-using-docker-model-runner-b7a3a43a32c8)
* [DMR REST API](https://docs.docker.com/ai/model-runner/api-reference/#request-from-the-host-using-tcp)
* [Docker Model Runner](https://docs.docker.com/ai/model-runner/)
* [ai/smollm2](https://hub.docker.com/r/ai/smollm2)
* [Define AI Models in Docker Compose applications](https://docs.docker.com/ai/compose/models-and-compose/#short-syntax)

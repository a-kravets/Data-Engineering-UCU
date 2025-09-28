# docker-network

Send data from service_a to service_b:

* `curl -X POST http://localhost:8001/send -H "Content-Type: application/json" -d "{\"hi\":\"from A\"}"`

Check data on service_b:

* `curl http://localhost:8002/data`

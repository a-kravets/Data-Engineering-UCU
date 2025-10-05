## Useful resources

* [Kubernetes Overview](https://kubernetes.io/docs/concepts/overview/)
* [Kubernetes Cluster Architecture](https://kubernetes.io/docs/concepts/architecture/)
* [GKE cluster architecture](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-architecture)
* [Kubernetes Pods](https://kubernetes.io/docs/concepts/workloads/pods/)

# Google Kubernetes Engine 

## Create a GKE cluster and deploy application

**Set a default compute zone**

Your [compute zone](https://cloud.google.com/compute/docs/regions-zones/#available) is an approximate regional location in which your clusters and their resources live. For example, `us-central1-a` is a zone in the `us-central1` region.

* Set the default compute region: `gcloud config set compute/region us-east1`
* Set the default compute zone: `gcloud config set compute/zone us-east1-c`

**Create a GKE cluster**

A cluster consists of at least one cluster master machine and multiple worker machines called nodes. Nodes are Compute Engine virtual machine (VM) instances that run the Kubernetes processes necessary to make them part of the cluster.

* `gcloud container clusters create --machine-type=e2-medium --zone=us-east1-c lab-cluster`

**Get authentication credentials for the cluster**

After creating your cluster, you need authentication credentials to interact with it.

* `gcloud container clusters get-credentials lab-cluster`

**Deploy an application to the cluster**

Kubernetes provides the Deployment object for deploying stateless applications like web servers. Service objects define rules and load balancing for accessing your application from the internet.

To create a new Deployment `hello-server` from the `hello-app` container image, run the following `kubectl create` command:

* `kubectl create deployment hello-server --image=gcr.io/google-samples/hello-app:1.0`

This Kubernetes command creates a deployment object that represents `hello-server`. In this case, `--image` specifies a container image to deploy. The command pulls the example image from a Container Registry bucket. `gcr.io/google-samples/hello-app:1.0` indicates the specific image version to pull. If a version is not specified, the latest version is used.

**(!)** Note that Kubernetes automatically creates Pods for us. By default, 1 Pod is created unless you specify `--replicas=N`

To create a Kubernetes Service, which is a Kubernetes resource that lets you expose your application to external traffic, run the following kubectl expose command:

* `kubectl expose deployment hello-server --type=LoadBalancer --port 8080`

  * `--port` specifies the port that the container exposes
  * `type="LoadBalancer"` creates a Compute Engine load balancer for your container

To inspect the hello-server Service, run kubectl get: `kubectl get service`

To view the application from your web browser, open a new tab and enter the following address, replacing `[EXTERNAL IP]` with the `EXTERNAL-IP` for `hello-server` (we can find it by runnin `kubectl get service`).

* `http://[EXTERNAL-IP]:8080`

**Delete the cluster**

To delete the cluster, run the following command:

* `gcloud container clusters delete lab-cluster`

text










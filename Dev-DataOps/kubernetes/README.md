## Contents:

* [Push the Docker image to the Artifact Registry](https://github.com/a-kravets/Data-Engineering-UCU/tree/main/Dev-DataOps/kubernetes#push-the-docker-image-to-the-artifact-registry)
* [Intro: Create a GKE cluster and deploy application](https://github.com/a-kravets/Data-Engineering-UCU/tree/main/Dev-DataOps/kubernetes#intro-create-a-gke-cluster-and-deploy-application)
* [Orchestrating the Cloud with Kubernetes (Pods and Services)](https://github.com/a-kravets/Data-Engineering-UCU/tree/main/Dev-DataOps/kubernetes#orchestrating-the-cloud-with-kubernetes-pods-and-services)
* [Building containers with DockerFile and Cloud Build](https://github.com/a-kravets/Data-Engineering-UCU/tree/main/Dev-DataOps/kubernetes#building-containers-with-dockerfile-and-cloud-build)

## Useful resources

* [Kubernetes Overview](https://kubernetes.io/docs/concepts/overview/)
* [Kubernetes Cluster Architecture](https://kubernetes.io/docs/concepts/architecture/)
* [GKE cluster architecture](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-architecture)
* [Kubernetes Pods](https://kubernetes.io/docs/concepts/workloads/pods/)

# Google Kubernetes Engine 

## Push the Docker image to the Artifact Registry

o push images to your private registry hosted by Artifact Registry, you need to tag the images with a registry name. The format is `<regional-repository>-docker.pkg.dev/my-project/my-repo/my-image`.

For instance:

* `docker push europe-west4-docker.pkg.dev/qwiklabs-gcp-02-8869fab4a91d/valkyrie-docker-repo/valkyrie-app:v0.0.1`

See [containerization](https://github.com/a-kravets/Data-Engineering-UCU/tree/main/Dev-DataOps/containerization) for more details

## Intro: Create a GKE cluster and deploy application

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

**kubectl**

`kubectl` stores its configuration in a file in the home directory in a hidden folder `$HOME/.kube/config`

It contains the list of clusters and the credentials that will be attached to each of those clusters.

To view the configuration, either open the config file or use the `kubectl` command `config view`.

`kubectl` command syntax: `kubectl` [command] [type] [name] [flags]

For instance, `kubectl create deployment hello-server --image=gcr.io/google-samples/hello-app:1.0`

**Deploy an application to the cluster**

Kubernetes provides the Deployment object for deploying stateless applications like web servers. Service objects define rules and load balancing for accessing your application from the internet.

To create a new Deployment `hello-server` from the `hello-app` container image, run the following `kubectl create` command:

* `kubectl create deployment hello-server --image=gcr.io/google-samples/hello-app:1.0`

This Kubernetes command creates a deployment object that represents `hello-server`. In this case, `--image` specifies a container image to deploy. The command pulls the example image from a Container Registry bucket. `gcr.io/google-samples/hello-app:1.0` indicates the specific image version to pull. If a version is not specified, the latest version is used.

**(!)** Note that Kubernetes Deployment automatically creates Pods for us. By default, 1 Pod is created unless you specify `--replicas=N`

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

## Orchestrating the Cloud with Kubernetes (Pods and Services)

**Google Kubernetes Engine Zone & Cluster**

* `gcloud config set compute/zone us-east1-c`
* `gcloud container clusters create io --zone us-east1-c`

You are automatically authenticated to your cluster upon creation. If you lose connection to your Cloud Shell for any reason, run the `gcloud container clusters get-credentials io` command to re-authenticate.

**Create Pods**

A Pod is basically the K8s replacement for "a computer": two containers in the same Pod can talk to each other via localhost, while two containers in different Pods cannot, even if they get run on the same computer.

Pods represent and hold a collection of one or more containers. Generally, if you have multiple containers with a hard dependency on each other, you package the containers inside a single Pod.

Pods also have [Volumes](https://kubernetes.io/docs/concepts/storage/volumes/). Volumes are data disks that live as long as the Pods live, and can be used by the containers in that Pod. Pods provide a shared namespace for their contents which means that the two containers inside of our example Pod can communicate with each other, and they also share the attached volumes.

Pods also share a network namespace. This means that there is one IP Address per Pod.

Kubernetes Deployment automatically creates Pods for us. By default, 1 Pod is created unless you specify `--replicas=N`

Pods can be created using Pod configuration files. `cat pods/fortune-app.yaml`

```
apiVersion: v1  
kind: Pod  
metadata:  
  name: fortune-app  
  labels:  
    app: fortune-app  
spec:  
  containers:  
    - name: fortune-app  
      image: "us-central1-docker.pkg.dev/qwiklabs-resources/spl-lab-apps/fortune-app:1.0.0"  
      ports:  
        - name: http  
          containerPort: 8080  
      resources:  
        limits:  
          cpu: 0.2  
          memory: "20Mi"
```
**Create the fortune-app Pod using kubectl:**

* `kubectl create -f pods/fortune-app.yaml`

**Examine your Pods. Use the kubectl get pods command to list all Pods running in the default namespace:**

* `kubectl get pods`

**Once the Pod is running, use the kubectl describe command to get more information about the fortune-app Pod:**

* `kubectl describe pods fortune-app`

**Create a Service**

Pods aren't meant to be persistent. They can be stopped or started for many reasons, like failed liveness or readiness checks, which leads to a problem:

What happens if you want to communicate with a set of Pods? When they get restarted they might have a different IP address.

That's where [Services](https://kubernetes.io/docs/concepts/services-networking/service/) come in. Services provide stable endpoints for Pods.

Services use labels to determine what Pods they operate on. If Pods have the correct labels, they are automatically picked up and exposed by our services.

The level of access a service provides to a set of Pods depends on the Service's type. Currently there are three types:

* ClusterIP (internal) is the default type. This Service is only visible inside the cluster.
* NodePort gives each node in the cluster an externally accessible IP.
* LoadBalancer adds a load balancer from the cloud provider which forwards traffic from the Service to Nodes within it.

Secure fortune-app service configuration file:

* `cat pods/secure-fortune.yaml`

Create the secure-fortune Pods and their configuration data:

```
kubectl create secret generic tls-certs --from-file tls/  
kubectl create configmap nginx-proxy-conf --from-file nginx/proxy.conf  
kubectl create -f pods/secure-fortune.yaml
```

`fortune-app` service configuration file:

```
kind: Service  
apiVersion: v1  
metadata:  
  name: "fortune-app"  
spec:  
  selector:  
    app: "fortune-app"  
    secure: "enabled"  
  ports:  
    - protocol: "TCP"  
      port: 443  
      targetPort: 443  
      nodePort: 31000  
  type: NodePort
```

Use the kubectl create command to create the fortune-app service from the configuration file:

* `kubectl create -f services/fortune-app.yaml`

Use the gcloud compute firewall-rules command to allow traffic to the fortune-app service on the exposed nodeport:

* `gcloud compute firewall-rules create allow-fortune-nodeport --allow tcp:31000`

**Add labels to Pods**

Use the kubectl label command to add the missing secure=enabled label to the secure-fortune Pod

```
kubectl label pods secure-fortune 'secure=enabled'
kubectl get pods secure-fortune --show-labels
```

**Create Deployments***

The goal of this lab is to get you ready for scaling and managing containers in production. That's where Deployments come in. Deployments are a declarative way to ensure that the number of Pods running is equal to the desired number of Pods, specified by the user.

The main benefit of [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#what-is-a-deployment) is in abstracting away the low level details of managing Pods. Behind the scenes Deployments use [Replica Sets](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/) to manage starting and stopping the Pods. If Pods need to be updated or scaled, the Deployment will handle that. Deployment also handles restarting Pods if they happen to go down for some reason.

You're going to break the fortune-app app into three separate pieces:

* `auth` - Generates JWT tokens for authenticated users.
* `fortune` - Serves fortunes to authenticated users.
* `frontend` - Routes traffic to the auth and fortune services.

You are ready to create Deployments, one for each service. Afterwards, you'll define internal services for the auth and fortune Deployments and an external service for the frontend Deployment. Once finished, you'll be able to interact with the microservices just like with the monolith, only now each piece is able to be scaled and deployed, independently!

Get started by examining the auth Deployment configuration file:

`cat deployments/auth.yaml`

```
apiVersion: apps/v1  
kind: Deployment  
metadata:  
  name: auth  
spec:  
  selector:  
    matchLabels:  
      app: auth  
  replicas: 1  
  template:  
    metadata:  
      labels:  
        app: auth  
    spec:  
      containers:  
        - name: auth  
          image: "us-central1-docker.pkg.dev/qwiklabs-resources/spl-lab-apps/auth-service:1.0.0"  
          ports:  
            - name: http  
              containerPort: 8080
```

Create Deployment object:

* `kubectl create -f deployments/auth.yaml`

Create a service for your auth Deployment

* `kubectl create -f services/auth.yaml`

Create and expose the fortune Deployment:

```
kubectl create -f deployments/fortune-service.yaml
kubectl create -f services/fortune-service.yaml
```

And one more time to create and expose the frontend Deployment

```
kubectl create configmap nginx-frontend-conf --from-file=nginx/frontend.conf  
kubectl create -f deployments/frontend.yaml  
kubectl create -f services/frontend.yaml
```
## Building containers with DockerFile and [Cloud Build](https://cloud.google.com/build/docs/overview)

Cloud Build is a build automation service. It:

* Compiles source code.
* Builds container images.
* Runs tests or scripts.
* Pushes the built image to a registry.

**When to use Cloud Build:**

* To automate building containers whenever code changes (CI/CD pipelines).
* To ensure reproducible, isolated builds that don’t depend on your laptop.
* To integrate testing or security scanning before deploying.
* You run it before deploying to Kubernetes.

Cloud Build prepares the artifacts (like the container image) that Deployments will run.










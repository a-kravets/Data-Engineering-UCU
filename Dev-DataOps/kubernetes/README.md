## Useful resources

* [Kubernetes Overview](https://kubernetes.io/docs/concepts/overview/)
* [Kubernetes Cluster Architecture](https://kubernetes.io/docs/concepts/architecture/)
* [GKE cluster architecture](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-architecture)

## Create a GKE cluster and deploy application

**Set a default compute zone**

Your [compute zone](https://cloud.google.com/compute/docs/regions-zones/#available) is an approximate regional location in which your clusters and their resources live. For example, `us-central1-a` is a zone in the `us-central1` region.

* Set the default compute region: `gcloud config set compute/region "REGION"`
* Set the default compute zone: `gcloud config set compute/zone "ZONE"`

**Create a GKE cluster**

A cluster consists of at least one cluster master machine and multiple worker machines called nodes. Nodes are Compute Engine virtual machine (VM) instances that run the Kubernetes processes necessary to make them part of the cluster.

* `gcloud container clusters create --machine-type=e2-medium --zone=ZONE lab-cluster`

**Get authentication credentials for the cluster**

After creating your cluster, you need authentication credentials to interact with it.

* `gcloud container clusters get-credentials lab-cluster`

**Deploy an application to the cluster**

text



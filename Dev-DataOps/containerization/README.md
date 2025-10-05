# containerization

## Image build

* `docker build -t name/repo_name:tag .`

## Start container

* `docker run -d image_name`

* `-d` detached
* `-it` interactive mode

## Data sharing via volume

Create a volume:

*  `docker volume create my-volume`

Run container with the volume:

*  `docker run -v volume_name:mount_point_in_container image_name`

For testing purpose we may create a file:

*  `cd mount_point_in_container`
*  `echo 'hello' > 'hello.txt'`

Run second container with the same volume volume:

*  `docker run -v volume_name:mount_point_in_container image_name`

Check if the file is indeed in place:

*  `cd mount_point_in_container`
*  `ls` 

## Push an image to the [Google Artifact Registry](https://cloud.google.com/artifact-registry/docs)

To push images to your private registry hosted by Artifact Registry, you need to tag the images with a registry name. The format is `<regional-repository>-docker.pkg.dev/my-project/my-repo/my-image`

Create the target Docker repository

You must create a repository before you can push any images to it. Pushing an image can't trigger creation of a repository and the Cloud Build service account does not have permissions to create repositories.

There are two way to do this:

* Using Cloud Console
* Using CLI (`gcloud artifacts repositories create my-repository --repository-format=docker --location=europe-west4 --description="Docker repository"`)

Configure authentication

* `gcloud auth configure-docker <regional-repository>-docker.pkg.dev` (for example, `gcloud auth configure-docker europe-west4-docker.pkg.dev`)

Docker build

* `docker build -t europe-west4-docker.pkg.dev/my-project/my-repo/my-image .`

Push the image to Artifact Registry

* `docker push europe-west4-docker.pkg.dev/my-project/my-repo/my-image`

Docker run

* `docker run -p 8080:80 -d europe-west4-docker.pkg.dev/my-project/my-repo/my-image`

# containerization

## Image build

* `docker build -t name/repo_name:tag .`

## Run image

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

# Get Latest Tag

Script that retrieves the latest release tag of a given repository.

## Usage

Docker Engine must be running beforehand as [regclient/regctl](https://hub.docker.com/r/regclient/regctl) is used to search for tags.

Parameters:
* ``repository_url`` - URL to repository. Defaults to dockerhub if full URL path is not specified
* ``repository_tag`` - (Optional) Currently used repository version. If specified, only tags of the same type will be considered.

```commandline
python .\get_last_tag.py <repository_url> <repository_tag>
```

get_last_tag.py can be called within a bash script. Only the latest tag is printed to sys.stdout, all logs are logged into sys.stderr.

## 
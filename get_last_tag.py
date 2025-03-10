"""
Script that retrieves the latest release tag of a given repository.
"""

import re
import sys
import logging
import docker
import semantic_version

from docker.errors import ContainerError, DockerException

logger = logging.getLogger('get_last_tag')
logging.basicConfig(
    stream=sys.stderr,
    encoding='utf-8',
    level=logging.DEBUG
)

def _get_repository_tags(repo_url: str, tag_regex: re.Pattern) -> tuple:
    """
    Run regclient CLI to download repository's tags. (https://hub.docker.com/r/regclient/regctl)

    :param repo_url: (str) URL to repository. Defaults to dockerhub if not full URL path is provided.
    :param tag_regex: (re.Pattern) Regex pattern
    :return:
    """

    client = docker.from_env()
    try:
        tags = client.containers.run(
            image='regclient/regctl:latest',
            command=f'tag ls {repo_url}',
            volumes=['regctl-conf:/home/appuser/.regctl/'],
            tty=True,
            auto_remove=True
        )
    except ContainerError as container_err:
        raise SystemExit(f'Could not connect to the repository: {repo_url}') from container_err
    except DockerException as docker_err:
        raise SystemExit('Could not run a contaier. Check if docker engine is running.') from docker_err

    tags = [tag for tag in tags.decode("utf-8").split('\r\n') if tag_regex.match(tag)]
    if not tags:
        raise SystemExit(f'No relevant tags downloaded for repository: {repo_url}')
    return tuple(tags)


def _create_regex_from_current_tag(current_tag: str = None) -> re.Pattern:
    """
    Create regex dynamically based on provided current_tag.

    :param current_tag: (str, Optional) Currently used repository version. If not provided default regex is used
    :return: (re.Pattern) Regex pattern
    """

    regex_pattern = '^'

    if not current_tag:
        regex_pattern = (r'^[v]{0,1}(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-'
                         r'(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d'
                         r'*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0'
                         r'-9a-zA-Z-]+)*))?$')
        logger.debug('Searching tags based on default semantic versioning regex')
    else:
        for char in current_tag:
            if char.isdigit():
                if regex_pattern[-1] != ')':
                    regex_pattern += r'(0|[1-9]\d*)'
            elif char == '.':
                regex_pattern += '[.]'
            else:
                regex_pattern += char
        regex_pattern += '$'
        logger.debug(f'Searching tags based on regex: {regex_pattern}')
    return re.compile(regex_pattern)


def _find_latest_tag(tags: tuple, current_version: str = None) -> str:
    """
    Compare tags and return the latest one.
    Note: Versions not convertable to Semantic Versioning 2.0.0 will not be compared.

    :param tags: (tuple) Downloaded tags
    :param current_version: (str, Optional) Currently used tag
    :return: (str, None) Latest tag
    """

    def convert_to_sem_ver(_tag: str) -> semantic_version.Version | None:
        sem_ver_conv = None
        _tag = _tag[1:] if _tag[0] == 'v' else _tag
        try:
            sem_ver_conv = semantic_version.Version(_tag)
        except ValueError:
            try:
                sem_ver_conv = semantic_version.Version.coerce(_tag)
            except ValueError:
                logger.warning(f'Incomparable tag version: {_tag}')
        return sem_ver_conv

    current_version = current_version if current_version else '0.0.0'
    latest_tag, latest_version = current_version, convert_to_sem_ver(current_version)

    for tag in tags:
        tag_ver = convert_to_sem_ver(tag)
        if not tag_ver:
            continue
        if tag_ver > latest_version:
            latest_tag, latest_version = tag, tag_ver

    if latest_version == convert_to_sem_ver('0.0.0'):
        raise SystemExit('Latest tag not retrieved, obtained tags cannot be compared')

    return latest_tag



def get_last_tag(repo_public_url: str, current_tag: str = None) -> str | None:
    """
    Interface for obtaining repository latest tag (version).

    Note: If current_tag is provided only tags of the same type will be retrieved.
          In other case only versions compliant with Semantic Versioning 2.0.0 will be retrieved.

    :param repo_public_url: (str) URL to repository. Defaults to dockerhub if full URL path is not provided.
    :param current_tag: (str, Optional) Currently used repository version
    :return: (str, None) Latest available version
    """

    logger.info(f'Downloading latest version for repository: {repo_public_url}')
    version_regex = _create_regex_from_current_tag(current_tag=current_tag)
    tags = _get_repository_tags(repo_public_url, version_regex)
    latest_tag = _find_latest_tag(tags, current_tag)
    logger.info(f'Latest tag found: {latest_tag}')
    return latest_tag


if __name__ == '__main__':

    last_tag = get_last_tag(*sys.argv[1:3])
    print(last_tag)

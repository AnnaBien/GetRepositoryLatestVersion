import re
import semver
import docker

from docker.errors import ContainerError


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
    except ContainerError:
        raise SystemExit(f'Could not connect to the repository: {repo_url}')

    print(tags)
    tags = [tag for tag in tags.decode("utf-8").split('\r\n') if tag_regex.match(tag)]
    if not tags:
        raise SystemExit(f'No relevant tags downloaded for repository: {repo_url}')
    return tuple(tags)


def _create_regex_from_current_version(current_version: str = None) -> re.Pattern:
    """
    Create regex dynamically based on provided current tag.

    :param current_version: (str, Optional) Currently used repository version. If not provided default regex is used
    :return: (re.Pattern) Regex pattern
    """

    regex_pattern = '^'

    if not current_version:
        regex_pattern = (r'^[v]{0,1}(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-'
                         r'(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d'
                         r'*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0'
                         r'-9a-zA-Z-]+)*))?$')
        print(f'Searching tags based on default semantic versioning regex')
    else:
        for char in current_version:
            if char.isdigit():
                if regex_pattern[-1] != ')':
                    regex_pattern += r'(0|[1-9]\d*)'
            else:
                regex_pattern += char
        regex_pattern += '$'
        print(f'Searching tags based on regex: {regex_pattern}')
    return re.compile(regex_pattern)


def _find_latest_version(tags: tuple, current_version: str = None) -> str | None:
    """
    Compare versions between tags following MAJOR.MINOR.PATCH style.

    :param tags: (tuple) Downloaded tags
    :param current_version: (str, Optional) Currently used tag
    :return: (str, None) Latest tag
    """

    try:
        latest_tag = semver.Version.parse(current_version)
    except (ValueError, TypeError):
        latest_tag = semver.Version.parse('0.0.0')

    for tag in tags:
        try:
            curr_tag = semver.Version.parse(tag[1:] if tag[0] == 'v' else tag)
        except ValueError:
            print(f'Incomparable tag version: {tag}')
            continue
        if curr_tag.major > latest_tag.major:
            latest_tag = curr_tag
        elif curr_tag.major == latest_tag.major:
            if curr_tag.minor > latest_tag.minor:
                latest_tag = curr_tag
            elif curr_tag.minor == latest_tag.minor:
                if curr_tag.patch > latest_tag.patch:
                    latest_tag = curr_tag
                elif not curr_tag.prerelease:
                    latest_tag = curr_tag

    if latest_tag == semver.Version.parse('0.0.0'):
        print('Latest tag not retrieved, obtained tags cannot be compared')
        return current_version
    print(f'Latest release found: {latest_tag}')
    return str(latest_tag)


def get_last_tag(repo_public_url: str, current_version: str = None) -> str | None:
    """
    Interface for obtaining repository latest tag (version).

    :param repo_public_url: (str) URL to repository. Defaults to dockerhub if not full URL path is provided.
    :param current_version: (str, Optional) Currently used repository version
    :return: (str, None) Latest available version
    """

    print(f'Downloading latest version for repository: {repo_public_url}')
    version_regex = _create_regex_from_current_version(current_version=current_version)
    tags = _get_repository_tags(repo_public_url, version_regex)
    return _find_latest_version(tags, current_version)

# GitLab Artifact Cleanup

## Overview

`gitlab-artifact-cleanup` is a tool to clean up old artifacts from GitLab CI/CD jobs.

## Motivation

GitLab has a built-in feature to delete artifacts from jobs that are older than a given threshold. However, there are
cases when this auto-cleanup does not apply:

- If auto-cleanup was disabled before, all artifacts that were created before auto-cleanup activation won't be deleted.
- Job artifacts which belong to the latest commit of a branch or to a tag are not deleted.
- If project pipelines keep failing constantly, all artifacts of the last successful pipeline will be kept.
- Artifacts that are selected to be kept manually (with the web UI for example) will be kept forever.

In these cases, artifacts can only be deleted manually in the web UI or with the GitLab API. `gitlab-artifact-cleanup`
uses the GitLab API and provides a convenient command line tool and a simple Python high-level API to clean up old
artifacts.

## Installation

### From PyPI

`gitlab-artifact-cleanup` is available as a [Python package on PyPI](https://pypi.org/project/gitlab-artifact-cleanup/).
Install it using `pip` or [`pipx`](https://pipx.pypa.io/stable/):

```bash
python3 -m pip install gitlab-artifact-cleanup
```

or

```bash
pipx install gitlab-artifact-cleanup
```

The tool requires at least Python 3.9.

### AUR

For Arch and its derivates, `gitlab-artifact-cleanup` is also available in the
[AUR](https://aur.archlinux.org/packages/gitlab-artifact-cleanup/) and can be installed with any AUR helper, for example
`yay`:

```bash
yay -S gitlab-artifact-cleanup
```

## Usage

### Command line tool

Run

```bash
gitlab-artifact-cleanup --write-default-config
```

to create an initial configuration file at `~/.gitlab-artifact-cleanuprc`. Then, open the web page of your GitLab
instance and navigate to *User Settings* -> *Access Tokens*. Create a new token with the `api` scope and copy its
contents into the newly created configuration file (`access_token`) and set the `url` of your GitLab server if you are
not using `gitlab.com`.

Now, run

```bash
gitlab-artifact-cleanup --dry-run [project_name]
```

to scan a given project for artifacts to be deleted. With `--dry-run` the tool only creates a list of artifacts that
would be deleted but does not apply any changes to the GitLab project. By default, all artifacts older than 7 days will
be erased that are not associated to any branch or tag. These default values can be adjusted on the command line or in
the configuration file (run with `--help` to get list of all options and their possible values).

Omit `--dry-run` to apply the changes and delete the artifacts.

### Python API

You can import a `Gitlab` class from the `gitlab_artifact_cleanup` package to clean up artifacts from a Python script.
This is a simple example:

```python
#!/usr/bin/env python3

from gitlab_artifact_cleanup import Gitlab


def main():
    gitlab = Gitlab(
        "https://gitlab.com",
        "my-very-secret-access-token",
        dry_run=True,
    )
    gitlab.delete_old_artifacts(
        "username/myproject",
        days_to_keep=14,
        keep_artifacts_of_latest_branch_commit=True,
        keep_artifacts_of_tags=True,
        delete_logs=False,
    )


if __name__ == "__main__":
    main()
```

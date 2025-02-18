import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from gitlab import Gitlab as _Gitlab
from gitlab.v4.objects import ProjectJob as GitlabProjectJob

from .util import human_size

logger = logging.getLogger(__name__)


class Gitlab:
    def __init__(self, gitlab_url: str, access_token: str, dry_run: bool = False):
        self._gitlab = _Gitlab(gitlab_url, private_token=access_token)
        self._dry_run = dry_run

    def delete_old_artifacts(
        self,
        repository_path_with_namespace: str,
        days_to_keep: int,
        keep_artifacts_of_latest_branch_commit: bool = True,
        keep_artifacts_of_tags: bool = True,
        delete_logs: bool = False,
    ) -> None:
        keep_timedelta = timedelta(days=days_to_keep)
        now = datetime.now(timezone.utc)
        project = self._gitlab.projects.get(repository_path_with_namespace)
        logger.info('Scanning project "%s"...', project.path_with_namespace)
        branches_to_hash = {branch.name: branch.commit["id"] for branch in project.branches.list(iterator=True)}
        tags_to_hash = {tag.name: tag.commit["id"] for tag in project.tags.list(iterator=True)}

        artifacts_size_total = 0
        cleaned_job_count = 0
        for job in project.jobs.list(iterator=True):
            job_branch = (
                job.ref if job.commit is not None and job.commit["id"] == branches_to_hash.get(job.ref) else None
            )
            job_tag = job.ref if job.commit is not None and job.commit["id"] == tags_to_hash.get(job.ref) else None
            if (
                job._attrs["artifacts"] is None
                or (
                    not delete_logs
                    and not any(artifact["file_type"] == "archive" for artifact in job._attrs["artifacts"])
                )
                or (keep_artifacts_of_latest_branch_commit and job_branch is not None)
                or (keep_artifacts_of_tags and job_tag is not None)
                or (now - datetime.fromisoformat(job.created_at) <= keep_timedelta)
            ):
                continue

            artifacts_size = sum(
                artifact["size"] if artifact["size"] is not None else 0
                for artifact in job._attrs["artifacts"]
                if delete_logs or artifact["file_type"] == "archive"
            )
            job_created_at_localtime = datetime.fromisoformat(job.created_at).astimezone().strftime("%Y-%m-%d %H:%M:%S")

            def job_description(
                job: GitlabProjectJob,
                job_created_at_localtime: str,
                artifacts_size: int,
                job_branch: Optional[str],
                job_tag: Optional[str],
            ) -> str:
                description = (
                    f'job "{job.id}", created at "{job_created_at_localtime}", size "{human_size(artifacts_size)}"'
                )
                if job_branch is not None and job_tag is not None:
                    description += f', linked to branch "{job_branch}" and tag "{job_tag}"'
                elif job_branch is not None:
                    description += f', linked to branch "{job_branch}"'
                elif job_tag is not None:
                    description += f', linked to tag "{job_tag}"'
                else:
                    description += ", dangling"
                return description

            if delete_logs:
                if not self._dry_run:
                    job.erase()
                    logger.info(
                        "Deleted artifacts and log of "
                        + job_description(job, job_created_at_localtime, artifacts_size, job_branch, job_tag)
                    )
                else:
                    logger.info(
                        "Would delete artifacts and log of "
                        + job_description(job, job_created_at_localtime, artifacts_size, job_branch, job_tag)
                    )
            else:
                if not self._dry_run:
                    job.delete_artifacts()
                    logger.info(
                        "Deleted artifacts of "
                        + job_description(job, job_created_at_localtime, artifacts_size, job_branch, job_tag)
                    )
                else:
                    logger.info(
                        "Would delete artifacts of "
                        + job_description(job, job_created_at_localtime, artifacts_size, job_branch, job_tag)
                    )
            cleaned_job_count += 1
            artifacts_size_total += artifacts_size
        if cleaned_job_count > 0:
            logger.info(
                'Found "%d" old dangling jobs, with "%s" of attached artifacts in total.',
                cleaned_job_count,
                human_size(artifacts_size_total),
            )
        else:
            logger.info("Found no old dangling jobs with attached artifacts.")

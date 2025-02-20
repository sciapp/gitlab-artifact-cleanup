import argparse
import getpass
import logging
import os
import sys
from textwrap import dedent
from typing import Optional

from gitlab.exceptions import GitlabAuthenticationError, GitlabListError
from yacl import setup_colored_exceptions, setup_colored_stderr_logging

from . import __version__
from .artifact_cleanup import Gitlab, ProjectGetError
from .config import CONFIG_FILEPATH, KEEP_ARTIFACTS_CHOICES, Config, KeepArtifacts, Verbosity, config

logger = logging.getLogger(__name__)


def get_argumentparser() -> argparse.ArgumentParser:
    def add_bool_argument(
        parser: argparse.ArgumentParser,
        short_name: Optional[str],
        long_name: str,
        help: str,
    ) -> None:
        normalized_long_name = long_name.replace("-", "_")
        group = parser.add_mutually_exclusive_group()
        flag_names = ["--" + long_name]
        if short_name is not None:
            flag_names.insert(0, "-" + short_name)
        group.add_argument(
            *flag_names,
            default=getattr(config, normalized_long_name),
            dest=normalized_long_name,
            action="store_true",
            help=help + f' (default: "{getattr(config, normalized_long_name)}")',
        )
        flag_names = ["--no-" + long_name]
        if short_name is not None:
            flag_names.insert(0, "-" + short_name.upper())
        group.add_argument(
            *flag_names,
            default=not getattr(config, normalized_long_name),
            dest=normalized_long_name,
            action="store_false",
            help="don't " + help[:1].lower() + help[1:] + ' (default: "%(default)s")',
        )

    parser = argparse.ArgumentParser(
        description=dedent(
            f"""\
            %(prog)s is a utility to clean up old artifacts and CI jobs from GitLab.
            Default values for command line options are taken from the config file at \"{CONFIG_FILEPATH}\""""
        ),
    )
    parser.add_argument(
        "repository_paths",
        action="store",
        nargs="*",
        default=config.repository_paths,
        help=(
            'the paths to the repositories to clean up (for example: "examples/ci-docker-in-docker", '
            f'default: "{config.repository_paths}")'
        ),
    )
    parser.add_argument(
        "-a",
        "--always-keep",
        action="store",
        choices=KEEP_ARTIFACTS_CHOICES,
        default=config.always_keep.name.lower(),
        dest="always_keep",
        help=f'artifacts which must always be kept regardless of age (default: "{config.always_keep.name.lower()}")',
    )
    parser.add_argument(
        "-k",
        "--days-to-keep",
        action="store",
        default=config.days_to_keep,
        dest="days_to_keep",
        type=int,
        help=f'number of days artifacts will always be kept (default: "{config.days_to_keep}")',
    )
    add_bool_argument(
        parser,
        "l",
        "delete-logs",
        help="delete jobs completely",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="only show what would be done",
    )
    parser.add_argument(
        "-u",
        "--gitlab-url",
        action="store",
        default=config.gitlab_url,
        dest="gitlab_url",
        help=f'the URL of the GitLab server (default: "{config.gitlab_url}")',
    )
    parser.add_argument(
        "-V",
        "--version",
        action="store_true",
        dest="print_version",
        help="print the version number and exit",
    )
    parser.add_argument(
        "-w",
        "--write-default-config",
        action="store_true",
        dest="write_default_config",
        help=f'create a configuration file with default values (config filepath: "{CONFIG_FILEPATH}")',
    )
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        dest="quiet",
        help=f'be quiet (default: "{config.verbosity is Verbosity.QUIET}")',
    )
    verbosity_group.add_argument(
        "--error",
        action="store_true",
        dest="error",
        help=f'print error messages (default: "{config.verbosity is Verbosity.ERROR}")',
    )
    verbosity_group.add_argument(
        "--warn",
        action="store_true",
        dest="warn",
        help=f'print warning and error messages (default: "{config.verbosity is Verbosity.WARN}")',
    )
    verbosity_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        dest="verbose",
        help=f'be verbose (default: "{config.verbosity is Verbosity.VERBOSE}")',
    )
    verbosity_group.add_argument(
        "--debug",
        action="store_true",
        dest="debug",
        help=f'print debug messages (default: "{config.verbosity is Verbosity.DEBUG}")',
    )
    return parser


def parse_arguments() -> argparse.Namespace:
    parser = get_argumentparser()
    args = parser.parse_args()

    if args.print_version:
        return args

    args.verbosity_level = (
        Verbosity.QUIET
        if args.quiet
        else (
            Verbosity.ERROR
            if args.error
            else (
                Verbosity.WARN
                if args.warn
                else Verbosity.VERBOSE if args.verbose else Verbosity.DEBUG if args.debug else config.verbosity
            )
        )
    )
    if args.write_default_config:
        return args

    if not args.repository_paths:
        raise argparse.ArgumentError(None, "No repository path is given.")

    if args.days_to_keep < 0:
        raise argparse.ArgumentError(None, "The number of days to keep must be positive.")

    args.always_keep = KeepArtifacts[args.always_keep.upper()]

    args.gitlab_access_token = config.gitlab_access_token
    if args.gitlab_access_token is None:
        if sys.stdin.isatty():
            args.gitlab_access_token = getpass.getpass(prompt="GitLab Login Token: ")
        else:
            args.gitlab_access_token = sys.stdin.readline().strip()
        if not args.gitlab_access_token:
            raise argparse.ArgumentError(None, "No GitLab login token is given.")

    return args


def setup_stderr_logging(verbosity_level: Verbosity) -> None:
    if verbosity_level is Verbosity.QUIET:
        logging.getLogger().handlers = []
    elif verbosity_level is Verbosity.WARN:
        logging.basicConfig(level=logging.WARNING)
    elif verbosity_level is Verbosity.VERBOSE:
        logging.basicConfig(level=logging.INFO)
    elif verbosity_level is Verbosity.DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    else:
        raise NotImplementedError(f'The verbosity level "{verbosity_level}" is not implemented')
    if verbosity_level is not Verbosity.QUIET:
        setup_colored_stderr_logging(format_string="[%(levelname)s] %(message)s")


def handle_clean_artifacts(args: argparse.Namespace) -> None:
    gitlab = Gitlab(args.gitlab_url, args.gitlab_access_token, args.dry_run)
    gitlab.delete_old_artifacts(
        args.repository_paths,
        days_to_keep=args.days_to_keep,
        keep_artifacts_of_latest_branch_commit=(
            args.always_keep in (KeepArtifacts.BRANCH_AND_TAG_ARTIFACTS, KeepArtifacts.BRANCH_ARTIFACTS)
        ),
        keep_artifacts_of_tags=(
            args.always_keep in (KeepArtifacts.BRANCH_AND_TAG_ARTIFACTS, KeepArtifacts.TAG_ARTIFACTS)
        ),
        delete_logs=args.delete_logs,
    )


def main() -> None:
    expected_exceptions = (
        argparse.ArgumentError,
        GitlabAuthenticationError,
        GitlabListError,
        ProjectGetError,
    )
    try:
        args = parse_arguments()
        if args.print_version:
            print(f"{os.path.basename(sys.argv[0])}, version {__version__}")
            sys.exit(0)
        setup_colored_exceptions(True)
        setup_stderr_logging(args.verbosity_level)
        if args.write_default_config:
            Config.write_default_config()
            logger.info('Wrote a default config file to "%s"', CONFIG_FILEPATH)
            sys.exit(0)
        handle_clean_artifacts(args)
    except expected_exceptions as e:
        logger.error(str(e))
        if "args" in locals() and args.verbosity_level is Verbosity.DEBUG:
            raise e
        for i, exception_class in enumerate(expected_exceptions, start=3):
            if isinstance(e, exception_class):
                sys.exit(i)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    sys.exit(0)

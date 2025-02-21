"""The package init module makes convenience imports available for API users."""

from ._version import __version__, __version_info__
from .artifact_cleanup import Gitlab

__author__ = "Ingo Meyer"
__email__ = "i.meyer@fz-juelich.de"
__copyright__ = "Copyright © 2025 Forschungszentrum Jülich GmbH. All rights reserved."
__license__ = "MIT"

__all__ = (
    "Gitlab",
    "__author__",
    "__copyright__",
    "__email__",
    "__license__",
    "__version__",
    "__version_info__",
)

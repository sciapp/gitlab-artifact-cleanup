"""This module provides utility functions."""


def human_size(size_in_bytes: int) -> str:
    """
    Convert a given size in bytes to a human readable format like "1.2 MiB".

    :param size_in_bytes: The size in bytes to convert
    :return: A human readable size as a string
    """
    units = ("B", "KiB", "MiB", "GiB", "TiB")

    converted_size = float(size_in_bytes)
    for unit in units[:-1]:
        if converted_size < 1024:
            return f"{converted_size:.2f} {unit}"
        converted_size /= 1024

    return f"{converted_size:.2f} {units[-1]}"

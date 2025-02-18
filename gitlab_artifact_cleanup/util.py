def human_size(size_in_bytes: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")

    converted_size = float(size_in_bytes)
    for unit in units[:-1]:
        if converted_size < 1024:
            return f"{converted_size:.2f} {unit}"
        converted_size /= 1024

    return f"{converted_size:.2f} {units[-1]}"

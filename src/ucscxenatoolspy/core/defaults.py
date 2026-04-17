"""Default UCSC Xena host URLs and name mappings."""

# Host URL → short name mapping
# Mirrors R's .xena_hosts
DEFAULT_HOSTS: dict[str, str] = {
    "https://ucscpublic.xenahubs.net": "publicHub",
    "https://tcga.xenahubs.net": "tcgaHub",
    "https://gdc.xenahubs.net": "gdcHub",
    "https://icgc.xenahubs.net": "icgcHub",
    "https://toil.xenahubs.net": "toilHub",
    "https://pancanatlas.xenahubs.net": "pancanAtlasHub",
    "https://xena.treehouse.gi.ucsc.edu:443": "treehouseHub",
    "https://pcawg.xenahubs.net": "pcawgHub",
    "https://atacseq.xenahubs.net": "atacseqHub",
    "https://previewsinglecell.xenahubs.net": "singlecellHub",
    "https://kidsfirst.xenahubs.net": "kidsfirstHub",
    "https://tdi.xenahubs.net": "tdiHub",
}

# Reverse mapping: short name → URL
HOST_NAME_TO_URL: dict[str, str] = {v: k for k, v in DEFAULT_HOSTS.items()}


def xena_default_hosts(host_name: str | None = None) -> list[str] | str:
    """Return default Xena host URLs or a specific host URL by name.

    Args:
        host_name: Optional short name (e.g. "tcgaHub"). If given,
            returns the corresponding URL.

    Returns:
        List of all default host URLs, or a single URL if host_name is given.

    Raises:
        KeyError: If host_name is not a valid host name.
    """
    if host_name is None:
        return list(DEFAULT_HOSTS.keys())
    return HOST_NAME_TO_URL[host_name]

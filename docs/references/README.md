# Literature Foundation

## Purpose

This directory defines the repository-facing bibliography and the mapping between literature, model components, parameters, data products, and validation. Zotero remains the source of record for the personal literature library.

## Files

- `references.bib` — curated repository bibliography. It contains the bibliographic union of the two Zotero exports, with local machine paths removed.
- `literature_matrix.md` — working literature-to-model matrix and metadata audit.
- `work_references.bib` — local working copy with Zotero PDF paths is intentionally **not** part of the repository.

## Bibliography policy

The repository bibliography must be reproducible on another machine. Zotero `file` fields containing local storage paths are therefore excluded from `references.bib`; they remain useful in the private `work_references.bib` copy for locating PDFs.

No bibliographic metadata should be invented merely to complete a record. DOI, publisher, journal, volume, pages, year and official URLs are preferred when available. Duplicate records are resolved by bibliographic identity, not by citation-key similarity alone.

The current curated bibliography contains **137 unique records**: 126 retained records from the original 127-record collection after removing one incomplete duplicate, plus 11 references verified as required by the current model documentation and implementation.

## Current model references

The Stage 10 modernization currently relies most directly on literature covering:

- solar geometry and radiation: Spencer (1971);
- atmospheric thermodynamics and ice saturation: Murphy & Koop (2005);
- seawater freezing point: Fofonoff & Millard (1983), with Gill (1982) as supporting oceanographic reference;
- ocean-side heat transfer: Eckert & Drake (1959), with the important caveat that the implemented flat-plate correlation is an approximation for iceberg geometry;
- iceberg basal melt: Weeks & Campbell (1973), FitzMaurice & Stern (2018), and related iceberg studies;
- ice-ocean thermodynamic parameterization: Holland & Jenkins (1999), Jenkins et al. (2010);
- iceberg dynamics/thermodynamics and coupled modelling: Bigg et al. (1997), Martin & Adcroft (2010), NEMO-ICB literature;
- observational and laboratory context: Cenedese & Straneo (2023), FitzMaurice et al. (2018), and the user's regional/observational sources.

## Data provenance

The model uses external products whose exact version and acquisition metadata must be retained with each experiment: ERA5, EN4, IBCAO V5.2, OSI-SAF sea-ice concentration CDR v3.1, and C3S CS2SMOS sea-ice thickness L4 combined v1.1. Dataset citations are tracked separately from the physical-equation bibliography.

## Status

This foundation is documentation-only. It does not change the production Fortran physics. Stage 10.6.1 remains classified **B — PASS WITH LIMITATIONS**.
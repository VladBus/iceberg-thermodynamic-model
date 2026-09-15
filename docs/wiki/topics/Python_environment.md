# Python environment

## Conda environment

Name:
iceberg-thermodynamic-model

Location:
/home/vlad/miniconda3/envs/iceberg-thermodynamic-model

Create (direct dependencies only):
conda env create -f environment.yml

Or manually:
conda create -n iceberg-thermodynamic-model python=3.12
conda install -n iceberg-thermodynamic-model -c conda-forge cdsapi xarray netCDF4 numpy pandas matplotlib

Activate:
conda activate iceberg-thermodynamic-model

Verify:
which python
python --version

## Direct dependencies (see environment.yml / requirements.txt)

- python=3.12
- cdsapi (ERA5 download via CDS API)
- xarray (NetCDF analysis)
- netCDF4 (NetCDF I/O)
- numpy
- pandas
- matplotlib (plotting)

No `file://` build paths and no transitive freeze: conda resolves transitive
dependencies automatically.

## Boundaries

Python is used for data acquisition, analysis and visualization ONLY.
Python does NOT perform model-grid interpolation, EOS, wind-stress physics,
momentum, or viscosity — those belong to the Fortran model.

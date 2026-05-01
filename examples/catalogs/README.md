# Catalogs

A catalog is a provider that needs to be explicitly added, and then will expose multiple different functions for an agent.
Let's first prepare some snakemake data:

```bash
wget https://github.com/snakemake/snakemake-tutorial-data/archive/v5.4.5.tar.gz
tar --wildcards -xf v5.4.5.tar.gz --strip 1 "*/data"
```

Setup your conda:

```bash
conda config --add channels defaults
conda config --add channels bioconda
conda config --add channels conda-forge
conda config --set channel_priority strict
pip install snakemake-wrapper-utils
```

Export envars so the snakemake catalog tools know EXACTLY where the data is (read only) and where to write (should be an empty directory for read/write)

```bash
mkdir -p ./workdir
export RESOURCE_SECRETARY_SNAKEMAKE_WORKDIR=$(pwd)/workdir
export RESOURCE_SECRETARY_SNAKEMAKE_INPUT=$(pwd)/data
```

```bash
mcpserver start --config ./snakemake.yaml --dual --port 8089
```

And now run fractale (and export needed tokens):

```bash
fractale run --database json ./plan.yaml
```

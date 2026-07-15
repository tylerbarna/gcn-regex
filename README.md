Validation and analysis of regular expressions for GCN event type feature

The main file of interest is `analysis.ipynb`. Most of the other scripts are various helper tools -- These include keeping parity between the PR's javascript regex doct and this repo's Python regex dict, downloading new circulars from the archive, and packing/unpacking the local copy archive that is version controlled in this repo. Some of these helper tools require internet connection, but most should be fault tolerant enough that the notebook will run without access to the internet.

On initial download, the notebook will populate the archive folder with json files contained in the tarball folder. On subsequent runs, it will only update the archive folder with new circulars retrieved from the archive and will repack the tarball folder.

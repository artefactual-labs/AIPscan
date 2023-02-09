# Fetch script

The fetch script is a command-line tool that allows a subset of a storage
service's packages to be fetched by AIPscan (rather than all of them at once).
When using the script the storage service's list of packages is grouped into
"pages" with each "page" containing a number of packages (specified by a
command-line argument).

So, for example, packages on a storage service with 150 packages on it could be
fetched by fetching three pages of 50 packages. Likewise if the storage service
has anything from 101 to 149 packages on it it could also be fetched by
fetching three pages of 50 packages.


## Cached package list

A storage service's list of packages is downloaded by the script and is cached
so paging will remain consistent between script runs. The cache of a particular
cached list of packages is identified by a "session identifier". A session
identifer is specified by whoever runs the script and can be any alphanumeric
identifier without spaces or special characters. It's used to name the
directory in which fetch-related files are created.

Below is what the directory structure would end up looking like if the session
identifier "someidentifier" was used, showing where the `packages.json` file,
containing the list of a storage service's packages, would be put.

    AIPscan/Aggregator/downloads/someidentifier
    ├── mets
    │   └── batch
    └── packages
        └── packages.json

**NOTE:** Each run of the script will generate a new fetch job database entry.
These individual fetch jobs shouldn't be deleted, via the AIPscan web UI,
until all fetch jobs (for each "page") have run. Otherwise the cached list of
packages will be deleted and the package list will have to be downloaded again.


## Running the script

The script should be run using the same Linux user used to run AIPscan, should
be run using the same virtual environment, and should be run from the root of
the AIPscan source code directory.

Example server commands needed to run:

1. `sudo su <Linux user name used to run AIPscan>`
2. `bash` # optional, for a normal command prompt
3. `cd /path/to/AIPscan/virtualenv`
4. `source bin/activate` # activate Python virtual environment
5. `cd /path/to/AIPscan`
6. `python3 bin/fetch_aips.py <options, see below>`

Example script run (fetching the first page of 50 packages from storage server ID 1):

    $ python3 bin/fetch_aips.py -s 1 -i someidentifier -p 1 -n 50

Example script run of the same using long form command-line options:

    $ python3 bin/fetch_aips.py --ss-id=1 --session-id=someidentifier --page=1 --packages-per-page=50

**NOTE:** Logging can be done to a file using the `-l` or `--log-file` command-line option. For example:

    $ python3 bin/fetch_aips.py -s 1 -i someidentifier -p 1 -n 50 -l "/tmp/somefetchjob.log"

# smashrating
Generate historical skill ratings based on offline tournament performances


### Dev environment

A postgresql-11 VM can be provisioned with the Vagrantfile included in `resources\pgsql_vagrant`.

The root user credentials are `postgres`/`POSTGRES`. It comes with an empty database called `vagrant` with 
the user `vagrant`/`vagrant` as the owner.

It uses the default port and can be connected to via `localhost:5432`.

There are scripts in `resources\scripts` for one-time tasks.
# Collecting Netlab Usage Data

It would be great to know how people use _netlab_; currently, we can only guess as we get little feedback and zero hard data.

We could start collecting usage data locally and kindly ask users to share it if they feel so inclined. The usage data would be collected in the `~/.netlab/usage.yml` file, containing sets of counters for **modules**, **devices**, **providers**, and **plugins**.

Each set of counters would be a dictionary; the keys would be individual objects, and the values would be composite counters -- dictionaries containing:

* **count** -- the number of times the object has been used
* **max** -- the maximum number of objects in a lab topology
* **avg** -- the average number of objects used in a lab topology (using exponential decay)
* **update** -- the last time the counter has been updated

Finally, we would need a number of **timestamps**:

* **start** -- the first time the usage file was updated
* **upload** -- the last time the usage file was uploaded

The user could inspect the usage data with **netlab usage show**, reset it with **netlab usage reset**, and upload it with **netlab usage upload**.

While it's relatively easy to implement the data collection part, the infrastructure supporting the uploads remains a mystery.

## Option A - separate GitHub project ```netlab_usage```
One option is to use GitHub for collecting usage data: Using a separate repo, Netlab would push and commit the usage file to a location under that repo.
Security wise, this would require an access token with limited write permissions (hence the separate repo - not sure if we could restrict access well enough within 1 repo)

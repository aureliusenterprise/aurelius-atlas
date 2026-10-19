# Aurelius Atlas

**Data governance made simple.** Aurelius Atlas is an open-source data governance solution that
enables business users to find, understand, and trust their data without waiting on IT: discover
data assets and their context in seconds, see who is accountable for them and whether they are fit
for purpose, follow the journey and transformations of data across systems, and keep sensitive
information in line with regulations such as GDPR.

It is one all-in-one data catalogue, designed to be business-user-friendly, meeting the demands of
modern distributed data environments.

This repository builds the new engine behind that product: a Python re-implementation of
[Apache Atlas](https://atlas.apache.org) that keeps the Atlas 2.4.0 REST API and the Atlas dashboard,
with Elasticsearch 9 as the only backend instead of JanusGraph, HBase and Solr — so the catalogue is
far easier to run and cheaper to operate. The original Java Atlas is converted in small, reviewed
increments, each proven against the Atlas 2.4.0 source code, so the clients, integrations, and
dashboards organisations rely on keep working exactly as they do today.

Start with the [User Guide](user-guide/index.md) for what the catalogue does for your organisation,
the [Conversion roadmap](architecture/conversion/index.md) for plan and status, the
[Architecture](architecture/index.md) overview for the system as it will stand, and the
[Contributor Guide](contributor-guide/index.md) to set up your machine.

The [User Guide](user-guide/index.md) is intentionally short: until the conversion is complete, the
[Apache Atlas documentation](https://atlas.apache.org/2.4.0/index.html) describes the behaviour this
system reproduces, and every intended difference is listed in
[Deviations from Apache Atlas](architecture/conversion/deviations.md).

## About the team

This project is maintained by the Aurelius Enterprise team. Please feel free to reach out if you have any questions,
need assistance, or would like to contribute.

[<img src="https://github.com/wombach.png" alt="Andreas Wombacher" title="Andreas Wombacher" width="64">](mailto:andreas.wombacher@aureliusenterprise.com)
[<img src="https://github.com/thijs-franck.png" alt="Thijs Franck" title="Thijs Franck" width="64">](mailto:thijs.franck@aureliusenterprise.com)
[<img src="https://github.com/matjgora.png" alt="Mateusz Gora" title="Mateusz Gora" width="64">](mailto:mateusz.gora@aureliusenterprise.com)
[<img src="https://github.com/mthomas-aurelius.png" alt="Michalis Thomas" title="Michalis Thomas" width="64">](mailto:michalis.thomas@aureliusenterprise.com)
[<img src="https://github.com/snikolaev.png" alt="Sem Nikolaev" title="Sem Nikolaev" width="64">](mailto:sem.nikolaev@aureliusenterprise.com)

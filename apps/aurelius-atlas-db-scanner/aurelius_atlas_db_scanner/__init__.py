"""The relational database scanner: one batch scan of one database into the catalogue (13.3).

The app reflects a live relational database through SQLAlchemy Core — schemas, tables,
columns, primary keys, foreign keys — and registers the m4i tree it finds: one System,
one Collection per schema, one Dataset per table, one Field per column, and one Process
per foreign-key column pair. It writes the whole tree through the catalogue server as
its own service identity. See ``specs/13-3-relational-database-scanner/spec.md`` for the
rules (DBS-01..12).
"""

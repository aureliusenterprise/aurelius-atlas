"""The Kafka cluster scanner: one batch scan of a broker's topics into the catalogue (13.1).

The app ports the legacy platform's Kafka scanner (``apps/m4i-data-dictionary-io``,
``SOURCE=kafka``) into a standalone job: list the broker's external topics, read each one's
schema from the Schema Registry or infer it from the topic's own messages, and write the
System/Collection/Dataset/Field tree through the catalogue server as the job's own service
identity. See ``specs/13-1-kafka-cluster-scanner/spec.md`` for the rules (KSC-01..10).
"""

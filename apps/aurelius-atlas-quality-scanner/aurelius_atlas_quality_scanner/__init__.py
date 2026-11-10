"""The Aurelius Atlas quality scanner: one batch run of the catalogue's quality rules.

The job reads the ACTIVE :class:`m4i_data_quality <aurelius_atlas_quality.rule.DqRule>` rules of the
catalogue, finds each rule's datasets, reads each dataset's extract through a reader
(:mod:`aurelius_atlas_quality_scanner.sources`), scores the rules with ``aurelius-atlas-quality``,
and writes the scores back as ``m4i_dq_score`` entities (12.2, DQS-01).
"""

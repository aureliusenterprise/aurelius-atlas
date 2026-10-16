# Data Quality

Data quality encompasses accuracy, completeness, consistency, timeliness, and validity of data across the organization.

## Quality Dimensions

| Dimension | Question | Example |
| --- | --- | --- |
| **Accuracy** | Is the data correct? | Customer email addresses are valid |
| **Completeness** | Is all expected data present? | No null values in required fields |
| **Consistency** | Is the data consistent across systems? | Same customer ID in CRM and billing |
| **Timeliness** | Is the data current? | Sales data updated within 1 hour |
| **Validity** | Does the data conform to rules? | Dates are in valid format |

## Root-Cause Analysis with Lineage

When data quality issues are detected, the lineage graph helps trace the problem back to its source. See [Using the Lineage Graph](<https://aureliusenterprise.github.io/main/architecture/data-governance/data-lineage/lineage-visualization/index.md>) for guidance on root-cause analysis.

## Monitoring

Dynamic lineage events provide runtime visibility into data processing, including record counts and failure indicators. See [Dynamic Lineage Events](<https://aureliusenterprise.github.io/main/architecture/data-governance/data-lineage/lineage-dynamic-events/index.md>) for details.

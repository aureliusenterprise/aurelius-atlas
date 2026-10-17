# Deviations from Apache Atlas

Every behaviour of Aurelius Atlas that a client could observe and that differs from Apache Atlas 2.4.0 ([ADR 046](<https://aureliusenterprise.github.io/phase1-1.1-typedef-models/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)). The parity report links each tolerated difference to its entry here; a difference without an entry is a defect.

| \# | Area | Apache Atlas behaviour | Aurelius Atlas behaviour | Reason | Increment |
| --- | --- | --- | --- | --- | --- |
| DV-01 | Notifications | Publishes entity changes to Kafka; consumes hook messages | Not supported | Out of scope ([ADR 050](<https://aureliusenterprise.github.io/phase1-1.1-typedef-models/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>)) | 0.1 |
| DV-02 | Authorization | Ranger or simple authorizer | Simple authorizer only | Out of scope; Ranger needs its own server | 0.1 |
| DV-03 | Admin | `version` names Apache Atlas 2.4.0 and its build revision | Names Aurelius Atlas, its release and its revision | A client must be able to tell which implementation answers | 0.5 |
| DV-04 | Authentication | Every endpoint except `admin/status` needs a login; the session reports the user, groups and permissions | Until 6.1, no endpoint needs a login; the session reports no user, no groups and no entity permissions | Authentication arrives in 6.1; removed then | 0.5 |
| DV-05 | Admin | The session's `timezones` are Java's `TimeZone.getAvailableIDs()` | The IANA time zone ids of the server's tz database, sorted | Java's list includes legacy three-letter ids the IANA database does not have | 0.5 |

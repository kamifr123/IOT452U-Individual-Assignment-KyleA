# Digital ID Platform

A console-based backend system implementing a federated Digital ID management platform.
Built for the IOT452U Software Engineering Tools and Techniques module.

## GitHub Repository

https://github.qmul.ac.uk/YOUR-USERNAME/IOT452U-Individual-Assignment

## System Structure

```
digital_id_system/
├── models/
│   └── digital_id.py          # DigitalID entity and IDStatus enum
├── services/
│   ├── identity_manager.py    # Identity creation, updates, status changes
│   └── identity_consumer.py   # Verification and lookup for organisations
├── auth/
│   └── authorisation.py       # Organisation types and permission enforcement
├── audit/
│   └── audit_log.py           # In-memory log of all key system actions
├── tests/
│   ├── test_identity_manager.py
│   └── test_identity_consumer.py
├── main.py                    # Console demo covering all key scenarios
└── .github/workflows/ci.yml   # GitHub Actions CI configuration
```

### Digital ID Model
Each Digital ID has immutable attributes (`national_id`, `date_of_birth`) that cannot
be changed after creation, and mutable attributes (`name`, `address`, `email`) that
the central authority may update. Status transitions (ACTIVE, SUSPENDED, REVOKED)
are validated and deterministic.

### Identity Management
Identity creation, attribute updates, and status changes are restricted exclusively
to the central authority. All operations are validated before execution and recorded
in the audit log. Revoked identities cannot be updated or reactivated.

### Identity Consumption
Verification and lookup are handled separately from management, enforcing the distinct
capability boundary required by the system. Three verification types are supported:

- Basic (employers, banks): returns valid/not valid only, no additional attributes exposed
- Tax authority: confirms identity is active and was not suspended during a reporting period
- Driving licence: confirms identity is active and has no temporary restriction in place
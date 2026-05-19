# Digital ID Platform

A console-based backend system implementing a federated Digital ID management platform.
Built for the IOT452U Software Engineering Tools and Techniques module.

## GitHub Repository

Public: https://github.com/kamifr123/IOT452U-Individual-Assignment-KyleA
Private QMUL: https://github.qmul.ac.uk/ec25720/IOT452U-Individual-Assignment.git

> Important: The QMUL GitHub runner did not work for this submission, so CI validation is performed on the public repository using a public GitHub Actions PR runner.

## Assessment Context

This project is the final individual coursework for IOT452U. It focuses on:
- Digital ID lifecycle management and consumption
- Clear architecture and separation of responsibilities
- Automated unit testing and continuous integration
- Traceable development through version control

## Repository Structure

```
.
├── audit/
│   └── audit_log.py
├── auth/
│   └── authorisation.py
├── models/
│   └── digital_id.py
├── services/
│   ├── identity_consumer.py
│   └── identity_manager.py
├── tests/
│   ├── test_identity_consumer.py
│   └── test_identity_manager.py
├── conftest.py
├── main.py
└── .github/workflows/ci.yml
```

## System Overview

- `models/digital_id.py`: DigitalID entity, immutable field rules, and status enum.
- `services/identity_manager.py`: creation, update, and status change operations for the central authority.
- `services/identity_consumer.py`: verification and lookup logic for authorised consumers.
- `auth/authorisation.py`: role-based access enforcement for management and consumption.
- `audit/audit_log.py`: in-memory audit trail for core operations.
- `main.py`: console demo showing core workflows and example behaviour.
- `conftest.py`: configures `PYTHONPATH` for tests and CI imports.

## Key Behaviour

- Central authority only can create IDs, update permitted fields, and change status.
- Consumers perform verification and lookup separately from management.
- Immutable fields such as `national_id` and `date_of_birth` cannot be changed after creation.
- Revoked identities cannot be updated or reactivated.
- Operations behave deterministically and handle repeated requests consistently.

## Running the System

```bash
python3 main.py
```

## Running Tests

```bash
pip3 install pytest
pytest tests/ -v
```

The test suite covers identity creation, duplicate handling, immutable field enforcement, status transitions, idempotency, authorisation rules, and multiple verification scenarios.

## Continuous Integration

The GitHub Actions workflow at `.github/workflows/ci.yml` installs Python 3.11, installs `pytest`, and runs `pytest tests/ -v`.
The workflow is triggered on push and pull request events.

## Public CI Runner Note

The QMUL GitHub runner could not be used successfully for this submission. CI is therefore validated using the public repository and a public GitHub Actions runner.

## Design Decisions

- Management and consumption are separated into distinct services, matching the assessment requirement that these are distinct capabilities.
- Authorisation is centralised for consistent permission enforcement.
- The project uses an in-memory model to keep the system focused on behaviour and structure rather than infrastructure.
- The code is structured to make system behaviour clear through readable implementation and automated tests.

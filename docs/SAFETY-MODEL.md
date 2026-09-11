# Safety Model

HP Server Recovery is designed around a fail-closed recovery boundary.

## Required principles

- Recovery targets must be explicitly identified and validated.
- Recovery sources must not overlap targets.
- Realtest source mounts must be read-only.
- System and data targets must be distinct.
- Protected paths must be explicitly bound.
- Allowed and forbidden hostnames must be explicitly bound for isolated realtests.
- The production Docker socket is not an acceptable isolated runtime.
- Published container ports in isolated tests are loopback-only.
- Destructive steps require an exact confirmation phrase.
- Cleanup failures prevent a run from being reported as complete.
- Resume must not replay already completed destructive steps.
- Secret-bearing values must not persist in state, reports or command audit data.

## No permissive fallback

Missing target identity, missing sentinel binding, changed source identity, unexpected Compose services, mutable image references or unsafe path relationships cause the operation to stop.

The software must not reinterpret a failed safety check as permission to continue with defaults.

## Synthetic public fixtures

The public repository uses synthetic hostnames, devices, image digests and recovery data. These fixtures exist to validate safety behavior without publishing a real deployment.

## Production use

The current repository is a pre-release framework and test reference. Production recovery requires an independently reviewed, environment-specific binding and restore procedure.

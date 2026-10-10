# K58 Phase 29 – Full-App Certification – PASS

Stand: 2026-10-10

## Ergebnis

Phase 29 ist vollständig real getestet, root-abgenommen und in den K58-Recovery-Vertrag integriert.

- Full-App Realtest: PASS
- Full-App Start Certificate v1: PASS
- Phase29 Report Binding: PASS
- Capture Contract Reuse: PASS
- Full-App Scope Binding: PASS
- Paperless Process Roles: PASS
- Database Integrity: PASS
- Certificate Sidecar: PASS
- Canonical Root Regression: 1330/1330 PASS
- USB Manifest Final: PASS
- Runtime Cleanup / Socket Absence: PASS
- K58 Phase29 Integration Root Acceptance: PASS

## Zertifizierter Scope

- Immich: Stock API + Microservices im normalen Server-Prozessumfang.
- Paperless: Stock `/init` mit Webserver, Celery Worker, Celery Beat/Scheduler und Document Consumer.
- Kein externes Netzwerk.
- Pre-/Post-Queue-Gates und Datenbank-/Schema-Integrität bleiben Bestandteil des fail-closed Vertrags.

## Fehlerkette und Korrekturen

### V1

Capture, Isolation, Image-Binding, PostgreSQL-Restore und Pre-Start-Queue bestanden. Der Stock-Start scheiterte an der Redis-URL für Paperless. Für den Stock-Init-Pfad ist `unix://` erforderlich; Paperless übersetzt diesen Wert intern passend für Celery.

### V2

Nach Korrektur der Redis-URL wurde Paperless real gesund gestartet. Der Zertifizierungslauf scheiterte jedoch bei der Prozessrollenprüfung. Ursache war nicht Paperless, sondern die Docker-Top-Abfrage: Docker Engine 29 verlangt ein PID-Feld im `ps`-Output. Die Abfrage `docker top <cid> -eo args` ist daher ungeeignet.

### V3

Die Prozessrollenprüfung verwendet `docker top <cid> -eo pid,args`. Nach einem rein speicherplatzbedingten Vorabstopp wurde Fail-Evidence verlustfrei auf das separate Evidence-Target verschoben und der vollständige Lauf erneut gestartet.

Der anschließende Realtest bestand vollständig einschließlich:

- Capture Binding
- Isolation
- Image Binding
- PostgreSQL Restore
- Pre-Start Queue Gate
- Stock Apps Started
- Post-Start Queue Gate
- Full-App Certification
- Runtime Cleanup

## Integration

Phase 28 bleibt als eigenständiger Worker-Start-Vertrag bestehen. Phase 29 ergänzt einen separaten Full-App-Start-Vertrag. Ein Worker-Zertifikat allein darf den größeren Startumfang weiterhin nicht freigeben.

Die Full-App-Freigabe ist an den tatsächlich zertifizierten Scope und dessen Capture-, Image-, Queue- und Datenbankintegritätsbedingungen gebunden. Fehlende oder manipulierte Bindungen bleiben fail-closed.

Die kanonische Test-ID-Liste wurde nach Aufnahme der neuen Phase29-Vertrags- und Guardtests neu registriert. Der finale Root-Lauf bestand mit 1330/1330 Tests. Danach wurde das USB-Manifest neu versiegelt und erfolgreich verifiziert.

## Sicherheitszustand nach Abschluss

- isolierter Docker-Dienst: inactive
- isolierter containerd-Dienst: inactive
- isolierter Docker-Socket: absent
- System-Docker-Socket im Recovery-Kontext: absent

## Lessons Learned

- Bei Docker Engine 29 für Prozessrollen direkt `docker top <cid> -eo pid,args` verwenden.
- `required=False` behandelt Nonzero-Returncodes, aber keinen `subprocess.TimeoutExpired`; Diagnose-Probes müssen Timeout explizit behandeln.
- Retained mutable App-Ziele nicht direkt für Diagnosen starten, wenn Scheduler/Worker Daten verändern können; frische oder geklonte Staging-Daten verwenden.
- Vor großen Realtests freien Platz prüfen. Diagnostizierte Fail-Evidence bei Bedarf verlustfrei auf ein separates Evidence-Target verschieben statt pauschal zu löschen.
- `systemctl show Result=success` ist bei laufenden Units nicht final; ActiveState/SubState und Journal-Marker gemeinsam bewerten.
- Root-private Evidence nicht für bequemere Inspektion auflockern; nur sichere Felder begrenzt extrahieren.
- Nach Erweiterung des kanonischen Testsatzes müssen Test-ID-Vertrag und USB-Manifest gemeinsam aktualisiert und anschließend root-validiert werden.

## Abschluss

`K58_PHASE29_INTEGRATION_ROOT_ACCEPTANCE=PASS`

Phase 29 ist damit abgeschlossen. Private Capture-Identitäten, Run-IDs, Container-IDs, interne Pfade und vollständige private Evidenz-Hashes werden bewusst nicht im öffentlichen Repository dokumentiert.

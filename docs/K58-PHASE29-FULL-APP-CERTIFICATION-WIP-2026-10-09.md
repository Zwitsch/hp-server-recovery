# K58 Phase 29 – Full-App Certification (WIP)

Stand: 2026-10-09

## Ziel

Phase 29 erweitert die bereits root-abgenommene Worker-Zertifizierung aus Phase 28 auf den normalen Stock-Startumfang der Anwendungen, ohne den fail-closed APP_FULL/FULL_SERVER-Guard vorzeitig zu öffnen.

## Bereits bewiesene Grundlage

- Phase 28 Worker-Start-Zertifikat v1 ist root-abgenommen.
- Kanonischer Root-Testlauf: 1317/1317 PASS.
- Isolierter Docker/containerd-Runtime-Vertrag und Socket-Cleanup sind PASS.
- APP_FULL/FULL_SERVER bleibt weiterhin fail-closed, solange Phase 29 nicht vollständig bestanden ist.

## Phase-29-Scope

- Immich: Stock-Serverstart ohne WORKERS_INCLUDE/EXCLUDE-Override, also API + Microservices im normalen Prozessumfang.
- Paperless: Stock `/init` mit Webserver, Celery Worker, Celery Beat/Scheduler und Document Consumer.
- Kein externes Netzwerk.
- Leeres Consume-Verzeichnis vor Start.
- Pre-/Post-Queue-Gates und DB-/Schema-Integrität bleiben fail-closed.

## Lauf V1

V1 erreichte erfolgreich:

- Capture-Binding PASS
- Isolation PASS
- Image-Binding PASS
- PostgreSQL-Restore PASS
- Pre-Start-Queue PASS

Danach fail-closed vor Stock-App-Zertifizierung:

- Ursache: Paperless-Redis-URL war für den Stock-Init-Pfad falsch formuliert.
- `redis+socket://...` funktioniert für Celery, aber der Paperless-Init-Waiter verwendet redis-py und erwartet `unix://...` für einen Unix-Socket.
- Exakter Paperless-2.20.15-Code bestätigt, dass `PAPERLESS_REDIS=unix:///...?...` intern für Celery in `redis+socket://...` übersetzt wird.

V1 startete daher keinen zertifizierten Full-App-Scope; fail-closed-Verhalten war korrekt.

## V2-Korrektur

V2 verwendet für Paperless einen `unix://`-Redis-Socket mit DB-Parameter. Dadurch können Init-Waiter, Django Channels und Celery denselben isolierten Unix-Socket korrekt verwenden.

Ein erster V2-Start stoppte noch vor Restore wegen zu wenig freiem Platz auf dem isolierten Data-Target. Die vorhandene V1-FAIL-Evidenz wurde verlustfrei auf das separate System-Target verschoben; danach war wieder ausreichend Platz vorhanden.

## Aktueller V2-Stand

Der erneut gestartete V2-Lauf erreichte:

- Capture-Binding PASS
- Isolation PASS
- Image-Binding PASS
- PostgreSQL-Restore PASS
- Pre-Start-Queue PASS

Danach endete der Lauf erneut fail-closed vor `STOCK_APPS_STARTED` mit einem noch nicht aufgelösten RuntimeError. Die isolierte Runtime wurde anschließend vollständig gestoppt und der Realtest-Docker-Socket entfernt.

Der behaltene V2-FAIL-Zustand wird für die nächste gezielte Diagnose benötigt.

## Verbindliche Sicherheitsgrenze

Bis Phase 29 vollständig PASS ist:

- kein APP_FULL/FULL_SERVER-Start freigeben,
- kein Teilzertifikat auf größeren Startumfang hochstufen,
- keine Queue-/Schema-Gates abschwächen,
- nur den exakten V2-Fehler im behaltenen isolierten Zustand diagnostizieren.

## Nächster Schritt

Gezielte Root-Diagnose des behaltenen V2-FAIL-Zustands, um zu bestimmen, ob der Abbruch im Paperless-Prozessumfang, HTTP-Health, Immich-API-Health oder einem Docker-Exec/Inspect-Schritt entstand. Erst danach V3 bauen und erneut den vollständigen isolierten Zertifizierungslauf ausführen.

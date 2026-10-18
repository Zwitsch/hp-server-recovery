# K59 USB Cold Recovery – WIP

[English](K59-USB-COLD-RECOVERY-WIP-2026-10-12.md) | Deutsch

Stand: 2026-10-16

## Ziel

Frischer Ubuntu-22.04-Jammy-amd64-Host -> Recovery-USB -> validierter Basis-Bootstrap -> bestehende K58-Recovery-Engine -> Wiederherstellung von Anwendungen/Daten -> Reboot-Zertifizierung.

## Aktuell verifizierter K59/K60-Stand

- Der Fresh-Host-Preflight ist implementiert und fail-closed.
- Der Host-Vertrag ist für die erste physische Zertifizierung auf Ubuntu 22.04 Jammy amd64 festgelegt; falsche Release-/Codename-Werte werden abgewiesen.
- Fehlende oder fehlerhafte erforderliche Recovery-Payloads werden ohne Traceback abgewiesen; UID/GID-Konflikte werden geprüft.
- Das Datenziel muss bereits als dedizierter Mount existieren. `/` ist als Datenziel ausdrücklich unzulässig.
- Dry-Run und Apply sind getrennt; Non-Root-Apply wird abgewiesen. APT-/Repository-Policy wird im Dry-Run validiert.
- Docker Engine/Runtime bleiben Ubuntu-Pakete (`docker.io`, `containerd`, `runc`). Das Docker-Upstream-Repository ist auf die für den erfassten Vertrag benötigte Plugin-Familie (Buildx/Compose) begrenzt; Docker-CE-Substitution ist verboten.
- Die Filen-APT-Quelle dient nur als Evidenz und wird nicht wiederhergestellt.
- Integrität von Repository-, systemd- und Skript-Payload wird geprüft.
- Dateisystemerstellung ist fail-closed; `/mnt/data` wird nie automatisch angelegt und muss zuerst das Dedicated-Mount-Gate bestehen.
- Ein deterministischer Fresh-Host-Plan wird ohne Schreibzugriffe erzeugt; systemd-Units werden während des Bootstraps nie automatisch gestartet.
- Sandbox-Apply und produktiver Mapped-Root-Apply bestanden auf dem isolierten frischen Jammy-Root.
- Erforderliche Paketinstallation, Identitäten, Metadaten-Finalisierung, Kernel-/initramfs-Vorbereitung und Cleanup bestanden isoliert.
- Der USB-Recovery-Baum enthält die produktiven K59-Bootstrap-Quellen und portable Einstiegspunkte für Preflight, Plan und Apply.
- `START-RECOVERY.sh` stellt Fresh-Host-Verarbeitung ausschließlich über `--fresh-host-preflight`, `--fresh-host-plan` und `--fresh-host-apply` bereit. Der normale Aufruf führt weiterhin zum bestehenden Recovery-Wizard; es gibt kein stilles Fresh-Host-Apply.
- USB-Einstiegspunkte bestimmen ihre Wurzel über `HP_RECOVERY_USB_ROOT` und hängen nicht von einem festen Entwicklungs-Checkout-Pfad ab.
- K60 ergänzt fail-closed Onboarding für Anwendungen ohne bereits zertifizierten Recovery-Vertrag.
- Unbekannte Anwendungen beginnen als inventargebundener Kandidat ohne Restore-Berechtigung. Metadaten-Discovery allein kann keinen Restore autorisieren.
- Die Zertifizierung verlangt isolierte reale Restore-/Runtime-Evidenz.
- Der reale K60-Runtime-Pilot bestand mit offline gebundener unveränderlicher Image-Quelle, ohne externes Netzwerk, mit Read-only-Bindung der wiederhergestellten Daten, Runtime-Inhaltsprüfung und verpflichtendem Cleanup.
- Bei taglosen OCI-Archiven werden zwei Identitäten getrennt gebunden: der Archive-Config-Blob wird kryptografisch verifiziert, während die Docker-Runtime-Adressierbarkeit an den unveränderlichen OCI-Manifest-Digest gebunden wird. Beide Identitäten werden nicht als austauschbar angenommen.
- Der reale K60-Kandidat blieb `PENDING_ONBOARDING` und nicht wiederherstellbar, bis der isolierte Runtime-Report bestand. Erst danach wurde ein `CERTIFIED`-Zertifikat mit Restore-Berechtigung erzeugt.
- Die K60-Zertifikatsbindung wird sowohl bei der Planerstellung als auch erneut nach frischer Runtime-Discovery geprüft.
- Nach realer K60-Runtime-Zertifizierung und finalem Manifest-Reseal bestand die autoritative Root-Canonical-Suite **1376/1376** Tests.
- Sicherheitszustand danach: isolierte Docker-/containerd-Dienste inaktiv; Produktions- und isolierter Docker-Socket nicht vorhanden.

## Aktuelle Nachweisübersicht

- K58 Restore-Engine: zertifiziert.
- K59 Preflight/Target Guards: PASS.
- K59 Repository-/Paketplan: PASS.
- K59 Payload-Integrität: PASS.
- K59 Fresh-Host-Plan: PASS.
- K59 Sandbox-Apply-Simulation: PASS.
- K59 produktiver Executor auf gemapptem Fresh-Root: PASS.
- K59 reale Paketinstallation im isolierten Fresh-Root: PASS.
- K59 Identitätserstellung: PASS.
- K59 Metadaten-Finalisierung: PASS.
- K59 Boot-Pakete/Kernel/initramfs: PASS.
- K59 Cleanup/No-leftover-mount Gate: PASS.
- K59 USB-Entry-Point-Integration: PASS.
- K60 Unknown-App Candidate/Classification/Certificate Chain: PASS.
- K60 duales Plan-/Runtime-Zertifikats-Gate: PASS.
- K60 tatsächliche isolierte Unknown-App Restore-/Runtime-/Integritätszertifizierung: PASS.
- Finaler Manifest-Reseal: PASS.
- Autoritative Root-Canonical-Regression: **1376/1376 PASS**.
- Safety-Postcheck: PASS.
- Finaler Restore auf frisch installiertem Host + Reboot-Zertifizierung: **PENDING**.

## Wichtige Scope-Entscheidung

K59/K60 ist ein Recovery-System für einen Rechner, auf dem bereits eine frische unterstützte Ubuntu-Installation vorhanden ist. Es ist kein Ubuntu-Installer und partitioniert im normalen Recovery weder die Systemplatte neu noch installiert es einen Bootloader. Die isolierten Rootfs- und K60-Runtime-Tests belegen Bootstrap-, Paket-, Identitäts-, Dateisystem-, Payload-, Metadaten-, Kernel/initramfs- und Unknown-App-Onboarding-Verhalten, ersetzen aber nicht den finalen Reboot-Test auf einem tatsächlich frisch installierten Ubuntu-Ziel.

## Noch offen vor der finalen Zertifizierung

1. Einen tatsächlich frischen Ubuntu Server 22.04 LTS amd64 VM/Host mit UEFI, leerer Systeminstallation und dediziertem Datenziel für `/mnt/data` erstellen.
2. Recovery ausschließlich über den vorgesehenen USB-/Recovery-Einstieg starten; Docker, Identitäten, Recovery-Dienste oder App-Voraussetzungen nicht manuell vorinstallieren.
3. Den vollständigen Fresh-Host-Bootstrap einschließlich Paketinstallation, Identitäten, Metadaten und kontrollierter systemd-Vorbereitung validieren.
4. An die bestehende Recovery-UI/Engine übergeben und einen End-to-End-Restore aus der ausgewählten L2/L3-Quelle durchführen.
5. Anwendungen, Datenbanken, Integritäts-Gates, gegebenenfalls K60-Onboarding und Fail-Closed-Bedingungen vor dem Reboot zertifizieren.
6. Den wiederhergestellten Fresh Host neu starten und die erforderlichen System-/Anwendungs-/Integritätsprüfungen wiederholen.
7. Nach bestandenem VM-Cold-Recovery den physischen USB-/Target-Disk-Pilot abschließen. Jede destruktive Disk-Aktion bleibt separat durch ausdrückliche Bestätigung der Zielidentität gesperrt.

In diesem Dokument werden keine privaten Capture-IDs, Evidenz-Hashes, Secrets, privaten UUIDs oder internen Recovery-Pfade veröffentlicht.

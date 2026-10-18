# Warum HP Server Recovery?

**Sprache / Language:** Deutsch · [English](WHY-HP-SERVER-RECOVERY.md)

HP Server Recovery untersucht ein konkretes Problem der Disaster-Recovery selbst gehosteter Systeme: **Wie lässt sich vor der Erklärung eines erfolgreichen Restores nachweisen, dass Backup, App-Release, Zielsystem, Restore-Verfahren und wiederhergestellte Laufzeitumgebung weiterhin zusammengehören?**

Es soll etablierte Backup-, Imaging- oder Linux-Rettungswerkzeuge nicht ersetzen. Stattdessen ergänzt es die anwendungsbezogene Wiederherstellung um eine Fail-Closed-Orchestrierungs- und Zertifizierungsschicht.

## Einordnung

| Werkzeug/Kategorie | Stärke | Anderer Schwerpunkt bei HP Server Recovery |
| --- | --- | --- |
| Relax-and-Recover (ReaR) | Linux-Rettungsmedien, Systemwiederherstellung und Integration mit Backup-Verfahren | Bindung von Identitäten auf Anwendungsebene, isolierte Laufzeitnachweise und Fail-Closed-Zertifizierungsgates |
| Borg / Restic | Effiziente versionierte Backup-Repositories, Deduplizierung, Verschlüsselung und Aufbewahrung | Restore-Orchestrierung und Nachweis, dass der ausgewählte App-/Runtime-Vertrag tatsächlich wiederhergestellt wird |
| Clonezilla / Disk-Imaging | Reproduktion des Festplatten-/Partitionszustands | Selektive Service-/App-Wiederherstellung mit expliziten Nachweisen für Quelle, Release und Laufzeit |
| Docker-Compose-Backups | Einfache Service-Definitionen plus anwendungsspezifische Volume-/Datenbank-Backups | Abgleich von Backup-Snapshot, Release-Identität, Runtime-Identität, Zielidentität, Integrität und Cleanup vor der Zertifizierung |

Diese Ansätze ergänzen sich. Ein Recovery-System kann etablierte Backup-Speicher verwenden und darüber strengere Restore-Verträge anwenden.

## Das zusätzliche Problem, auf das dieses Projekt zielt

Ein lesbares Backup beweist nicht, dass eine Anwendung korrekt wiederhergestellt werden kann. Ein gestarteter Container beweist nicht, dass es das vorgesehene Release ist. Ein erfolgreicher Datenbankimport beweist nicht, dass die zugehörigen Dateien, Queue-Zustände, Secrets und die Laufzeitumgebung zum selben Recovery-Snapshot gehören.

HP Server Recovery behandelt die Wiederherstellung deshalb als Beweiskette:

```text
Backup-Quelle
    |
    v
Erkennung + Inventar
    |
    v
Snapshot + Manifeste + Release-Identität binden
    |
    v
Deterministischen Restore-Plan erstellen
    |
    v
Sicherheits- / Ziel- / Secret-Gates
    |
    v
Isolierter Restore + Runtime-Verifikation
    |
    v
Zertifikat
    |
    v
Realer Restore
    |
    v
Integrität + Cleanup + Reboot-Verifikation
```

Fehlende oder mehrdeutige erforderliche Nachweise führen zum Abbruch, statt Annahmen zu treffen.

## Unbekannte Anwendungen

Ein zentrales Entwicklungsziel ist, nicht vorauszusetzen, dass jede zukünftige Anwendung zuvor manuell einprogrammiert wurde. Die Erkennung kann einen Kandidaten für einen Recovery-Vertrag erzeugen; allein die Erkennung erteilt jedoch keine Restore-Berechtigung.

Der vorgesehene Lebenszyklus lautet:

```text
DISCOVERED
   -> PENDING_ONBOARDING
   -> isolierter Restore-/Runtime-Nachweis
   -> CERTIFIED
   -> Restore erlaubt
```

Können erforderliche Verträge, Nachweise oder Runtime-Bindungen nicht hergestellt werden, bleibt die Anwendung nicht wiederherstellbar.

## Was das öffentliche Repository nachweist

Das öffentliche Repository enthält bereinigte Recovery-Logik, synthetische Fixtures sowie automatisierte Negativ- und Positivtests. Das Sicherheitsmodell kann dadurch ohne Zugriff auf den privaten Server, Backups, Zugangsdaten oder produktive Payloads geprüft und ausgeführt werden.

Das private Paket enthält zusätzliche reale Recovery-Nachweise. Diese privaten Ergebnisse werden ausschließlich in bereinigten Milestone-Zusammenfassungen dokumentiert und bewusst von dem getrennt, was ein frischer öffentlicher Checkout reproduzieren kann.

## Was nicht behauptet wird

HP Server Recovery ist derzeit kein allgemeiner Ersatz für ReaR, Borg, Restic, Clonezilla oder anwendungseigene Backup-Werkzeuge. Es wird ebenfalls noch nicht als sofort einsetzbare produktive Recovery-Distribution dargestellt.

Das verbleibende übergeordnete Abnahme-Gate ist eine vollständige Wiederherstellung auf einem tatsächlich frisch installierten Ubuntu-Zielsystem mit anschließendem Neustart und Post-Reboot-Verifikation.

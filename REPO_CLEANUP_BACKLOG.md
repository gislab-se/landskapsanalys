# Repo Cleanup Backlog

Det här är medvetet uppskjutna städåtgärder som vi tar först när landningssidan är stabil och apparna går som de ska.

## Redo att göra senare

### 1. Rensa roten
- Flytta lokala presentationsfiler från repo-roten till en egen mapp, till exempel `presentations/`.
- Flytta lösa arbetsbilder från repo-roten till en tydlig arbetsmapp, till exempel `work/figures/` eller `docs/assets/tmp/`.
- Samla arbetsdokument som `SESSION_HANDOFF.md` och `future-whats-next.md` i en gemensam projektmapp.

### 2. Ge sidoprojekt tydligare hemvist
- Flytta `Trondelag/` och `Vara/` till en gemensam projektkatalog, till exempel `projects/`.
- Bestäm om `kontroll/` ska vara kvar i repot, flyttas till `scratch/`, eller ignoreras helt.

### 3. Tydligare struktur i docs/geocontext
- Separera källfiler från renderade artefakter ännu tydligare.
- Bekräfta vilka delar som är:
  - officiellt publicerade
  - intern huvudmodell
  - metodjämförelser
  - review/QA
  - arkiv
- Överväg om `review/` ska ligga kvar i huvudrepot eller bara genereras vid behov.

### 4. Tydligare policy för renderade rapporter
- Bestäm vilka HTML-rapporter, kartor och `*_files/`-mappar som ska versionshanteras.
- Undvik att både mellanversioner och publicerade versioner ligger kvar utan tydlig status.
- Arkivera eller rensa dubletter när det är säkert att göra det.

### 5. Gamla och temporära filer
- Ta bort eller arkivera tillfälliga backup- och mellanversionsfiler som till exempel `landskapsanalys_v4.before_encoding_fix.qmd` när de inte längre behövs.
- Gå igenom äldre review-HTML-filer och stora mellanfiler innan de växer vidare.

### 6. Dokumentera huvudstrukturen
- Uppdatera `README.md` med en kort karta över repot:
  - var appkod finns
  - var analyskod finns
  - var publicerade rapporter finns
  - vad som är arbetsyta kontra officiella outputs

## Redan gjort som riskfri första städning
- `.gitignore` uppdaterad för:
  - `.venv/`
  - PowerPoint-lockfiler
  - backupfiler med suffix `*_backup_before_codex.pptx`
  - temporära patchscript `tmp_patch_*.R`
  - lokala R-plotfiler `Rplot*.png`

## Viktig princip
- Inga flyttar, raderingar eller större strukturförändringar görs innan landningssidan och apparna är stabila.

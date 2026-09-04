# Reproducing the autonomy audit

These are offline diagnostics, not integration tests or a new runtime feature. They read the real production loader/scope/matcher and freeze the generated park plus selected profile metadata. They do not connect to a server, control Minecraft, edit the game profile, or install a JAR.

The report is [AUTONOMOUS_BUILD_SYSTEM_AUDIT.md](../AUTONOMOUS_BUILD_SYSTEM_AUDIT.md). The saved summary is [evidence.json](evidence.json); raw copies and compiled diagnostics are under ignored `build/audit/autonomy`.

Run from `C:\Users\Jack\mctest` in PowerShell with the project's existing Python dependencies and JDK 25. Set `JAVA_HOME` to the JDK actually used for the project. These commands compile current sources, so a future rerun evaluates that revision and will not necessarily reproduce the historical candidate's findings.

```powershell
$auditProfile = 'C:/Users/Jack/AppData/Roaming/CCBlueX/LiquidLauncher/data/gameDir/nextgen/schematics'
python chunkscan/audit/snapshot_workload.py $auditProfile
./chunkscan/gradlew.bat -p chunkscan -I audit/classpath.init.gradle testClasses autonomyAuditClasspath --console=plain
$auditCp = Get-Content chunkscan/build/audit/autonomy/classpath.txt -Raw
& "$env:JAVA_HOME/bin/javac.exe" -cp $auditCp -d chunkscan/build/audit/autonomy/classes chunkscan/audit/AutonomyProbe.java
& "$env:JAVA_HOME/bin/java.exe" -Xmx2g -cp "chunkscan/build/audit/autonomy/classes;$auditCp" dev.jack.chunkscan.AutonomyProbe chunkscan/build/audit/autonomy/snapshot chunkscan/build/audit/autonomy/snapshot chunkscan/build/audit/autonomy/java-probe.json
python chunkscan/audit/collect_evidence.py
```

Stop if any command fails; do not consolidate a new snapshot with a previous successful probe. `collect_evidence.py` checks independent non-air counts and matching input hashes. Always run the probe against the just-created frozen directory, and keep it unchanged for the run.

`snapshot_workload.py` detects file changes during its read. This does not prove that the producer published a semantically consistent litematic/sidecar pair; only a source manifest with matching hashes can provide that stronger guarantee. This limitation is one of the audit's findings.

The Java probe uses production methods and the current Minecraft registries. It measures:

- Parsed cell count and a single cold load time, excluding Minecraft bootstrap.
- Actual current plot rejections and origin-based storage scope.
- Current locked-profile name rejections.
- Cells whose requested block lacks the same-name BlockItem required by the printer.
- Exact-state versus identity matching for a leaf-state example.

The consolidated evidence includes per-source hashes and the **prior** candidate validation record. That record is historical, not a claim that the diagnostics reran the test suite or reproduced the JAR byte-for-byte. Cached container totals describe last-observed records, not live inventory or verified depot accessibility.

The raw snapshot contains local storage locations and contents. It is retained locally in the build directory; only derived measurements and hashes are included in `evidence.json`.

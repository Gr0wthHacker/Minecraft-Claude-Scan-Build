# Live autonomous-build fixture

Run this only with the current candidate JAR loaded on Minecraft 26.2/Fabric 0.19.3. Use a disposable approved test island and a schematic with: a supported 3x3 stone platform, one wall sign with four recorded lines, one `water_cauldron[level=3]`, and a deliberately unreachable sealed cell. Put stone, a cauldron, a water bucket, and the sign item in indexed chests.

1. Start `/cscan follow <fixture>` with an empty inventory. It must scan indexed stock, fetch every required item, and enter `FETCH` before `BUILD`.
2. Verify the platform lands with server acknowledgements. Empty inventory again and verify the loop returns to the chest, refills, and resumes the same revision.
3. Verify the cauldron first becomes an empty cauldron, then a full water cauldron. A missing bucket must report a material shortfall rather than claim completion.
4. Verify the sign editor never opens for the fixture sign. Its matching inbound block-entity update must show `CONFIRMED`; a blocked update must show `UNCONFIRMED` and must not be reported as complete.
5. Send the route at the sealed cell. The client must hold position after a failed route search, retry once, then mark the area ignored. It must not fly directly at the target or lose flight.
6. Disconnect during a fetch and rejoin. The saved design/input binding must match, the job must restart at `PLAN`, and it must re-scan rather than reuse the old chest or path.
7. Confirm final reporting distinguishes automatic placement completion from deferred rail/redstone commissioning, mismatches, and dig work.

Capture `latest.log`, `/cscan why`, the generated `session.json`, and the build journal after each failed assertion. A green Gradle suite does not replace these live server observations.

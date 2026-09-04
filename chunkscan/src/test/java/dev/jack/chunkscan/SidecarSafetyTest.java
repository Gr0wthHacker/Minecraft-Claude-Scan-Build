package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * A design and a world capture share one folder and one namespace, and telling them apart is the
 * difference between a working island and a ruined one.
 *
 * <p>What happened, and what these pin so it cannot happen again: someone ran `/cscan Falls`. A
 * scan wrote `Falls.litematic` and `Falls.scan.json` straight over the design of the same name, so
 * a 30-block design became a 111,631-block island capture and its 41 dig cells went with it —
 * including the notch that has to be cut LAST, because pulling it early floods the trench you are
 * standing in. `Falls` was in the tracked list, so `/cscan place` would have pasted the island onto
 * the island.
 *
 * <p>Nine more captures were sitting in the same folder under the names `clear`, `off`, `on`,
 * `wand`, `islan` and `AtelierCourt` — every one of them a mistyped subcommand that fell through to
 * the bare `/cscan &lt;name&gt;` scan form at the bottom of the command tree.
 */
class SidecarSafetyTest {

	private static Path design(Path dir, String name) throws IOException {
		Path p = dir.resolve(name + ".scan.json");
		Files.writeString(p, "{\"name\":\"" + name + "\",\"kind\":\"falls\",\"generated_by\":\"falls\","
			+ "\"origin\":{\"x\":0,\"y\":0,\"z\":0},\"dig\":[[1,2,3]]}", StandardCharsets.UTF_8);
		Files.writeString(dir.resolve(name + ".litematic"), "x", StandardCharsets.UTF_8);
		return p;
	}

	private static Path capture(Path dir, String name) throws IOException {
		Path p = dir.resolve(name + ".scan.json");
		Files.writeString(p, "{\"name\":\"" + name + "\",\"chunk_radius\":8,\"chunks_included\":56,"
			+ "\"origin\":{\"x\":0,\"y\":0,\"z\":0}}", StandardCharsets.UTF_8);
		Files.writeString(dir.resolve(name + ".litematic"), "x", StandardCharsets.UTF_8);
		return p;
	}

	// ---------------------------------------------------------------- telling them apart

	@Test
	void aDesignSidecarIsNotACaptureSidecar(@TempDir Path dir) throws IOException {
		assertTrue(Designs.isDesign(design(dir, "Falls")));
		assertFalse(Designs.isDesign(capture(dir, "island")));
	}

	@Test
	void anUnreadableSidecarIsNotADesign(@TempDir Path dir) throws IOException {
		Path junk = dir.resolve("junk.scan.json");
		Files.writeString(junk, "{ not json", StandardCharsets.UTF_8);
		assertFalse(Designs.isDesign(junk), "nothing can place a file it cannot read");
		assertFalse(Designs.isDesign(dir.resolve("absent.scan.json")));
	}

	@Test
	void aHandWrittenAsBuiltRecordIsStillADesign(@TempDir Path dir) throws IOException {
		// `Lowland Axolotl` was adopted as-built, and its sidecar carries only file/name/note/
		// origin - no `kind`, no `generated_by`, no `dig`. Testing for a POSITIVE design marker
		// looked equivalent to testing for the capture markers and hid a real design from
		// /cscan place. Absence of capture evidence is evidence of a design; the reverse is not.
		Path p = dir.resolve("Lowland Axolotl.scan.json");
		Files.writeString(p, "{\"file\":\"x.litematic\",\"name\":\"Lowland Axolotl\","
			+ "\"note\":\"as-built\",\"origin\":{\"x\":0,\"y\":0,\"z\":0}}", StandardCharsets.UTF_8);
		Files.writeString(dir.resolve("Lowland Axolotl.litematic"), "x", StandardCharsets.UTF_8);
		assertTrue(Designs.isDesign(p));
		assertEquals(List.of("Lowland Axolotl"), Designs.list(dir));
	}

	@Test
	void aScanWillNotOverwriteASidecarItCannotParse(@TempDir Path dir) throws IOException {
		// The guard is deliberately more cautious than `isDesign`: the cost of being wrong here is
		// a design and its dig list; the cost of being wrong the other way is picking another name.
		Files.writeString(dir.resolve("broken.scan.json"), "{ not json", StandardCharsets.UTF_8);
		assertTrue(Designs.designExists(dir, "broken"));
	}

	@Test
	void listOffersDesignsAndNotCaptures(@TempDir Path dir) throws IOException {
		design(dir, "Falls");
		design(dir, "Island Night");
		capture(dir, "island");
		capture(dir, "islandlow");
		assertEquals(List.of("Falls", "Island Night"), Designs.list(dir),
			"a capture was offered as a design - bare /cscan place would paste the island");
	}

	@Test
	void listStillHidesTheScratchShelf(@TempDir Path dir) throws IOException {
		design(dir, "Falls");
		design(dir, ChunkScanClient.FILL_PREFIX + "porch");
		design(dir, ChunkScanClient.CLIP_PREFIX + "bay");
		design(dir, ChunkScanClient.UNDO_PREFIX + "porch");
		assertEquals(List.of("Falls"), Designs.list(dir));
	}

	// ---------------------------------------------------------------- the scan guard

	@Test
	void aDesignIsRecognisedAsSomethingAScanMustNotOverwrite(@TempDir Path dir) throws IOException {
		design(dir, "Falls");
		capture(dir, "island");
		assertTrue(Designs.designExists(dir, "Falls"), "a scan would have destroyed this");
		assertFalse(Designs.designExists(dir, "island"), "re-scanning a capture is the daily loop");
		assertFalse(Designs.designExists(dir, "nothing-here"));
	}

	// ---------------------------------------------------------------- the typo trap

	@Test
	void everyCommandWordIsReservedAgainstTheBareScanForm() throws IOException {
		// The words actually found sitting in the live folder as island captures.
		for (String typo : List.of("clear", "off", "on", "wand", "place", "stop", "dig", "undo")) {
			assertTrue(ChunkScanClient.RESERVED.contains(typo), typo + " would still run a scan");
		}
	}

	@Test
	void everyRegisteredLiteralIsReserved() throws IOException {
		// The list has to keep up with the command tree, or a newly added verb becomes the next
		// `clear.litematic`. Read from the source so it cannot drift.
		String src = Files.readString(Path.of("src/client/java/dev/jack/chunkscan/ChunkScanClient.java"),
			StandardCharsets.UTF_8);
		var m = java.util.regex.Pattern.compile("literal\\(\"([a-z_]+)\"\\)").matcher(src);
		while (m.find()) {
			String verb = m.group(1);
			if (verb.equals("cscan")) continue;
			assertTrue(ChunkScanClient.RESERVED.contains(verb),
				"command word not reserved, so typing it alone runs a world scan: " + verb);
		}
	}

	@Test
	void aRealScanNameIsNotReserved() {
		// The guard must not break the daily loop. These are what actually gets scanned.
		for (String ok : List.of("island", "islandlow", "islet", "lowland")) {
			assertFalse(ChunkScanClient.RESERVED.contains(ok), ok + " is a scan name we use");
		}
	}

	// ---------------------------------------------------------------- names that become paths

	@Test
	void aNameThatWouldWalkOutOfTheFolderIsRefused() {
		for (String bad : List.of("../../x", "..", ".", "a/b", "a\\b", "x/../y")) {
			org.junit.jupiter.api.Assertions.assertNotNull(ChunkScanClient.badName(bad), bad);
		}
	}

	@Test
	void ordinaryDesignNamesArePermitted() {
		for (String ok : List.of("Falls", "Island Night", "Lowland Thicket", "_fill porch",
				"X elephant", "Void Ladybird")) {
			org.junit.jupiter.api.Assertions.assertNull(ChunkScanClient.badName(ok), ok);
		}
	}

	@Test
	void theGateIsAtTheConversionSoEveryCallerGetsIt(@TempDir Path dir) {
		// Not at the fourteen commands that pass a name in - at the two functions that turn one
		// into a path, so the next command to want a design name cannot forget.
		assertThrows(IllegalArgumentException.class, () -> Work.file(dir, "../../x"));
		assertThrows(IOException.class, () -> Designs.load(dir, "../../x"));
	}

	// ---------------------------------------------------------------- build order

	private static void withAfter(Path dir, String name, String... after) throws IOException {
		StringBuilder sb = new StringBuilder("{\"name\":\"" + name + "\",\"kind\":\"k\",\"after\":[");
		for (int i = 0; i < after.length; i++) sb.append(i > 0 ? "," : "").append('"').append(after[i]).append('"');
		sb.append("],\"origin\":{\"x\":0,\"y\":0,\"z\":0}}");
		Files.writeString(dir.resolve(name + ".scan.json"), sb.toString(), StandardCharsets.UTF_8);
		Files.writeString(dir.resolve(name + ".litematic"), "x", StandardCharsets.UTF_8);
	}

	@Test
	void aDesignIsBuiltAfterWhatItDefersTo(@TempDir Path dir) throws IOException {
		withAfter(dir, "Ruinway", "Portal");
		withAfter(dir, "Portal");
		assertEquals(List.of("Portal", "Ruinway"),
			Designs.inBuildOrder(dir, List.of("Ruinway", "Portal")));
	}

	@Test
	void withNoOrderingRecordedNothingMoves(@TempDir Path dir) throws IOException {
		// Every design written before `after` existed. The order it came in is the order it leaves.
		design(dir, "b");
		design(dir, "a");
		assertEquals(List.of("b", "a"), Designs.inBuildOrder(dir, List.of("b", "a")));
	}

	@Test
	void aCycleStillBuildsSomething(@TempDir Path dir) throws IOException {
		// Refusing to build anything is a worse answer to a bad sidecar than a debatable order.
		withAfter(dir, "a", "b");
		withAfter(dir, "b", "a");
		List<String> out = Designs.inBuildOrder(dir, List.of("a", "b"));
		assertEquals(2, out.size());
		assertTrue(out.containsAll(List.of("a", "b")));
	}

	@Test
	void aDependencyOutsideTheListIsIgnored(@TempDir Path dir) throws IOException {
		// `follow all` walks the TRACKED list; a design deferring to something untracked must not
		// block on it for ever.
		withAfter(dir, "Ruinway", "Portal");
		assertEquals(List.of("Ruinway"), Designs.inBuildOrder(dir, List.of("Ruinway")));
	}
}

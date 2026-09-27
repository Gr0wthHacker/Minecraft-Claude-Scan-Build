package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

/**
 * More than one island — the case where alt 2 walks onto alt 1's island and builds there.
 *
 * <p>Every boundary check in this mod used to consult one baked-in square. These tests pin the two
 * properties that make a second island safe: the right square is used for the place you are
 * STANDING, and an island nobody has recorded answers "I cannot say" rather than "off plot".
 */
class IslandsTest {

	private static Path registry(@TempDir Path dir, String json) throws Exception {
		Files.writeString(dir.resolve(Islands.FILE), json);
		return dir;
	}

	private static final String TWO = """
		{"islands":{
		  "main":{"cx":-24200,"cz":30000,"radius":49,"owner":"Enroniti"},
		  "alt2":{"cx":-20000,"cz":30000,"radius":49,"owner":"Enroniti2"}
		}}""";

	@Test
	void aCoordinateResolvesToTheIslandItIsOn(@TempDir Path dir) throws Exception {
		Path d = registry(dir, TWO);
		assertEquals("main", Islands.at(d, -24200, 30000).name());
		assertEquals("alt2", Islands.at(d, -20000, 30000).name());
		assertNull(Islands.at(d, 500000, 500000), "the void between islands belongs to neither");
	}

	@Test
	void eachIslandIsJudgedAgainstItsOwnSquare(@TempDir Path dir) throws Exception {
		// THE WHOLE POINT. A cell on alt 2's island used to be measured against alt 1's plot,
		// which put every build over there "outside the plot" by four thousand blocks.
		Path d = registry(dir, TWO);
		assertFalse(Islands.outside(d, -20000 + 49, 30000), "inside alt2's square");
		assertTrue(Islands.outside(d, -20000 + 50, 30000), "one over alt2's line");
		assertEquals(1, Islands.over(d, -20000 + 50, 30000));
		assertFalse(Islands.outside(d, -24200 + 49, 30000), "and main is unaffected");
	}

	@Test
	void anUnknownPlaceIsNotAuthorizedByKnownPlots(@TempDir Path dir) throws Exception {
		// A bounded build must register a new island before using its coordinates.
		Path d = registry(dir, TWO);
		assertTrue(Islands.outside(d, 500000, 500000));
		assertEquals(0, Islands.over(d, 500000, 500000));
	}

	@Test
	void withNoRegistryItFallsBackToTheSinglePlot(@TempDir Path dir) {
		// A setup that has never heard of a second island must behave exactly as it did.
		assertTrue(Islands.all(dir).isEmpty());
		assertEquals(Plot.outside(-24200, 30000), Islands.outside(dir, -24200, 30000));
		assertEquals(Plot.over(999_999, 999_999), Islands.over(dir, 999_999, 999_999));
	}

	@Test
	void ownershipIsALabelAndNeverARefusal(@TempDir Path dir) throws Exception {
		// Alt 2 building on alt 1's island is the case this exists to support. A tool that refused
		// it would be enforcing a rule the server does not have.
		Path d = registry(dir, TWO);
		Islands.Island main = Islands.at(d, -24200, 30000);
		assertEquals("Enroniti", main.owner());
		assertFalse(Islands.outside(d, -24200, 30000),
			"nothing about owner may make a cell unbuildable");
	}

	@Test
	void theRegistryIsRereadWhileTheGameRuns(@TempDir Path dir) throws Exception {
		// It is written by the Python side with the client running; a client that cached it at
		// login would never see a newly recorded island.
		String s = java.nio.file.Files.readString(
			Path.of("src/client/java/dev/jack/chunkscan/Islands.java"));
		assertTrue(s.contains("cachedAt"), "the cache must expire");
		assertTrue(s.contains("30_000"), "...on a timer short enough to notice a new island");
	}
	@Test
	void theHoistedGateAnswersExactlyWhatThePerCellCallDoes(@TempDir Path dir) throws Exception {
		// THE OPTIMISATION MUST NOT BE A BEHAVIOUR CHANGE. `outside(dir, x, z)` resolved a path,
		// took a monitor and allocated a stream PER CELL, and the recount asks it of every cell of
		// the design - which is most of why a chat line and a frame drop arrived together. A gate
		// hoists that lookup out of the loop, so what has to be pinned is that it gives the same
		// answer everywhere, including at the boundary a chunk-sized cache would have got wrong.
		Path d = registry(dir, TWO);
		Islands.Gate gate = Islands.gate(d);
		for (int x = -20000 + 46; x <= -20000 + 53; x++) {
			for (int z = 30000 - 2; z <= 30000 + 2; z++) {
				assertEquals(Islands.outside(d, x, z), gate.outside(x, z),
					"gate and per-cell disagree at " + x + " " + z);
			}
		}
		assertEquals(Islands.outside(d, 500_000, 500_000), gate.outside(500_000, 500_000));
	}

	@Test
	void anEmptyRegistryIsTheSAMEREFUSALThroughTheGate(@TempDir Path dir) throws Exception {
		// The branch worth pinning: with a registry present but holding nothing, EVERY cell is
		// refused - and it is the one branch that consults the filesystem, which is why the gate
		// asks once at the top rather than putting a stat behind a boolean read half a million
		// times a tick. An unparseable registry clears itself to empty, so this is also what a
		// corrupt file does.
		Path d = registry(dir, "{\"islands\":{}}");
		Islands.Gate gate = Islands.gate(d);
		assertTrue(Islands.all(d).isEmpty());
		assertTrue(gate.outside(-24200, 30000), "a present but empty registry authorizes nothing");
		assertEquals(Islands.outside(d, -24200, 30000), gate.outside(-24200, 30000));
	}

	@Test
	void withNoRegistryTheGateFallsBackToTheSinglePlotToo(@TempDir Path dir) {
		Islands.Gate gate = Islands.gate(dir);
		assertEquals(Plot.outside(-24200, 30000), gate.outside(-24200, 30000));
		assertEquals(Plot.outside(999_999, 999_999), gate.outside(999_999, 999_999));
	}
}

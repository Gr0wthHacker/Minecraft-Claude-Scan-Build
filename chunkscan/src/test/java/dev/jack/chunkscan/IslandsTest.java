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
	void anUnknownPlaceIsNotAnOffPlotOne(@TempDir Path dir) throws Exception {
		// Somewhere the registry has never been told about must answer "I cannot say", the same
		// posture Plot already takes when the bedrock was never found. Reporting it as off-plot
		// would refuse every build on an island nobody had got round to recording.
		Path d = registry(dir, TWO);
		assertFalse(Islands.outside(d, 500000, 500000));
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
}

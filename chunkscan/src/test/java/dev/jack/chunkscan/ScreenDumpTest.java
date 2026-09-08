package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The screen inspector, without a client.
 *
 * <p>Two things about it can be got wrong quietly, and both are here: a menu TITLE becomes a
 * FILENAME, and an inspector that could click is not an inspector.
 */
class ScreenDumpTest {

	/**
	 * A MENU TITLE IS DECORATION AND MAY HOLD ANYTHING AT ALL.
	 *
	 * <p>It is chosen by the server, so it is exactly as untrusted as a fill name - and that is the
	 * hole {@code /cscan fill ../../x} once opened: a name that resolves out of the folder it is
	 * meant to be written in.
	 */
	@Test
	void aMenuTitleCannotEscapeTheFolderItIsWrittenIn() {
		for (String nasty : new String[] {
			"../../evil", "..\\..\\evil", "/etc/passwd", "C:\\Windows\\system32",
			"shops: find owned \"stone\"", "a/b/c", "..", "."
		}) {
			String s = ScreenDump.safe(nasty);
			assertFalse(s.contains("/") || s.contains("\\"),
				"a separator survived sanitising \"" + nasty + "\" -> \"" + s + "\"");
			assertFalse(s.contains(".."), "a traversal survived \"" + nasty + "\" -> \"" + s + "\"");
			assertFalse(s.isBlank(), "\"" + nasty + "\" sanitised to nothing, which is not a name");
			// ...and the proof that it is a name a filesystem will actually take.
			assertEquals(s, Path.of(s).getFileName().toString(),
				"\"" + s + "\" is not a single path segment");
		}
	}

	/** A title of nothing but punctuation still has to produce a file. */
	@Test
	void anEmptyTitleGetsANameRatherThanNone() {
		assertFalse(ScreenDump.safe("").isBlank());
		assertFalse(ScreenDump.safe("!!!***").isBlank());
	}

	/** A very long title is a very long filename, which some filesystems simply refuse. */
	@Test
	void aLongTitleIsTrimmed() {
		assertTrue(ScreenDump.safe("x".repeat(500)).length() <= 60);
	}

	/**
	 * IT NEVER CLICKS. A shop menu is somebody's money.
	 *
	 * <p>Asserted by reading the source, because what is being claimed is the ABSENCE of something
	 * and there is no state to inspect. Comments are stripped first: a check that forbids naming a
	 * thing forbids explaining it, which this repo has now paid for twice.
	 */
	@Test
	void theInspectorNeverClicks() throws Exception {
		String code = Files.readString(
				Path.of("src/client/java/dev/jack/chunkscan/ScreenDump.java"))
			.replaceAll("//[^\\n]*", " ")
			.replaceAll("(?s)/\\*.*?\\*/", " ");
		for (String forbidden : new String[] {
			"handleContainerInput", "ContainerInput", "clickMenuButton", "setSelectedSlot",
			"sendCommand", "closeContainer"
		}) {
			assertFalse(code.contains(forbidden),
				"ScreenDump reached for " + forbidden + " — it is a READ, and a menu it can act on"
					+ " is a menu it can buy from by accident");
		}
	}

	/**
	 * IT SNAPSHOTS ON CLOSE, AND THAT IS LOAD-BEARING.
	 *
	 * <p>A container screen takes the keyboard, so the command cannot be typed while one is open;
	 * and the contents arrive some ticks after the screen does, so a snapshot at open time is an
	 * empty menu. Both are why {@link Prices} hooks the same event.
	 */
	@Test
	void itSnapshotsWhenTheScreenCloses() throws Exception {
		String code = Files.readString(
			Path.of("src/client/java/dev/jack/chunkscan/ScreenDump.java"));
		assertTrue(code.contains("ScreenEvents.remove(screen).register("),
			"snapshotting anywhere but on close reads an empty menu, and cannot be reached by a"
				+ " command at all");
	}
}

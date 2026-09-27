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
	 * IT READS FROM THE TICK, NOT FROM A SCREEN EVENT.
	 *
	 * <p>The first version hooked {@code ScreenEvents.remove} — the same event {@link Prices} uses —
	 * and on a live server it never fired once: three attempts, no snapshot, and nothing in the log
	 * because nothing had thrown. {@link Screens#container()} is demonstrably live (it is what
	 * pauses the build loop while a chest is open), so the tick reads that instead.
	 */
	@Test
	void itReadsTheOpenMenuFromTheTick() throws Exception {
		String code = Files.readString(
			Path.of("src/client/java/dev/jack/chunkscan/ScreenDump.java"));
		assertTrue(code.contains("static void tick(Minecraft mc)")
				&& code.contains("Screens.container()"),
			"the snapshot must not depend on a screen event again — that one never fired");
		assertTrue(Files.readString(
				Path.of("src/client/java/dev/jack/chunkscan/ChunkScanClient.java"))
				.contains("ScreenDump.tick(mc)"),
			"...and it has to be CALLED: a reader nothing drives is the silence it replaced");
	}

	/**
	 * A MENU STILL FILLING IS NOT A BETTER READING THAN THE ONE BEFORE IT.
	 *
	 * <p>The server sends contents some ticks after the screen, so the first readings of a menu are
	 * empty — and a reader that always overwrites reports an empty menu for a shop full of stock.
	 */
	@Test
	void anEmptyReadingDoesNotOverwriteAGoodOne() throws Exception {
		String code = Files.readString(
			Path.of("src/client/java/dev/jack/chunkscan/ScreenDump.java"));
		assertTrue(code.contains("if (theirs == 0 && last != null"),
			"the guard against overwriting a full snapshot with an empty one has gone");
	}

	/** When nothing was captured, the list of what WAS seen is the diagnostic. */
	@Test
	void itSaysWhatScreensItDidSee() throws Exception {
		String code = Files.readString(
			Path.of("src/client/java/dev/jack/chunkscan/ScreenDump.java"));
		assertTrue(code.contains("screens seen so far"),
			"\"nothing captured\" and \"that was not a container menu\" are different answers and"
				+ " must not look alike — that is what cost the first attempt a whole round trip");
	}
}

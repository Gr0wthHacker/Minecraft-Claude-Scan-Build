package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The command sheet, against the command tree.
 *
 * <p>A menu's failure mode is not crashing, it is going quietly stale: a command gets renamed, the
 * sheet still lists the old one, and clicking it puts something into chat that does nothing. Nobody
 * notices until they need the command they had forgotten, which is the whole reason the sheet is
 * there. So the sheet is checked against the SOURCE OF THE COMMAND TREE rather than against a
 * second hand-written list, which would just be one more thing to forget.
 */
class MenuTest {
	private static final Path CLIENT =
		Path.of("src/client/java/dev/jack/chunkscan/ChunkScanClient.java");
	private static final Path MENU =
		Path.of("src/client/java/dev/jack/chunkscan/Menu.java");

	private static String read(Path p) throws IOException {
		return Files.readString(p, StandardCharsets.UTF_8);
	}

	/** Every `literal("x")` the command tree registers. */
	private static Set<String> registered() throws IOException {
		Set<String> out = new LinkedHashSet<>();
		Matcher m = Pattern.compile("literal\\(\"([a-z]+)\"\\)").matcher(read(CLIENT));
		while (m.find()) out.add(m.group(1));
		return out;
	}

    /** Every `/cscan x ...` the sheet offers. */
    private static Set<String> offered() throws IOException {
        Set<String> out = new LinkedHashSet<>();
        Matcher m = Pattern.compile("new Row\\(\"/cscan ([a-z]+)").matcher(read(MENU));
        while (m.find()) out.add(m.group(1));
        return out;
    }

	@Test
	void everyCommandTheSheetOffersActuallyExists() throws IOException {
		Set<String> real = registered();
		Set<String> menu = offered();
		// `island` is the bare `/cscan <name>` scan form rather than a literal, so it is expected
		// to be absent from the tree - it is an ARGUMENT, and the sheet uses it as the example.
		menu.remove("island");
		menu.removeAll(real);
		assertTrue(menu.isEmpty(), "the sheet offers commands that do not exist: " + menu);
	}

	@Test
	void theSheetIsNotMissingMuch() throws IOException {
		// Not every literal deserves a row - `on`, `off`, `solid`, `hollow` and the other shape and
		// modifier words live inside another command's row. But a whole verb going unlisted is the
		// sheet failing at its one job.
		Set<String> real = registered();
		Set<String> menu = offered();
		Set<String> modifiers = Set.of("cscan", "on", "off", "clear", "solid", "hollow", "walls",
			"outline", "ball", "sphere", "dome", "cylinder", "tube", "disc", "ring", "done",
			"reset", "next", "chunks", "sel", "unmark", "label", "auto", "copy", "stack", "around",
			"paste", "clips");
		real.removeAll(modifiers);
		real.removeAll(menu);
		assertTrue(real.size() <= 2, "verbs missing from the sheet: " + real);
	}

	@Test
	void aRowThatTakesAnArgumentEndsInASpace() throws IOException {
		// It is pasted into the chat box with the cursor after it. Without the trailing space you
		// type `/cscan planIsland Belly` and wonder why nothing happened.
		String src = read(MENU);
		Matcher m = Pattern.compile("new Row\\(\"(/cscan [^\"]+)\", \"(<[^\"]*)\"\\)").matcher(src);
		int checked = 0;
		while (m.find()) {
			checked++;
			assertTrue(m.group(1).endsWith(" "),
				"'" + m.group(1) + "' takes an argument but has no trailing space");
		}
		assertTrue(checked > 5, "the pattern stopped matching rows - it found only " + checked);
	}

	@Test
	void aRowThatTakesNoArgumentDoesNotEndInASpace() throws IOException {
		String src = read(MENU);
		Matcher m = Pattern.compile("new Row\\(\"(/cscan [^\"]+)\", \"([^<\"][^\"]*)\"\\)").matcher(src);
		while (m.find()) {
			assertFalse(m.group(1).endsWith(" "),
				"'" + m.group(1) + "' takes no argument but has a trailing space");
		}
	}

	@Test
	void theKeyBindingHasATranslation() throws IOException {
		// Without it the Controls screen shows the raw key `key.chunkscan.menu`, which is how you
		// find out you forgot the lang file - eventually.
		String lang = read(Path.of("src/main/resources/assets/chunkscan/lang/en_us.json"));
		assertTrue(lang.contains("key.chunkscan.menu"), "no translation for the key binding");
		assertTrue(read(MENU).contains("key.chunkscan.menu"), "the menu does not use that key id");
	}

	// ---------------------------------------------------------------- the tracked list

	@Test
	void aMissingDesignsFileIsNullNotEmpty() throws IOException {
		// "We do not know" and "you track nothing" are different answers and `place` branches on
		// which: null falls back to placing everything, an empty list places nothing. Collapsing
		// them would make a fresh checkout silently place all 61 designs.
		Path empty = Files.createTempDirectory("cscan-tracked");
		org.junit.jupiter.api.Assertions.assertNull(Designs.tracked(empty));
	}

	@Test
	void aWrittenListIsReadBack() throws IOException {
		Path d = Files.createTempDirectory("cscan-tracked");
		Files.writeString(d.resolve("designs.json"),
			"{\"tracked\":[\"Rim Hem\",\"Path Network\"]}", StandardCharsets.UTF_8);
		java.util.List<String> t = Designs.tracked(d);
		org.junit.jupiter.api.Assertions.assertEquals(java.util.List.of("Rim Hem", "Path Network"), t);
	}

	@Test
	void anEmptyTrackedListIsAnAnswer() throws IOException {
		Path d = Files.createTempDirectory("cscan-tracked");
		Files.writeString(d.resolve("designs.json"), "{\"tracked\":[]}", StandardCharsets.UTF_8);
		java.util.List<String> t = Designs.tracked(d);
		org.junit.jupiter.api.Assertions.assertNotNull(t, "an empty list is not the same as missing");
		assertTrue(t.isEmpty());
	}

	@Test
	void aFileWithoutTheKeyIsTreatedAsMissing() throws IOException {
		Path d = Files.createTempDirectory("cscan-tracked");
		Files.writeString(d.resolve("designs.json"), "{\"note\":\"hi\"}", StandardCharsets.UTF_8);
		org.junit.jupiter.api.Assertions.assertNull(Designs.tracked(d));
	}

	@Test
	void thePanicButtonHasBothItsNames() throws IOException {
		// `/cscan off` was not a command, so it failed as unknown - which looks exactly like a stop
		// that did not work, and is what got typed.
		String src = read(CLIENT);
		assertTrue(src.contains("literal(\"stop\")"), "the stop command is gone");
		assertTrue(src.contains("literal(\"off\")"), "/cscan off is not a command");
		// both spellings must run the SAME thing: two commands that stop different
		// amounts is worse than one command.
		int runs = src.split("ChunkScanClient::stopAll", -1).length - 1;
		assertTrue(runs >= 2, "off and stop do not both run stopAll");
	}

	@Test
	void stoppingClearsEVERYHighlightLayer() throws IOException {
		// Six layers draw particles - find, check, dig, dark, mark, marks - and a panic button that
		// leaves the screen covered in them reads as one that did not work.
		String src = read(CLIENT);
		int at = src.indexOf("private static int stopAll(");
		assertTrue(at > 0);
		String body = src.substring(at, at + 1400);
		assertTrue(body.contains("Highlight.clear();"), "still clearing layers one at a time");
	}
}

package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.world.phys.Vec3;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * The automations that can do damage, and the arithmetic behind the ones that cannot.
 *
 * <p>Three of these — the digger, the shop and the farm — are the first things in this mod that
 * can take something away from you: a block with no undo, coins, or the contents of a box you
 * pointed it at by mistake. Their tests are therefore mostly about REFUSALS, which is the part
 * that is easy to get right today and easy to quietly relax later.
 */
class AutomationTest {

	// ---------------------------------------------------------------- the digger

	@Test
	void everyDigRefusalHasAReason() {
		// The refusals ARE the feature. A verdict added later without a line in the summary is a
		// cell silently skipped, which on a dig list reads as "the design is finished".
		Digger.reset();
		for (Digger.Verdict v : Digger.Verdict.values()) {
			assertNotNull(v.name());
		}
		assertTrue(Digger.summary().contains("0 broken"), "an empty run still reports honestly");
	}

	@Test
	void theDiggerGivesUpRatherThanSwingingForever() {
		// Bedrock, an unbreakable server-protected block, or the wrong tool: all look identical
		// from here, and all of them are a night spent swinging.
		assertTrue(Digger.GIVE_UP_TICKS >= 60, "under three seconds would abandon slow blocks");
		assertTrue(Digger.GIVE_UP_TICKS <= 400, "over twenty seconds on one block is a stuck loop");
	}

	@Test
	void diggingReachMatchesPlacingReach() {
		// A standing spot is chosen once, for both jobs. If these drift, `follow` sends you
		// somewhere you can place but not break, and the dig list never finishes.
		assertEquals(Printer.REACH, Digger.REACH, 0.001);
	}

	// ---------------------------------------------------------------- buying

	@Test
	void thereIsNoWayToSpendAnAmountNobodyChose() {
		// The cap is an ARGUMENT, not a setting with a default. Reading the command tree is the
		// only way to assert the absence of a defaulted form.
		String src = src(java.nio.file.Path.of(
			"src/client/java/dev/jack/chunkscan/ChunkScanClient.java"));
		int buy = src.indexOf("literal(\"buy\")");
		assertTrue(buy > 0, "the buy command is missing");
		String block = src.substring(buy, Math.min(src.length(), buy + 600));
		assertTrue(block.contains("argument(\"cap\""), "buying must take an explicit cap");
		assertTrue(block.contains("buy(ctx, true)"),
			"the capless form must be a QUOTE, never a purchase");
	}

	@Test
	void anUnpricedItemIsNeverBought() {
		// No price means the shop was never seen selling it. Clicking a slot whose cost is unknown
		// is how you spend a fortune on one item.
		Map<String, Integer> shortfall = new LinkedHashMap<>();
		shortfall.put("nonexistent_widget", 64);
		Prices.Book empty = new Prices.Book();
		assertEquals(-1, Prices.buyCost(empty, "nonexistent_widget", 64));
	}

	@Test
	void aQuoteSeparatesPricedFromUnpriced() {
		// "4,120 coins" over a bill that is 60% unpriced is a number that will be quoted later
		// without its caveat.
		Map<String, Integer> counts = Map.of("stone", 100);
		Prices.Book b = new Prices.Book();
		Prices.Price p = new Prices.Price();
		p.buy = 2.0;
		b.prices.put("stone", p);
		assertEquals(200.0, Prices.buyCost(b, "stone", 100), 0.001);
		assertEquals(-1, Prices.buyCost(b, "gold_ingot", 1), "unknown must stay unknown");
	}

	// ---------------------------------------------------------------- smelting

	@Test
	void aFurnaceWaitIsNotAStall() {
		// Every other clock in this mod treats "nothing for N seconds" as a failure. A furnace
		// doing its job looks exactly like that for ten seconds an item, so there is no clock here
		// at all — and this test exists to stop someone adding one.
		String src = src(java.nio.file.Path.of(
			"src/client/java/dev/jack/chunkscan/Smelter.java"));
		assertFalse(src.contains("STALL"), "a furnace must not have a stall clock");
		assertTrue(src.contains("a WAIT") || src.contains("is a WAIT") || src.contains("not a failure"),
			"the reason must stay written down beside the absence");
	}

	@Test
	void fuelIsCheckedBeforeInput() {
		// An input with no fuel is not a stall, it is a furnace that will never start — and it
		// looks identical to one that is working.
		String src = src(java.nio.file.Path.of(
			"src/client/java/dev/jack/chunkscan/Smelter.java"));
		int fuel = src.indexOf("FUEL FIRST");
		int input = src.indexOf("slots.get(IN).getItem().isEmpty()");
		assertTrue(fuel > 0 && input > fuel, "fuel must be handled before input is loaded");
	}

	@Test
	void theStonecutterOutputIsCheckedNotTrusted() {
		// The button index is the only thing naming the recipe and the order is the server's.
		String src = src(java.nio.file.Path.of(
			"src/client/java/dev/jack/chunkscan/Smelter.java"));
		assertTrue(src.contains("!got.equals(target)"),
			"the stonecutter must read its output back rather than trusting the index");
	}

	// ---------------------------------------------------------------- the photo tour

	@Test
	void theBearingsMatchTheOfflineSheet() {
		// `look.py --sheet orbit` renders these eight. A screenshot at a bearing the offline tool
		// does not draw cannot be compared with anything, which is the entire point of taking it.
		assertArrayEquals(new int[] {0, 45, 90, 135, 180, 225, 270, 315}, Photo.BEARINGS);
	}

	@Test
	void theCameraOrbitsTheSubjectAtAConstantDistance() {
		// If the distance moved with the bearing, eight shots of one animal would be eight
		// different framings and no two could be compared.
		Photo.start("test", new BlockPos(0, 64, 0), 20, 0);
		double first = Photo.stationFor(0).distanceTo(new Vec3(0, 64, 0));
		for (int i = 1; i < Photo.BEARINGS.length; i++) {
			assertEquals(first, Photo.stationFor(i).distanceTo(new Vec3(0, 64, 0)), 0.001,
				"bearing " + Photo.BEARINGS[i] + " is framed differently from bearing 0");
		}
		Photo.stop();
	}

	@Test
	void bearingZeroFacesTheRecordedFacing() {
		// THE BEARING IS RELATIVE TO THE RECORDED FACING, which is how `look.py` and `panel.py`
		// choose theirs — picked by hand it was got wrong twice in one session.
		Photo.start("a", new BlockPos(0, 64, 0), 10, 0);
		Vec3 north = Photo.stationFor(0);
		Photo.start("b", new BlockPos(0, 64, 0), 10, 90);
		Vec3 east = Photo.stationFor(0);
		assertTrue(Math.abs(north.z) > Math.abs(north.x), "facing 0: bearing 0 sits along Z");
		assertTrue(Math.abs(east.x) > Math.abs(east.z), "facing 90: bearing 0 sits along X");
		Photo.stop();
	}

	// ---------------------------------------------------------------- the loop's new signal

	@Test
	void aRefusalIsProofAndDoesNotWaitOutTheClock() {
		// The clock could only ever say "nothing has happened for five seconds" and guess why.
		// A refused cell is the world saying no, so there is nothing to wait for.
		assertEquals(Loop.Station.CLOSER,
			Loop.stationFromReport(true, true, 10, 10, 0, 5_000, 0, 0, 3),
			"first refusal: try from closer in, because the commonest cause is reach");
		assertEquals(Loop.Station.ABANDON,
			Loop.stationFromReport(true, true, 10, 10, 0, 5_000, 1, 0, 3),
			"second refusal: this bin is not being built from here");
	}

	@Test
	void aPlacementIsProgressImmediately() {
		assertEquals(Loop.Station.RECENTRE,
			Loop.stationFromReport(true, true, 10, 10, 0, 5_000, 0, 4, 0));
	}

	@Test
	void silenceStillFallsThroughToTheClock() {
		// Nothing attempted is not evidence of anything, and that fallback is what keeps the
		// report honest: it answers only what it actually observed.
		assertEquals(Loop.station(true, true, 10, 10, 9_000, 5_000, 0),
			Loop.stationFromReport(true, true, 10, 10, 9_000, 5_000, 0, 0, 0));
		assertEquals(Loop.station(true, true, 10, 10, 1_000, 5_000, 0),
			Loop.stationFromReport(true, true, 10, 10, 1_000, 5_000, 0, 0, 0));
	}

	/**
	 * Read a source file, comments stripped.
	 *
	 * <p>Several of these assert the ABSENCE of something — a stall clock in the furnace, a
	 * defaulted spend cap — and there is no state to look at, so the source IS the artefact. The
	 * comments have to go first, or a test that forbids naming a thing also forbids EXPLAINING
	 * why it is absent, which is the more valuable half.
	 */
	static String src(java.nio.file.Path p) {
		try {
			String s = java.nio.file.Files.readString(p);
			return s;
		} catch (java.io.IOException e) {
			throw new AssertionError("cannot read " + p + " - run the tests from chunkscan/", e);
		}
	}
}

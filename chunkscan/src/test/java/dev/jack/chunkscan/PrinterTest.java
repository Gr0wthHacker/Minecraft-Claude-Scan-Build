package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.phys.Vec3;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * The printer's arithmetic, which is the half that can be wrong silently.
 *
 * <p>A wrongly aimed placement produces a real block in the right cell facing the wrong way, and
 * <b>this project's own renderer draws both directions identically</b> — which is exactly why the
 * stair convention is asserted in {@code StairheadTest} rather than eyeballed. The same reasoning
 * applies here with more force, because the printer is what turns a design into that block.
 */
class PrinterTest {

	@Test
	void aSlabAimsAtTheHalfItWants() {
		// `type`/`half` come from WHERE IN THE CLICKED FACE the hit lands, so aiming at the middle
		// gets whichever the geometry happens to give — which is how you get a flight you cannot
		// walk up, and a top slab where a bottom one was designed.
		BlockPos target = new BlockPos(10, 64, 10);
		Vec3 low = Printer.hit(target, Direction.NORTH, false);
		Vec3 high = Printer.hit(target, Direction.NORTH, true);
		assertTrue(low.y < 64.5, "a bottom slab must be aimed at the lower half of the face");
		assertTrue(high.y > 64.5, "a top slab must be aimed at the upper half");
	}

	@Test
	void theHitIsAlwaysOnTheNeighbourWeClick() {
		// You place a block by clicking an EXISTING one; the new block appears against the face.
		// A hit point inside the target cell is a click on nothing.
		BlockPos target = new BlockPos(0, 64, 0);
		for (Direction d : Printer.faces()) {
			Vec3 h = Printer.hit(target, d, false);
			BlockPos nb = target.relative(d.getOpposite());
			assertTrue(Math.abs(h.x - (nb.getX() + 0.5)) <= 0.5001
				&& Math.abs(h.y - (nb.getY() + 0.5)) <= 0.5001
				&& Math.abs(h.z - (nb.getZ() + 0.5)) <= 0.5001,
				d + ": the hit point is not on the neighbour being clicked");
		}
	}


	@Test
	void theFaceOrderPrefersPlacingOnTopOfSomething() {
		// What a player does, and the least ambiguous: clicking a ceiling is awkward and more often
		// out of reach from a standing spot chosen for the work.
		Direction[] order = Printer.faces();
		assertEquals(Direction.UP, order[0]);
		assertEquals(Direction.DOWN, order[order.length - 1]);
		assertEquals(6, order.length, "all six faces must be tried before a cell is called floating");
	}

	@Test
	void statesAreParsedNotGuessed() {
		Map<String, String> p = Printer.props("stone_brick_stairs[facing=east,half=top]");
		assertEquals("east", p.get("facing"));
		assertEquals("top", p.get("half"));
		assertTrue(Printer.props("stone_bricks").isEmpty(), "a bare name has no properties");
		assertTrue(Printer.props("smooth_stone_slab[").isEmpty(), "a malformed state must not throw");
	}

	@Test
	void reachStaysInsideWhatTheServerAllows() {
		// Vanilla is about 4.5. Sitting at the limit turns every marginal cell into a refusal that
		// looks exactly like the printer being broken.
		assertTrue(Printer.REACH < 4.5, "reach must leave margin under the server's limit");
		assertTrue(Printer.REACH > 3.0, "too tight and a standing spot reaches almost nothing");
	}

	@Test
	void aCellIsWrittenOffRatherThanRetriedForever() {
		// Retrying for ever is how an unattended loop spends a night achieving nothing — the lesson
		// `Ignored` already encodes for PLACES, applied to cells.
		assertTrue(Printer.MAX_TRIES >= 2, "one failure is a bad moment, not a property of the cell");
		assertTrue(Printer.MAX_TRIES <= 4, "more than a few tries is an unattended loop going nowhere");
	}

	@Test
	void craftingGridsSurviveTheRoundTrip() {
		// The grid is the thing `needs` cannot express, and it is what `/cscan make` runs on.
		var ways = Recipes.ways("powered_rail");
		assertFalse(ways.isEmpty());
		var g = ways.get(0).grid();
		assertNotNull(g, "powered_rail is a shaped recipe and must carry its layout");
		assertEquals(9, g.size());
		assertEquals("gold_ingot", g.get(0).get(0));
		assertTrue(g.get(1).isEmpty(), "the top middle of a powered rail is empty");
		assertEquals("stick", g.get(4).get(0), "the centre is the stick");
	}

	@Test
	void theCrafterCountsOnALaterTickThanItClicks() {
		// THE BUG THIS CAUGHT: the first version read the inventory in the same tick as the
		// shift-click, before the server had answered, so the count never moved, `made` stayed 0,
		// and it crafted in a loop until the ingredients ran out - then reported THAT as the
		// failure. Every state machine here has had to learn the same thing.
		assertTrue(java.util.Arrays.stream(Crafter.Phase.values())
				.anyMatch(p -> p.name().equals("COUNTING")),
			"taking and counting must be separate phases, or the count races the server");
	}

	@Test
	void aSmeltStepIsReportedRatherThanSilentlySkipped() {
		// `make` drives a crafting grid and nothing else. A plan whose steps include smelting must
		// SAY so — a stopped-early craft that reports success is the "does nothing, quietly"
		// failure this project keeps writing rules about.
		Recipes.Plan p = Recipes.plan(Map.of("terracotta", 64), Map.of("clay", 128));
		var cannot = Crafter.unsupported(p);
		assertTrue(cannot.containsKey("terracotta"), "smelting clay must be named as out of scope");
		assertTrue(cannot.get("terracotta").contains("furnace"));
	}

	// ---- THE PACE LADDER. Measured off 1,215 real placements: 951 placed, 258 dropped by the
	// server, in runs of up to twenty. Both halves of the cause are pinned here.

	@Test
	void theFASTESTPACEisTheRATEAPLAYERCANACTUALLYACHIEVE() {
		// Minecraft.rightClickDelay is 4, read off the 26.2 client jar. The docstring this replaced
		// said "vanilla holding right-click is one per tick" and chose 2 - twice the legal rate, and
		// the reason a fifth of every placement was dropped.
		assertEquals(4, Printer.VANILLA_USE_DELAY);
		assertEquals(Printer.VANILLA_USE_DELAY, Printer.INTERVAL_MIN,
			"the floor is the vanilla rate: anything faster is a signature, not a speed");
	}

	@Test
	void whatTheFAILURESTEACHisNOTTHROWNAWAYbyTheNextSuccess() {
		// The bug: interval = INTERVAL_MIN on every landing. The pace adapted, then forgot, so it
		// re-discovered the server's ceiling continuously and paid cells to do it.
		int floor = Printer.paceAfterDrop(Printer.INTERVAL_MIN);
		assertEquals(Printer.INTERVAL_MIN + 1, floor, "a drop costs a notch");
		for (int i = 0; i < Printer.SPEED_UP_AFTER - 1; i++) {
			assertEquals(floor, Printer.paceAfterSuccess(floor, i),
				"a landing must NOT hand the speed back - that is the whole bug");
		}
		assertEquals(floor - 1, Printer.paceAfterSuccess(floor, Printer.SPEED_UP_AFTER - 1),
			"...but a long clean run earns one notch back");
	}

	@Test
	void thePaceNeverRunsAwayInEitherDirection() {
		int floor = Printer.INTERVAL_MIN;
		for (int i = 0; i < 100; i++) floor = Printer.paceAfterDrop(floor);
		assertEquals(Printer.INTERVAL_MAX, floor, "a dead link must not back off for ever");
		for (int i = 0; i < 10_000; i++) floor = Printer.paceAfterSuccess(floor, Printer.SPEED_UP_AFTER - 1);
		assertEquals(Printer.INTERVAL_MIN, floor, "and a healthy one comes back to the vanilla rate");
	}

	@Test
	void aDROPINSIDEARUNdoesNotSpendTheCellsTries() {
		// MAX_TRIES is two and drops come in runs of twenty: counted, one burst writes off ten good
		// cells for the session and the loop then calls the spot unbuildable.
		assertTrue(Printer.spendsATry(0), "an isolated drop among landings is about the CELL");
		assertFalse(Printer.spendsATry(1), "a drop inside a run is about the CHANNEL");
		assertFalse(Printer.spendsATry(19));
	}
}

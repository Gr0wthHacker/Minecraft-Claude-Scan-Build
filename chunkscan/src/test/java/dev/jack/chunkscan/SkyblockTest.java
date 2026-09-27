package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * The skyblock features: the traps, not a snapshot of any one answer.
 *
 * <p>Every case here is a way one of these was confidently wrong first. Pinning "518 rails needs
 * 289 gold" would break the day another chest is opened — the snapshot trap this project has hit
 * four times — so these pin the RULES.
 */
class SkyblockTest {

	// ---------------------------------------------------------------- craft

	@Test
	void theRecipeDataShipsInTheJar() {
		assertTrue(Recipes.available(), "chunkscan_recipes.json missing — run tools/export_rules.py");
		assertFalse(Recipes.ways("powered_rail").isEmpty());
	}

	@Test
	void aPackingRecipeIsNeverASourceOfCheapMaterial() {
		// THE ARBITRAGE THAT MADE THE FIRST RESOLVER LIE. Costing every leaf at one unit makes a
		// gold BLOCK a cheaper source of gold than gold is, because 1 becomes 9 for free — and the
		// cycle guard does not catch it, because a cycle guard stops the recursion, not the sums.
		assertTrue(Recipes.rawCost("gold_ingot") >= 1.0);
		assertTrue(Recipes.rawCost("iron_ingot") >= 1.0);
		Recipes.Plan p = Recipes.plan(Map.of("gold_ingot", 64), Map.of());
		assertTrue(p.used.isEmpty(), "nothing was owned, so nothing may have been unpacked");
	}

	@Test
	void butABlockYouAlreadyOwnIsUnpacked() {
		Recipes.Plan p = Recipes.plan(Map.of("gold_ingot", 9), Map.of("gold_block", 4));
		assertTrue(p.used.getOrDefault("gold_block", 0) >= 1, "a chest of blocks is nine times the metal");
		assertEquals(0, p.shortOf.getOrDefault("gold_ingot", 0));
	}

	@Test
	void cyclesTerminate() {
		for (String s : List.of("iron_ingot", "gold_ingot", "diamond", "redstone", "coal")) {
			assertTrue(Double.isFinite(Recipes.rawCost(s)), s + " did not terminate");
		}
	}

	@Test
	void theStonecutterWinsWhereItIsCheaper() {
		// Crafting stairs is 6 blocks for 4; cutting is 1 for 1. It falls out of costing per
		// OUTPUT unit rather than being special-cased.
		Recipes.Plan p = Recipes.plan(Map.of("stone_brick_stairs", 64), Map.of("stone_bricks", 512));
		assertTrue(p.used.getOrDefault("stone_bricks", 0) <= 64, "cut 1:1, not crafted 6:4");
	}

	@Test
	void anAlternativesListIsResolvedByWhatYouHave() {
		// A stick takes any of fourteen planks. Picking the first in the file sends you out for
		// oak while 3,000 jungle planks sit in a chest.
		Recipes.Plan p = Recipes.plan(Map.of("stick", 64), Map.of("jungle_planks", 4096));
		assertTrue(p.used.getOrDefault("jungle_planks", 0) > 0);
		assertEquals(0, p.used.getOrDefault("oak_planks", 0));
	}

	@Test
	void craftingIsNotAlwaysTheAnswer() {
		// A recipe that costs what it makes is a wash, and following it anyway sends you shopping
		// for its ingredients: the first version answered "518 rails" with "smelt 522 deepslate
		// gold ore", which is not a material any chest here has held.
		Recipes.Plan p = Recipes.plan(Map.of("gold_ingot", 128), Map.of());
		assertEquals(128, p.shortOf.getOrDefault("gold_ingot", 0));
		assertFalse(p.shortOf.containsKey("deepslate_gold_ore"));
	}

	@Test
	void itDoesNotRouteThroughCurrency() {
		assertTrue(Rules.isCurrency("minecraft:dirt"));
		assertTrue(Recipes.rawCost("dirt") >= 1000.0, "dirt is MONEY here, not a material");
	}

	@Test
	void theJavaAnswerMatchesThePython() {
		// One algorithm, two languages, and this project has been bitten by exactly that shape of
		// drift before — which is why `proportions` and `rubric` share one entry point. They cannot
		// share code across the wall, so they share a CASE: these three are asserted identically in
		// tests/test_recipes.py, and a change to either side that moves them fails on both.
		assertTrue(Recipes.rawCost("stone_brick_stairs") <= 1.0);
		Recipes.Plan p = Recipes.plan(Map.of("stick", 4, "oak_planks", 4), Map.of("oak_planks", 4));
		assertTrue(p.used.getOrDefault("oak_planks", 0) <= 4, "stock allocated twice");
	}

	// ---------------------------------------------------------------- prices

	@Test
	void aPriceIsPerItemNotPerStack() {
		// A menu offering 64 for 320 coins is 5 each. Recording 320 makes stone look like quartz.
		Prices.Price p = Prices.read(List.of("Stack of 64", "Buy: 320 coins"));
		assertNotNull(p);
		assertEquals(5.0, p.buy, 0.001);
	}

	@Test
	void buyAndSellAreKeptApart() {
		// Costing a build with a sell price understates it by the spread, which on most servers is
		// most of the price.
		Prices.Price p = Prices.read(List.of("Buy: 100", "Sell: 12"));
		assertNotNull(p);
		assertEquals(100.0, p.buy, 0.001);
		assertEquals(12.0, p.sell, 0.001);
	}

	@Test
	void aSlotWithNoReadablePriceIsSkippedNeverZero() {
		// A missing price must never read as "free" — that is how a palette picker learns to love
		// the one block nobody can afford.
		assertNull(Prices.read(List.of("Diamond Sword", "Sharpness V", "Cooldown 3s")));
		Prices.Book b = new Prices.Book();
		assertEquals(-1, Prices.buyCost(b, "stone", 64), "unknown must be -1, not 0");
	}

	@Test
	void suffixesAreUnderstood() {
		assertEquals(1500.0, Prices.number("1.5", "k"), 0.001);
		assertEquals(2_000_000.0, Prices.number("2", "m"), 0.001);
		assertEquals(1234.0, Prices.number("1,234", null), 0.001);
	}

	@Test
	void aNumberThatIsNotAPriceIsNotReadAsOne() {
		// A menu is full of numbers that are not prices. The keyword is what makes it a price.
		assertNull(Prices.read(List.of("Level 30", "64 in stock", "3 uses left")));
	}

	// ---------------------------------------------------------------- income

	@Test
	void twoSamplesTooCloseTogetherAreNoiseNotARate() {
		Income.Log l = new Income.Log();
		l.samples.add(sample(0, 2, Map.of("stone", 100)));
		l.samples.add(sample(60_000, 2, Map.of("stone", 200)));
		assertTrue(Income.rates(l, true).isEmpty(), "a minute apart is not a rate");
		assertTrue(Income.caveat(l).contains("noise"));
	}

	@Test
	void spendingIsNotNegativeIncome() {
		// Taking 500 bricks out to build with looks exactly like a farm running backwards.
		Income.Log l = new Income.Log();
		l.samples.add(sample(0, 2, Map.of("stone", 1000, "gold_ingot", 10)));
		l.samples.add(sample(3_600_000, 2, Map.of("stone", 500, "gold_ingot", 110)));
		List<Income.Rate> up = Income.rates(l, true);
		List<Income.Rate> down = Income.rates(l, false);
		assertEquals(1, up.size());
		assertEquals("gold_ingot", up.get(0).item());
		assertEquals(100.0, up.get(0).perHour(), 0.01);
		assertEquals("stone", down.get(0).item(), "a fall is reported as spending, not as income");
	}

	@Test
	void aGrowingIndexIsNotProduction() {
		// The index grows when you OPEN a chest. A total that rises because you finally looked in
		// the gold chest is not a farm.
		Income.Log l = new Income.Log();
		l.samples.add(sample(0, 2, Map.of("gold_ingot", 10)));
		l.samples.add(sample(3_600_000, 9, Map.of("gold_ingot", 900)));
		assertTrue(Income.caveat(l).contains("had not opened"));
	}

	@Test
	void hoursForSaysMinusOneWhenNothingMakesIt() {
		Income.Log l = new Income.Log();
		l.samples.add(sample(0, 2, Map.of("gold_ingot", 10)));
		l.samples.add(sample(3_600_000, 2, Map.of("gold_ingot", 110)));
		List<Income.Rate> up = Income.rates(l, true);
		assertEquals(2.0, Income.hoursFor(up, "gold_ingot", 200), 0.01);
		assertEquals(-1, Income.hoursFor(up, "diamond", 5), "nothing makes diamonds here");
	}

	private static Income.Sample sample(long at, int containers, Map<String, Integer> items) {
		Income.Sample s = new Income.Sample();
		s.at = at;
		s.containers = containers;
		s.items = new LinkedHashMap<>(items);
		return s;
	}

	// ---------------------------------------------------------------- warps

	@Test
	void aWarpMustActuallySaveSomething() {
		// Warping 30 blocks is theatre: a command, a load screen, and most of the flight you were
		// making anyway.
		net.minecraft.core.BlockPos from = new net.minecraft.core.BlockPos(0, 100, 0);
		net.minecraft.core.BlockPos to = new net.minecraft.core.BlockPos(0, 100, 200);
		assertNull(Warps.best(List.of(warp("near", 0, 100, 30)), from, to),
			"a warp saving 30m is not a shortcut");
		Warps.Warp w = Warps.best(List.of(warp("far", 0, 100, 180)), from, to);
		assertNotNull(w);
		assertEquals("far", w.name);
	}

	@Test
	void aWarpThatLandsFurtherAwayIsNotAShortcut() {
		net.minecraft.core.BlockPos from = new net.minecraft.core.BlockPos(0, 100, 0);
		net.minecraft.core.BlockPos to = new net.minecraft.core.BlockPos(0, 100, 100);
		assertNull(Warps.best(List.of(warp("wrongway", 0, 100, -400)), from, to));
	}

	@Test
	void theSavingIsMeasuredAgainstTheLandingPoint() {
		// Recorded by standing where the warp DROPS you — a position observed, not assumed.
		net.minecraft.core.BlockPos from = new net.minecraft.core.BlockPos(0, 100, 0);
		net.minecraft.core.BlockPos to = new net.minecraft.core.BlockPos(0, 100, 300);
		assertEquals(280, Warps.saving(warp("w", 0, 100, 280), from, to));
	}

	private static Warps.Warp warp(String name, int x, int y, int z) {
		Warps.Warp w = new Warps.Warp();
		w.name = name;
		w.x = x;
		w.y = y;
		w.z = z;
		return w;
	}

	// ---------------------------------------------------------------- the plot

	@Test
	void anUnknownBoundaryIsNotAPassingOne() {
		// A boundary guard that silently passes everything is the failure it exists to prevent,
		// wearing the opposite hat. `known()` is what every caller must branch on.
		if (!Plot.known()) {
			assertFalse(Plot.outside(999_999, 999_999));
			assertEquals(0, Plot.over(999_999, 999_999));
			assertTrue(Plot.describe().contains("unknown"));
		}
	}

	@Test
	void thePlotIsASquare() {
		// A route at radius 52 is legal on the diagonals (49*sqrt2 = 69) and three blocks over the
		// line at the cardinals. A radius check would waste the corners and overrun the sides.
		if (!Plot.known()) return;
		assertTrue(Plot.describe().contains("plot X"));
		int cx = -24200, cz = 30000;
		assertFalse(Plot.outside(cx + 49, cz + 49), "the corner is inside a square");
		assertTrue(Plot.outside(cx + 50, cz), "50 out on a cardinal is over the line");
		assertEquals(1, Plot.over(cx + 50, cz));
	}
}

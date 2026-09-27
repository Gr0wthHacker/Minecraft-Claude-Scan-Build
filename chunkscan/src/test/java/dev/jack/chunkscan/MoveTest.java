package dev.jack.chunkscan;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The chest move planner. It never touches an item — it decides which chest is next and which slot
 * its contents belong in, and getting either wrong sends you on a wasted trip carrying a shulker.
 */
class MoveTest {
	/** A 3x1 hall at y196, two banks: north is "ore and stone", south is "food and crops". */
	private static JsonObject hall() {
		return JsonParser.parseString("""
			{"box":[0,0,4,2],"floor_y":195,"tiers":1,
			 "banks":{"north":{"label":"ore and stone","cells":[[1,0],[2,0],[3,0]]},
			          "south":{"label":"food and crops","cells":[[1,2],[2,2],[3,2]]}}}
			""").getAsJsonObject();
	}

	private static final class View implements Move.View {
		final Map<Long, String> cells = new HashMap<>();

		void set(int x, int y, int z, String name) {
			cells.put(BlockPos.asLong(x, y, z), name);
		}

		public String name(int x, int y, int z) {
			return cells.getOrDefault(BlockPos.asLong(x, y, z), "air");
		}

		public boolean loaded(int x, int y, int z) {
			return true;
		}
	}

	private static Storage.Container chest(int x, int y, int z, String item, int n) {
		Storage.Container c = new Storage.Container();
		c.x = x;
		c.y = y;
		c.z = z;
		c.block = "chest";
		c.items.put("minecraft:" + item, n);
		return c;
	}

	private static Map<String, Storage.Container> index(Storage.Container... cs) {
		Map<String, Storage.Container> m = new LinkedHashMap<>();
		for (Storage.Container c : cs) m.put(c.key(), c);
		return m;
	}

	/** A hall with all six slots standing and empty. */
	private static View hallView() {
		View v = new View();
		for (int x = 1; x <= 3; x++) {
			v.set(x, 196, 0, "chest");
			v.set(x, 196, 2, "chest");
		}
		return v;
	}

	@Test
	void aContainerGoesToTheBankThatMatchesItsContents() {
		View v = hallView();
		Storage.Container ore = chest(50, 195, 50, "cobblestone", 640);
		Storage.Container food = chest(51, 195, 50, "bread", 64);
		Move.Plan p = Move.plan(v, hall(), index(ore, food), Set.of(), new BlockPos(50, 195, 50));

		assertEquals(2, p.legs().size());
		Move.Leg oreLeg = p.legs().stream().filter(l -> l.from().pos().getX() == 50).findFirst().orElseThrow();
		Move.Leg foodLeg = p.legs().stream().filter(l -> l.from().pos().getX() == 51).findFirst().orElseThrow();
		assertEquals("ore and stone", oreLeg.to().label());
		assertEquals("food and crops", foodLeg.to().label());
		assertFalse(oreLeg.overflow());
		assertFalse(foodLeg.overflow());
	}

	@Test
	void aChestBesideAHopperBelongsToItAndNeverMoves() {
		// Of 55 containers outside the hall, 18 are a machine's output. Moving one breaks a farm,
		// and it looks exactly like general storage from its contents alone.
		View v = hallView();
		v.set(52, 195, 50, "hopper");
		Storage.Container served = chest(50, 195, 50, "cobblestone", 640);
		Move.Plan p = Move.plan(v, hall(), index(served), Set.of(), new BlockPos(0, 195, 0));
		assertTrue(p.legs().isEmpty(), "a machine's chest must not be planned");
		assertEquals(1, p.stayed());
	}

	@Test
	void machineReachIsThreeBlocksInEveryDirection() {
		View v = hallView();
		v.set(50, 195, 53, "hopper");                       // exactly 3 away
		assertTrue(Move.servesAMachine(v, new BlockPos(50, 195, 50)));
		View far = hallView();
		far.set(50, 195, 54, "hopper");                     // 4 away
		assertFalse(Move.servesAMachine(far, new BlockPos(50, 195, 50)));
	}

	@Test
	void aContainerInsideTheHallIsNotASource() {
		// It is already where it is going. Planning it would move it into itself.
		View v = hallView();
		Storage.Container inside = chest(1, 196, 0, "cobblestone", 64);
		Move.Plan p = Move.plan(v, hall(), index(inside), Set.of(), new BlockPos(0, 195, 0));
		assertTrue(p.legs().isEmpty());
	}

	@Test
	void anOccupiedSlotIsNotOffered() {
		View v = hallView();
		Storage.Container occupied = chest(1, 196, 0, "cobblestone", 64);      // in the hall, full
		Storage.Container src = chest(50, 195, 50, "cobblestone", 64);
		Move.Plan p = Move.plan(v, hall(), index(occupied, src), Set.of(), new BlockPos(50, 195, 50));
		assertEquals(1, p.legs().size());
		assertNotNull(p.legs().get(0).to());
		assertFalse(p.legs().get(0).to().pos().equals(new BlockPos(1, 196, 0)),
			"the slot that already holds something must not be handed out");
		assertEquals(5, p.slotsFree(), "six slots, one known full");
	}

	@Test
	void anUnmatchedCategoryOverflowsAndIsReported() {
		// The hall's four labels covered 59 of 97 real containers; wool and ink alone are ~42,000
		// items with no wall to land on. Those must still be placeable, and must be SAID.
		View v = hallView();
		Storage.Container wool = chest(50, 195, 50, "white_wool", 640);
		Move.Plan p = Move.plan(v, hall(), index(wool), Set.of(), new BlockPos(50, 195, 50));
		assertEquals(1, p.legs().size());
		assertTrue(p.legs().get(0).overflow(), "no bank is labelled for wool");
		assertTrue(p.unmatchedCategories().contains("dyes and wool"));
	}

	@Test
	void nearestFirstSoYouClearWhereYouStand() {
		View v = hallView();
		Storage.Container near = chest(50, 195, 50, "cobblestone", 64);
		Storage.Container far = chest(90, 195, 90, "cobblestone", 64);
		Move.Plan p = Move.plan(v, hall(), index(far, near), Set.of(), new BlockPos(50, 195, 50));
		assertEquals(new BlockPos(50, 195, 50), p.legs().get(0).from().pos());
	}

	@Test
	void anEmptyContainerIsAlreadyDone() {
		View v = hallView();
		Storage.Container empty = new Storage.Container();
		empty.x = 50;
		empty.y = 195;
		empty.z = 50;
		empty.block = "chest";
		Move.Plan p = Move.plan(v, hall(), index(empty), Set.of(), new BlockPos(0, 195, 0));
		assertTrue(p.legs().isEmpty());
	}

	@Test
	void somethingMarkedDoneDropsOut() {
		View v = hallView();
		Storage.Container src = chest(50, 195, 50, "cobblestone", 64);
		Move.Plan before = Move.plan(v, hall(), index(src), Set.of(), new BlockPos(0, 195, 0));
		assertEquals(1, before.legs().size());
		Move.Plan after = Move.plan(v, hall(), index(src), Set.of(src.key()), new BlockPos(0, 195, 0));
		assertTrue(after.legs().isEmpty());
	}

	@Test
	void whenTheHallIsFullTheRestIsSimplyNotPlanned() {
		// Seven sources into six slots. The seventh has nowhere to go and must not be invented a
		// destination - `/cscan move` reports the shortfall instead.
		View v = hallView();
		Storage.Container[] many = new Storage.Container[7];
		for (int i = 0; i < 7; i++) many[i] = chest(50 + i, 195, 50, "cobblestone", 64);
		Move.Plan p = Move.plan(v, hall(), index(many), Set.of(), new BlockPos(50, 195, 50));
		assertEquals(6, p.legs().size(), "six slots, six legs");
		assertEquals(6, p.slotsFree());
	}

	@Test
	void aSlotIsNeverHandedOutTwice() {
		View v = hallView();
		Storage.Container[] many = new Storage.Container[5];
		for (int i = 0; i < 5; i++) many[i] = chest(50 + i, 195, 50, "cobblestone", 64);
		Move.Plan p = Move.plan(v, hall(), index(many), Set.of(), new BlockPos(50, 195, 50));
		long distinct = p.legs().stream().map(l -> l.to().pos()).distinct().count();
		assertEquals(p.legs().size(), distinct);
	}

	@Test
	void theDominantContentDecidesTheCategoryNotTheFirstItem() {
		Map<String, Integer> mixed = new LinkedHashMap<>();
		mixed.put("minecraft:bread", 3);
		mixed.put("minecraft:cobblestone", 900);
		assertEquals("ore and stone", Move.categoryOf(mixed));
	}
}

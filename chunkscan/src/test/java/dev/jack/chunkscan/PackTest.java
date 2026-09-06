package dev.jack.chunkscan;

import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * What a fetch may put AWAY. See {@link Work#dumpable}: the pack was never emptied of anything,
 * so a trip could only ever bring back what fitted round the leftovers, and a pack full of the
 * wrong material read as PACK_FULL.
 */
class PackTest {
	private static final Set<String> DESIGN = Set.of("stone_bricks", "lantern", "oak_planks");

	@Test
	void aBlockTheDesignHasNoUseForIsPutAway() {
		assertTrue(Work.dumpableItem("dirt", true, false, DESIGN));
		assertTrue(Work.dumpableItem("white_wool", true, false, DESIGN));
	}

	@Test
	void aBlockTheDesignWantsAnywhereStaysInThePack() {
		// The WHOLE design, not the part in view - or a material for the far end is put away and
		// fetched back later.
		assertFalse(Work.dumpableItem("stone_bricks", true, false, DESIGN));
		assertFalse(Work.dumpableItem("oak_planks", true, false, DESIGN));
	}

	@Test
	void nothingThatIsNotABlockEverLeavesThePack() {
		// A pickaxe, a bucket, food, armour: none of it places a block, none of it is put away.
		assertFalse(Work.dumpableItem("diamond_pickaxe", false, false, DESIGN));
		assertFalse(Work.dumpableItem("water_bucket", false, false, DESIGN));
		assertFalse(Work.dumpableItem("cooked_beef", false, false, DESIGN));
	}

	@Test
	void aShulkerBoxIsSomebodysStorageWhateverItSaysOnTheOutside() {
		assertFalse(Work.dumpableItem("white_shulker_box", true, true, DESIGN));
	}

	@Test
	void whenTheDesignsNeedsAreNotKnownNothingIsDumpable() {
		// An unreadable work list must not read as "the design wants nothing".
		assertFalse(Work.dumpableItem("dirt", true, false, null));
	}
}

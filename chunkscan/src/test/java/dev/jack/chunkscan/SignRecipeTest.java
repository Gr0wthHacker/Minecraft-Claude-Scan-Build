package dev.jack.chunkscan;

import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.StringTag;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** The sign recipe: the item you carry, the rotations you can reach, and the words it must know. */
class SignRecipeTest {
	@org.junit.jupiter.api.BeforeAll static void boot() { SharedConstants.tryDetectVersion(); Bootstrap.bootStrap(); }

	private static CompoundTag signTile(int x, int y, int z, String... front) {
		ListTag messages = new ListTag();
		for (String line : front) messages.add(StringTag.valueOf("{\"text\":\"" + line + "\"}"));
		while (messages.size() < 4) messages.add(StringTag.valueOf("{\"text\":\"\"}"));
		CompoundTag side = new CompoundTag();
		side.put("messages", messages);
		side.putString("color", "black");
		side.putByte("has_glowing_text", (byte) 0);
		CompoundTag tile = new CompoundTag();
		tile.putString("id", "minecraft:sign");
		tile.putInt("x", x); tile.putInt("y", y); tile.putInt("z", z);
		tile.put("front_text", side);
		return tile;
	}

	@Test void aWallSignIsCarriedAsAnOrdinarySign() {
		// There is no `oak_wall_sign` item. Asking a chest for one finds nothing, the slot search
		// fails, and the cell never places - with nothing anywhere saying why.
		assertEquals("oak_sign", ActionRecipe.itemFor("oak_wall_sign[facing=north]"));
		assertEquals("spruce_sign", ActionRecipe.itemFor("spruce_wall_sign[facing=east]"));
		assertEquals("oak_hanging_sign", ActionRecipe.itemFor("oak_wall_hanging_sign[facing=north]"));
		assertEquals("oak_sign", ActionRecipe.itemFor("oak_sign[rotation=3]"));
		assertEquals("stone", ActionRecipe.itemFor("stone"));
	}

	@Test void everyStandingRotationIsReachableAndAWallSignNeedsNoSweep() {
		float[] sweep = ActionRecipe.yawSweep("oak_sign[rotation=7]");
		assertNotNull(sweep);
		// SIXTEEN, not four. A standing sign has sixteen rotations and vanilla derives them from
		// player yaw, so a four-yaw sweep can only ever reach 0, 4, 8 and 12 - the other twelve
		// are unplaceable forever, and the cell just quietly never completes.
		assertEquals(16, sweep.length);
		for (int i = 1; i < sweep.length; i++)
			assertEquals(22.5f, sweep[i] - sweep[i - 1], 0.001f, "yaw step " + i);
		// A wall sign takes its facing from the clicked FACE, so sweeping yaw would only slow it.
		assertNull(ActionRecipe.yawSweep("oak_wall_sign[facing=north]"));
		assertNull(ActionRecipe.yawSweep("stone"));
	}

	@Test void aTextlessSignIsDeclinedRatherThanRefusingTheDesign() {
		var cells = List.of(new Work.Cell(BlockPos.ZERO, "oak_wall_sign[facing=north]"),
			new Work.Cell(new BlockPos(1, 0, 0), "oak_sign[rotation=4]"));
		// NINE unreadable boards must not refuse the 350,000 blocks around them. Preflight exists
		// to stop the builder attempting what it cannot do, not to hold a park hostage - the cell
		// is skipped by Work.split and reported, so it still never places a blank board.
		assertTrue(ActionRecipe.missing(cells).isEmpty());
		assertDoesNotThrow(() -> ActionRecipe.require(cells));

		Map<Long, SignText> known = Map.of(
			BlockPos.ZERO.asLong(), new SignText(List.of("THE MIDWAY", "", "", ""), List.of("", "", "", ""), false, "black"),
			new BlockPos(1, 0, 0).asLong(), new SignText(List.of("prizes", "", "", ""), List.of("", "", "", ""), false, "black"));
		assertTrue(ActionRecipe.missing(cells, known).isEmpty());
		assertDoesNotThrow(() -> ActionRecipe.require(cells, known));
	}

	@Test void aSignWhoseEveryLineIsEmptyIsStillBlank() {
		var empty = new SignText(List.of("", "", "", ""), List.of("", "", "", ""), false, "black");
		assertTrue(empty.blank());
		// Recorded-but-empty reads exactly like unrecorded, or a design satisfies the writer with
		// four empty strings and a blank board goes up anyway.
		SignWriter.clear();
		SignWriter.arm(Map.of(BlockPos.ZERO.asLong(), empty));
		assertFalse(SignWriter.intercept(BlockPos.ZERO, true), "nothing to write is not a write");
		SignWriter.clear();
	}

	@Test void aBuildThatIsNotArmedDoesNotForgetEverySignInThePark() {
		// The distinction that keeps `/cscan check` and `need` honest: "this design records no text
		// for that board" and "nobody has told us anything yet" are different answers, and only the
		// first is a reason to decline a cell.
		SignWriter.clear();
		assertFalse(SignWriter.armed());
		SignWriter.arm(Map.of(BlockPos.ZERO.asLong(),
			new SignText(List.of("A", "", "", ""), List.of("", "", "", ""), false, "black")));
		assertTrue(SignWriter.armed());
		SignWriter.clear();
		assertFalse(SignWriter.armed());
	}

	@Test void aMessageIsReadAsTheCharactersAPlayerSees() {
		assertEquals("THE MIDWAY", SignText.plain("{\"text\":\"THE MIDWAY\"}"));
		assertEquals("", SignText.plain("{\"text\":\"\"}"));
		assertEquals("", SignText.plain(""));
		// A hand-made or Litematica-authored sign may carry a bare string or `extra` parts. Losing
		// those to an exception would blank a sign that has perfectly good text.
		assertEquals("plain", SignText.plain("\"plain\""));
		assertEquals("ab", SignText.plain("{\"text\":\"a\",\"extra\":[{\"text\":\"b\"}]}"));
		assertEquals("not json at all", SignText.plain("not json at all"));
	}

	@Test void tileEntitiesDecodeAtTheSameCornerAsTheCells() throws Exception {
		CompoundTag region = new CompoundTag();
		CompoundTag size = new CompoundTag();
		size.putInt("x", 4); size.putInt("y", 4); size.putInt("z", 4);
		CompoundTag pos = new CompoundTag();
		pos.putInt("x", 0); pos.putInt("y", 0); pos.putInt("z", 0);
		region.put("Size", size);
		region.put("Position", pos);
		ListTag tiles = new ListTag();
		tiles.add(signTile(1, 2, 3, "LOST PLATEAU"));
		CompoundTag notASign = new CompoundTag();
		notASign.putString("id", "minecraft:chest");
		notASign.putInt("x", 0); notASign.putInt("y", 0); notASign.putInt("z", 0);
		tiles.add(notASign);
		region.put("TileEntities", tiles);
		CompoundTag regions = new CompoundTag();
		regions.put("main", region);
		CompoundTag root = new CompoundTag();
		root.put("Regions", regions);

		BlockPos origin = new BlockPos(100, 60, -40);
		Map<Long, SignText> signs = LitematicReader.signs(root, origin);
		// Keyed in WORLD coordinates off the design's own origin - the text has to land on the same
		// blocks the cells did, or every board reads the wrong sign's words.
		assertEquals(1, signs.size(), "a chest is not a sign");
		SignText text = signs.get(new BlockPos(101, 62, -37).asLong());
		assertNotNull(text, "sign should decode at origin + its region-relative position");
		assertEquals("LOST PLATEAU", text.front().get(0));
		assertEquals(4, text.front().size(), "always four lines, padded");
		assertFalse(text.blank());
	}

	@Test void aRegionWithNoTileEntitiesIsADesignWithNoSigns() throws Exception {
		CompoundTag region = new CompoundTag();
		CompoundTag size = new CompoundTag();
		size.putInt("x", 2); size.putInt("y", 2); size.putInt("z", 2);
		CompoundTag pos = new CompoundTag();
		pos.putInt("x", 0); pos.putInt("y", 0); pos.putInt("z", 0);
		region.put("Size", size);
		region.put("Position", pos);
		CompoundTag regions = new CompoundTag();
		regions.put("main", region);
		CompoundTag root = new CompoundTag();
		root.put("Regions", regions);
		// Most designs have none. That must not be an error, or every build refuses.
		assertTrue(LitematicReader.signs(root, BlockPos.ZERO).isEmpty());
	}

	@Test void aDeclinedCellIsHandedBackRatherThanBlockingOrStalling() {
		// Cauldrons are DECLINED, not unimplemented: preflight must not refuse a design for two
		// cells a human will place, the way it refused Park Complete's 350,000 for them.
		assertEquals("cauldron fill", ActionRecipe.manual("water_cauldron[level=3]"));
		assertNull(ActionRecipe.manual("stone"));
		assertNull(ActionRecipe.missingFor("water_cauldron[level=3]"));
		var cells = List.of(new Work.Cell(BlockPos.ZERO, "water_cauldron[level=3]"));
		assertDoesNotThrow(() -> ActionRecipe.require(cells));

		// ...and it must leave the todo, or the printer burns its tries on a cell it can never
		// satisfy, which from the outside is indistinguishable from a stall.
		var split = new Work.Split("x", List.of(), List.of(), 0, 0, null, List.of(),
			List.of(new Work.Cell(BlockPos.ZERO, "water_cauldron[level=3]")));
		assertTrue(split.placementComplete(), "the loop's own part is finished, so it must advance");
		assertFalse(split.complete(), "the DESIGN is not finished, and must not claim to be");
		assertEquals(1, split.manualLeft().get("cauldron fill"));
		assertEquals(1, split.total(), "declined work is still work, and still counted");
	}

	@Test void aWholeCircuitIsHandedToACommissioningPass() {
		// Rails, repeaters, comparators AND dust, together. A circuit half-laid by the loop and
		// half by hand is worse than one pass owning all of it - and a repeater's facing convention
		// is an open known-wrong here, which 1868 unattended placements would stamp in invisibly.
		for (String state : List.of("powered_rail[shape=north_south]", "detector_rail", "rail",
				"repeater[facing=east,delay=2]", "comparator[facing=north,mode=compare]",
				"redstone_wire[power=4]", "redstone_wire[power=0]")) {
			assertEquals("redstone/rail commissioning", ActionRecipe.manual(state), state);
			assertNull(ActionRecipe.missingFor(state), state + " must not REFUSE the design");
		}
		// A redstone TORCH is an ordinary block and stays automated - it is not part of the gate.
		assertNull(ActionRecipe.manual("redstone_wall_torch[facing=north]"));
		assertNull(ActionRecipe.manual("redstone_block"));
		var cells = List.of(new Work.Cell(BlockPos.ZERO, "repeater[facing=east,delay=2]"));
		assertDoesNotThrow(() -> ActionRecipe.require(cells));
	}

	@Test void onlyASignThisBuildKnowsIsIntercepted() {
		SignWriter.clear();
		BlockPos mine = new BlockPos(5, 70, 5), theirs = new BlockPos(9, 70, 9);
		SignWriter.arm(Map.of(mine.asLong(),
			new SignText(List.of("BASE CAMP", "", "", ""), List.of("", "", "", ""), false, "black")));
		assertTrue(SignWriter.intercept(mine, true));
		// A PLAYER's own sign must still open its editor. Swallowing that would be far worse than
		// doing nothing: they would type into a screen that never appears.
		assertFalse(SignWriter.intercept(theirs, true));
		assertEquals(1, SignWriter.pendingCount());
		SignWriter.clear();
		assertFalse(SignWriter.intercept(mine, true), "a stopped build owns no positions");
		assertEquals(0, SignWriter.pendingCount());
	}
}

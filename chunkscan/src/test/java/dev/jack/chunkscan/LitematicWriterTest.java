package dev.jack.chunkscan;

import net.minecraft.SharedConstants;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtIo;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.BlockState;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Writes build/test-out/synthetic.litematic with the real writer plus synthetic.ids (expected palette
 * indices, one per line in (y,z,x) order). verify_synthetic.py then decodes the file with mcbuild
 * and compares — that's the cross-implementation check that matters.
 */
class LitematicWriterTest {
	static final int SX = 4, SY = 3, SZ = 5;

	@BeforeAll
	static void boot() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@Test
	void packRoundTripsAcrossLongBoundaries() {
		for (int bits : new int[]{2, 3, 5, 7, 11}) {
			int[] ids = new int[1000];
			for (int i = 0; i < ids.length; i++) ids[i] = (i * 7919) % (1 << bits);
			long[] packed = LitematicWriter.pack(ids, bits);
			int[] back = unpack(packed, ids.length, bits);
			assertArrayEquals(ids, back, "bits=" + bits);
		}
	}

	@Test
	void bitsForMatchesMcbuild() {
		assertEquals(2, LitematicWriter.bitsFor(1));
		assertEquals(2, LitematicWriter.bitsFor(2));
		assertEquals(2, LitematicWriter.bitsFor(4));
		assertEquals(3, LitematicWriter.bitsFor(5));
		assertEquals(4, LitematicWriter.bitsFor(16));
		assertEquals(5, LitematicWriter.bitsFor(17));
	}

	@Test
	void writesSyntheticFile() throws Exception {
		List<BlockState> palette = new ArrayList<>();
		palette.add(Blocks.AIR.defaultBlockState());
		palette.add(Blocks.STONE.defaultBlockState());
		palette.add(Blocks.OAK_STAIRS.defaultBlockState().setValue(StairBlock.FACING, Direction.EAST));
		palette.add(Blocks.CHEST.defaultBlockState());
		palette.add(Blocks.GLASS.defaultBlockState()); // 5 entries -> 3 bits

		int[] ids = new int[SX * SY * SZ];
		long nonAir = 0;
		for (int y = 0; y < SY; y++)
			for (int z = 0; z < SZ; z++)
				for (int x = 0; x < SX; x++) {
					int v = (x + y * 2 + z * 3) % 5;
					if (y == 2 && x > 1) v = 0;
					ids[(y * SZ + z) * SX + x] = v;
					if (v != 0) nonAir++;
				}

		CompoundTag chest = new CompoundTag();
		chest.putString("id", "minecraft:chest");
		chest.putInt("x", 1); chest.putInt("y", 0); chest.putInt("z", 2);

		Capture cap = new Capture(100, 64, -200, SX, SY, SZ, ids, palette, List.of(chest), List.of(), nonAir, List.of(), List.of());
		Path out = Path.of("build", "test-out");
		Files.createDirectories(out);
		Path lit = out.resolve("synthetic.litematic");
		LitematicWriter.write(lit, cap, "synthetic", "test", "unit test");

		StringBuilder sb = new StringBuilder();
		for (int v : ids) sb.append(v).append('\n');
		Files.writeString(out.resolve("synthetic.ids"), sb.toString());

		CompoundTag root = NbtIo.readCompressed(lit, net.minecraft.nbt.NbtAccounter.unlimitedHeap());
		assertEquals(7, root.getIntOr("Version", -1));
		assertEquals(LitematicWriter.dataVersion(), root.getIntOr("MinecraftDataVersion", -1));
	}

	private static int[] unpack(long[] longs, int volume, int bits) {
		int[] out = new int[volume];
		long mask = (1L << bits) - 1;
		for (int i = 0; i < volume; i++) {
			long off = (long) i * bits;
			int li = (int) (off >> 6), sb = (int) (off & 63);
			long v = longs[li] >>> sb;
			if (sb + bits > 64) v |= longs[li + 1] << (64 - sb);
			out[i] = (int) (v & mask);
		}
		return out;
	}
}

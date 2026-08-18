package dev.jack.chunkscan;

import net.minecraft.SharedConstants;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.LongArrayTag;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.NbtUtils;
import net.minecraft.world.level.block.state.BlockState;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

/**
 * Writes a {@link Capture} as a Litematica schematic (Version 7 / SubVersion 1), single region,
 * region position (0,0,0). Bit packing straddles long boundaries — Litematica's own format,
 * not the vanilla padded one — with bits = max(2, ceil(log2(paletteSize))).
 */
final class LitematicWriter {
	private LitematicWriter() {}

	static void write(Path file, Capture cap, String name, String author, String description) throws IOException {
		CompoundTag root = new CompoundTag();
		root.putInt("Version", 7);
		root.putInt("SubVersion", 1);
		root.putInt("MinecraftDataVersion", dataVersion());
		root.put("Metadata", metadata(cap, name, author, description));
		CompoundTag regions = new CompoundTag();
		regions.put(name, region(cap));
		root.put("Regions", regions);
		NbtIo.writeCompressed(root, file);
	}

	static int dataVersion() {
		return SharedConstants.getCurrentVersion().dataVersion().version();
	}

	private static CompoundTag metadata(Capture cap, String name, String author, String description) {
		long now = System.currentTimeMillis();
		CompoundTag md = new CompoundTag();
		md.putString("Name", name);
		md.putString("Author", author);
		md.putString("Description", description);
		md.putInt("RegionCount", 1);
		md.putInt("TotalVolume", (int) Math.min(Integer.MAX_VALUE, cap.volume()));
		md.putInt("TotalBlocks", (int) Math.min(Integer.MAX_VALUE, cap.nonAirCount()));
		md.putLong("TimeCreated", now);
		md.putLong("TimeModified", now);
		md.put("EnclosingSize", vec3(cap.sizeX(), cap.sizeY(), cap.sizeZ()));
		return md;
	}

	private static CompoundTag region(Capture cap) {
		CompoundTag reg = new CompoundTag();
		reg.put("Position", vec3(0, 0, 0));
		reg.put("Size", vec3(cap.sizeX(), cap.sizeY(), cap.sizeZ()));
		reg.put("BlockStatePalette", palette(cap.palette()));
		reg.put("BlockStates", new LongArrayTag(pack(cap.ids(), bitsFor(cap.palette().size()))));
		ListTag tiles = new ListTag();
		tiles.addAll(cap.tileEntities());
		reg.put("TileEntities", tiles);
		ListTag ents = new ListTag();
		ents.addAll(cap.entities());
		reg.put("Entities", ents);
		reg.put("PendingBlockTicks", new ListTag());
		reg.put("PendingFluidTicks", new ListTag());
		return reg;
	}

	private static ListTag palette(List<BlockState> states) {
		ListTag list = new ListTag();
		for (BlockState s : states) list.add(NbtUtils.writeBlockState(s));
		return list;
	}

	static int bitsFor(int paletteSize) {
		return Math.max(2, 32 - Integer.numberOfLeadingZeros(Math.max(1, paletteSize - 1)));
	}

	static long[] pack(int[] values, int bits) {
		long[] out = new long[(int) (((long) values.length * bits + 63) / 64)];
		long mask = (1L << bits) - 1;
		for (int i = 0; i < values.length; i++) {
			long v = values[i] & mask;
			long off = (long) i * bits;
			int li = (int) (off >> 6), sb = (int) (off & 63);
			out[li] |= v << sb;
			if (sb + bits > 64) out[li + 1] |= v >>> (64 - sb);
		}
		return out;
	}

	private static CompoundTag vec3(int x, int y, int z) {
		CompoundTag t = new CompoundTag();
		t.putInt("x", x);
		t.putInt("y", y);
		t.putInt("z", z);
		return t;
	}
}

package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import net.minecraft.nbt.*;
import java.io.IOException;
import java.nio.file.Path;
import java.util.*;

/** Reads unrotated Litematica regions at an explicitly recorded world origin. Air never means dig. */
final class LitematicReader {
	static List<Work.Cell> read(Path file, BlockPos origin) throws IOException {
		return decode(NbtIo.readCompressed(file, NbtAccounter.create(256L * 1024 * 1024)), origin);
	}

	static List<Work.Cell> decode(CompoundTag root, BlockPos origin) throws IOException {
		int version = root.getIntOr("Version", 0);
		if (version < 5 || version > 7) throw new IOException("Unsupported litematic version: " + version);
		CompoundTag regions = root.getCompound("Regions").orElseThrow(() -> new IOException("Missing Regions"));
		Map<Long, Work.Cell> cells = new LinkedHashMap<>();
		long total = 0;
		for (String key : regions.keySet()) {
			CompoundTag r = regions.getCompound(key).orElseThrow(() -> new IOException("Invalid region " + key));
			CompoundTag size = r.getCompound("Size").orElseThrow(() -> new IOException("Missing Size"));
			CompoundTag pos = r.getCompound("Position").orElseThrow(() -> new IOException("Missing Position"));
			int sx = integer(size, "x"), sy = integer(size, "y"), sz = integer(size, "z");
			long nx = Math.abs((long)sx), ny = Math.abs((long)sy), nz = Math.abs((long)sz);
			if (nx == 0 || ny == 0 || nz == 0 || nx > 64_000_000 || ny > 64_000_000 || nz > 64_000_000
				|| nx * ny > 64_000_000 || nx * ny * nz > 64_000_000) throw new IOException("Invalid/oversized region");
			long volume = nx * ny * nz;
			if ((total += volume) > 64_000_000) throw new IOException("Schematic exceeds 64 million cells");
			BlockPos base = origin.offset(integer(pos, "x") + Math.min(0, sx + 1),
				integer(pos, "y") + Math.min(0, sy + 1), integer(pos, "z") + Math.min(0, sz + 1));
			ListTag pal = r.getList("BlockStatePalette").orElseThrow(() -> new IOException("Missing palette"));
			if (pal.isEmpty()) throw new IOException("Empty palette");
			List<String> states = new ArrayList<>();
			for (Tag tag : pal) {
				CompoundTag p = tag.asCompound().orElseThrow(() -> new IOException("Invalid palette entry"));
				String name = p.getString("Name").orElseThrow(() -> new IOException("Missing block name"));
				if (!name.startsWith("minecraft:")) throw new IOException("Unsupported block namespace: " + name);
				String state = name.substring(10);
				CompoundTag props = p.getCompoundOrEmpty("Properties");
				List<String> pairs = new ArrayList<>();
				for (String prop : new TreeSet<>(props.keySet())) pairs.add(prop + "=" + props.getString(prop)
					.orElseThrow(() -> new IOException("Invalid property")));
				states.add(state + (pairs.isEmpty() ? "" : "[" + String.join(",", pairs) + "]"));
			}
			int bits = LitematicWriter.bitsFor(states.size());
			long[] packed = r.getLongArray("BlockStates").orElseThrow(() -> new IOException("Missing BlockStates"));
			if (packed.length != (volume * bits + 63) / 64) throw new IOException("Invalid packed block length");
			long mask = (1L << bits) - 1;
			for (int i = 0; i < volume; i++) {
				long off = (long)i * bits;
				int word = (int)(off >>> 6), shift = (int)(off & 63);
				long id = packed[word] >>> shift;
				if (shift + bits > 64) id |= packed[word + 1] << (64 - shift);
				id &= mask;
				if (id >= states.size()) throw new IOException("Palette index out of range");
				String state = states.get((int)id);
				if (Set.of("air", "cave_air", "void_air").contains(state)) continue;
				BlockPos at = base.offset((int)(i % nx), (int)(i / (nx * nz)), (int)(i / nx % nz));
				Work.Cell cell = new Work.Cell(at, state);
				Work.Cell old = cells.putIfAbsent(at.asLong(), cell);
                if (cells.size() > 1_000_000) throw new IOException("Schematic exceeds one million non-air cells");
				if (old != null && !old.equals(cell)) throw new IOException("Conflicting overlapping regions at " + at);
			}
		}
		return List.copyOf(cells.values());
	}

	private static int integer(CompoundTag tag, String key) throws IOException {
		return tag.getInt(key).orElseThrow(() -> new IOException("Missing integer " + key));
	}
}

package dev.jack.chunkscan;

import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;

import java.util.ArrayList;
import java.util.List;

/**
 * What a sign READS, which is a different thing from the sign block itself.
 *
 * <p>A sign is two things in two halves of a litematic - a palette entry and a tile entity - and
 * only the first has ever reached this mod. Placing the block without this is a blank board, which
 * is exactly the silent failure {@code Park Complete} shipped 177 of once already.
 *
 * <p>26.x nests the lines under {@code front_text}/{@code back_text} as a {@code messages} list of
 * JSON text components, and there are ALWAYS FOUR: a sign with two lines still stores four, and a
 * shorter list is a sign the game refuses to load. {@code mcbuild/gen/canvas.py::sign_text} is the
 * writer this parses, so the two cannot drift.
 */
record SignText(List<String> front, List<String> back, boolean glowing, String colour) {

	/** A sign whose every line is empty - what a cell with no recorded text would place. */
	boolean blank() {
		for (String line : front) if (!line.isEmpty()) return false;
		for (String line : back) if (!line.isEmpty()) return false;
		return true;
	}

	/**
	 * Decode one {@code minecraft:sign} tile entity, or null when this is some other block entity.
	 *
	 * <p>Never throws on a malformed side: a sign we cannot read must fail the PREFLIGHT gate as
	 * "no text recorded", not abort the decode of a design's other nine hundred cells.
	 */
	static SignText of(CompoundTag tile) {
		String id = tile.getString("id").orElse("");
		if (!id.equals("minecraft:sign") && !id.equals("sign")
			&& !id.equals("minecraft:hanging_sign") && !id.equals("hanging_sign")) return null;
		CompoundTag front = tile.getCompound("front_text").orElse(null);
		CompoundTag back = tile.getCompound("back_text").orElse(null);
		if (front == null && back == null) return null;
		boolean glowing = front != null && front.getByteOr("has_glowing_text", (byte) 0) != 0;
		String colour = front == null ? "black" : front.getString("color").orElse("black");
		return new SignText(lines(front), lines(back), glowing, colour);
	}

	/** The four lines of one side, padded, as PLAIN text rather than as JSON components. */
	private static List<String> lines(CompoundTag side) {
		List<String> out = new ArrayList<>(4);
		if (side != null) {
			ListTag messages = side.getList("messages").orElse(null);
			if (messages != null) for (Tag message : messages) {
				if (out.size() == 4) break;
				out.add(plain(message.asString().orElse("")));
			}
		}
		while (out.size() < 4) out.add("");
		return List.copyOf(out);
	}

	/**
	 * One stored message as the characters a player would read.
	 *
	 * <p>The writer emits {@code {"text":"FOO"}}, but a hand-made or Litematica-authored sign may
	 * carry a bare string or a component with {@code extra} parts, so this degrades rather than
	 * refusing: an unparseable message becomes its own raw text, which is still closer to right
	 * than an empty line.
	 */
	static String plain(String message) {
		if (message == null || message.isEmpty()) return "";
		try {
			JsonElement parsed = JsonParser.parseString(message);
			return flatten(parsed);
		} catch (Exception notJson) {
			return message;
		}
	}

	private static String flatten(JsonElement element) {
		if (element == null || element.isJsonNull()) return "";
		if (element.isJsonPrimitive()) return element.getAsString();
		if (element.isJsonArray()) {
			StringBuilder joined = new StringBuilder();
			for (JsonElement part : element.getAsJsonArray()) joined.append(flatten(part));
			return joined.toString();
		}
		if (!element.isJsonObject()) return "";
		var object = element.getAsJsonObject();
		StringBuilder joined = new StringBuilder();
		if (object.has("text") && object.get("text").isJsonPrimitive())
			joined.append(object.get("text").getAsString());
		if (object.has("extra")) joined.append(flatten(object.get("extra")));
		return joined.toString();
	}
}

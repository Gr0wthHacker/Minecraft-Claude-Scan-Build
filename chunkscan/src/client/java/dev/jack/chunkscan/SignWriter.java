package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.network.protocol.game.ServerboundSignUpdatePacket;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashMap;
import java.util.Map;

/**
 * The second half of placing a sign: saying what it reads.
 *
 * <p>A sign is a palette entry AND a tile entity, and only the first is something you click. When
 * the sign lands the server asks the client to open its editor; the ONE update the client sends
 * back is the text. So this is not a screen we drive - it is a screen we decline to open, because
 * of a version fact that decides the whole design:
 *
 * <p><b>ON A 1.19 SERVER A SIGN IS EDITABLE EXACTLY ONCE.</b> The close-then-correct shape - let
 * vanilla send its empty update, then send the real one - reads fine and loses every line, because
 * the second packet arrives at a sign the server has already sealed. There is no retry. So the
 * editor is cancelled at the packet and this sends the single update itself.
 *
 * <p>A position with no recorded text is NOT intercepted: the editor opens as usual and a human
 * types. Silently swallowing a player's own sign would be far worse than doing nothing.
 */
public final class SignWriter {
	private SignWriter() {}

	/** What the active build's signs say, by {@link BlockPos#asLong()}. Empty when idle. */
	private static Map<Long, SignText> wanted = Map.of();
	/** Editors we cancelled and owe an update, drained on the client thread. */
	private static final Deque<Pending> queue = new ArrayDeque<>();
	private static int written, refused;

	private record Pending(BlockPos pos, boolean front, SignText text) {}

	static void arm(Map<Long, SignText> signs) {
		wanted = signs == null ? Map.of() : Map.copyOf(signs);
	}

	static void clear() {
		wanted = Map.of();
		queue.clear();
		written = 0;
		refused = 0;
	}

	static int written() { return written; }

	static int pendingCount() { return queue.size(); }

	/** Is this a sign THIS BUILD placed and knows the words for? */
	static SignText textFor(BlockPos pos) {
		return pos == null ? null : wanted.get(pos.asLong());
	}

	/**
	 * Called from the packet mixin. True when we have taken responsibility for this sign, in which
	 * case the vanilla editor must not open.
	 */
	public static boolean intercept(BlockPos pos, boolean front) {
		SignText text = textFor(pos);
		if (text == null || text.blank()) return false;
		queue.add(new Pending(pos.immutable(), front, text));
		return true;
	}

	/**
	 * Send the updates we owe, on the client thread.
	 *
	 * <p>Deliberately one per tick. The server applies these to a block it has just created, and a
	 * burst of them is both the least testable thing here and the easiest to have throttled.
	 */
	static void pump(Minecraft mc) {
		if (queue.isEmpty()) return;
		if (mc.getConnection() == null) { queue.clear(); return; }
		Pending next = queue.poll();
		java.util.List<String> lines = next.front() ? next.text().front() : next.text().back();
		try {
			mc.getConnection().send(new ServerboundSignUpdatePacket(next.pos(), next.front(),
				lines.get(0), lines.get(1), lines.get(2), lines.get(3)));
			written++;
		} catch (Exception failed) {
			// A refused update is a blank sign standing in the world, so it is COUNTED rather than
			// swallowed: `/cscan why` is where a build that placed boards nobody can read shows up.
			refused++;
		}
	}

	static String report() {
		if (written == 0 && refused == 0 && queue.isEmpty()) return "";
		return "signs written " + written + (refused > 0 ? ", " + refused + " refused" : "")
			+ (queue.isEmpty() ? "" : ", " + queue.size() + " pending");
	}
}

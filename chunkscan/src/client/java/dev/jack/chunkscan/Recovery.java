package dev.jack.chunkscan;

/**
 * What to do when the flight is not working, in escalating order.
 *
 * <p>Every stuck-loop fixed so far has been fixed by understanding ONE situation: the shaft, the
 * ceiling, the unloaded chunk, the wall the route thought was clear. That approach has a floor under
 * it — there will always be a situation nobody thought of, and Jack named the shape of it: <i>"there
 * is going to be times where its literally impossible to reach, e.g. if its in the center of many
 * layers because we built the wrong way in."</i> A design cell in the middle of a solid mass cannot
 * be placed by any amount of cleverness about flying.
 *
 * <p>So the last resort is not another special case. It is a LADDER, and the only thing it needs to
 * know is how long things have been going badly:
 *
 * <ol>
 *   <li><b>NONE</b> — normal flight. Bumping and re-routing are ordinary.</li>
 *   <li><b>BACK_OFF</b> — go back to somewhere that was definitely open. Most wedges are one bad
 *       approach, and the way out is the way in.</li>
 *   <li><b>CLIMB_OUT</b> — abandon the destination and rise into open sky. Above this island there
 *       is nothing to be stuck on, and from there every route is findable again.</li>
 *   <li><b>GO_HOME</b> — `/is`. When the way out is not up, not back, and not round, the only move
 *       left is to leave.</li>
 * </ol>
 *
 * <p><b>Sealed is not a stage, it is a shortcut.</b> Being in a closed pocket — built into something,
 * which is exactly Jack's case — makes every earlier rung pointless, so it goes straight to the top.
 * That is the difference {@link Nav#pocket} exists to measure.
 */
final class Recovery {
	/** Ticks of trouble before each rung. Twenty ticks to the second. */
	static final int BACK_OFF_AT = 100;      // 5s
	static final int CLIMB_OUT_AT = 200;     // 10s
	static final int GO_HOME_AT = 400;       // 20s

	/** Fewer reachable cells than this and you are shut in rather than merely stuck. */
	static final int SEALED_CELLS = 60;

	enum Stage { NONE, BACK_OFF, CLIMB_OUT, GO_HOME }

	private Recovery() {}

	/**
	 * @param troubleTicks how long the flight has been getting nowhere: bumping, routeless, or
	 *                     simply not moving while it has somewhere to be
	 * @param sealed       the reachable space around the player is a closed pocket
	 */
	static Stage stageFor(int troubleTicks, boolean sealed) {
		// Shut in: every rung below the top is about getting somewhere else in this world, and there
		// is nowhere else in this world to get to.
		if (sealed && troubleTicks >= BACK_OFF_AT) return Stage.GO_HOME;
		if (troubleTicks >= GO_HOME_AT) return Stage.GO_HOME;
		if (troubleTicks >= CLIMB_OUT_AT) return Stage.CLIMB_OUT;
		if (troubleTicks >= BACK_OFF_AT) return Stage.BACK_OFF;
		return Stage.NONE;
	}

	/**
	 * Is the flight in trouble this tick?
	 *
	 * <p>Deliberately broad. The point of the ladder is that it does not need to know WHICH problem
	 * it is having — the specific handlers upstream have already had their turn, and if the flight is
	 * still not moving after all of them, the reason has stopped mattering.
	 *
	 * <p>Movement is the one honest signal, and it is the one that cannot be argued with: a flight
	 * that is covering ground is fine whatever else is true of it.
	 */
	static boolean inTrouble(boolean moving, boolean hasTarget, boolean arrived) {
		return hasTarget && !arrived && !moving;
	}
}

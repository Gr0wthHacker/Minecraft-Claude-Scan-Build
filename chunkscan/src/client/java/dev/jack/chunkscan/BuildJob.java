package dev.jack.chunkscan;

/** One visible owner for a followed schematic's current intent. */
final class BuildJob {
	enum Phase { IDLE, PLAN, LOOK, FETCH, BUILD, PARKED, COMPLETE }
	private static Phase phase = Phase.IDLE;
	private static String detail = "";
	private BuildJob() {}
	static void start() { phase = Phase.PLAN; detail = "planning from live world"; }
	static void stop() { phase = Phase.IDLE; detail = ""; }
	static void replan() { phase = Phase.PLAN; detail = "replanning after resume"; }
	static Phase phase() { return phase; }
	static String detail() { return detail; }
	static void decide(Loop.Phase next) {
		phase = switch (next) {
			case LOOK -> Phase.LOOK;
			case FETCH -> Phase.FETCH;
			case BUILD -> Phase.BUILD;
			case COMPLETE -> Phase.COMPLETE;
			case DEAD_END, PACK_FULL -> Phase.PARKED;
		};
		detail = next.name().toLowerCase(java.util.Locale.ROOT);
	}
	static boolean permits(ActionGate.Owner owner) {
		return switch (owner) {
			case PRINT -> phase == Phase.BUILD;
			// A WITHDRAWAL IS NOT A PHASE. ChestScan opens a chest at a DEAD_END, Unbox opens one it
			// has just placed mid-BUILD, and a helper whose tick is refused cannot run its own
			// timer - it is busy for ever and the loop hovers beside it. Only the PRINTER answers
			// to the phase.
			case WITHDRAW -> true;
			default -> true;
		};
	}
}

package dev.jack.chunkscan;

import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The failure cooldown — the difference between a loop you can leave alone and one you cannot.
 *
 * <p>The first version had a single global FAILED phase and the caller gated on it, so ONE bad chest
 * disabled restocking for the rest of the session: the loop flew there and sat forever with nothing
 * in the log to say why. On an unattended alt that is an hour of nothing.
 */
class WithdrawTest {
	@BeforeEach
	void clean() {
		Withdraw.clearFailures();
	}

	@Test
	void aChestWithNoHistoryIsAlwaysWorthTrying() {
		assertFalse(Withdraw.recentlyFailed(new BlockPos(0, 100, 0), System.currentTimeMillis()));
	}

	@Test
	void failureIsAPropertyOfTheCHEST_notOfTheWithdrawer() {
		// The whole bug: one bad chest must not disable every other chest.
		Withdraw.noteFailureForTest(new BlockPos(0, 100, 0));
		long now = System.currentTimeMillis();
		assertTrue(Withdraw.recentlyFailed(new BlockPos(0, 100, 0), now));
		assertFalse(Withdraw.recentlyFailed(new BlockPos(9, 100, 9), now),
			"a different chest was punished for its neighbour's failure");
	}

	@Test
	void theCoolingOffPeriodExpires() {
		// It must retry eventually: a chest can be refilled, and a timeout can be lag rather than a
		// missing container. Permanent blacklisting turns a hiccup into a dead session.
		BlockPos p = new BlockPos(0, 100, 0);
		Withdraw.noteFailureForTest(p);
		long later = System.currentTimeMillis() + Withdraw.RETRY_AFTER_MS + 1;
		assertFalse(Withdraw.recentlyFailed(p, later));
	}

	@Test
	void followClearsFailuresWhenItStarts() {
		// A new session should not inherit the last one's grudges.
		Withdraw.noteFailureForTest(new BlockPos(0, 100, 0));
		Withdraw.clearFailures();
		assertFalse(Withdraw.recentlyFailed(new BlockPos(0, 100, 0), System.currentTimeMillis()));
	}

	@Test
	void theRetryWindowIsLongEnoughToMatterAndShortEnoughToRecover() {
		assertTrue(Withdraw.RETRY_AFTER_MS >= 10_000, "too short: it would hammer a dead chest");
		assertTrue(Withdraw.RETRY_AFTER_MS <= 300_000, "too long: a lag blip costs you the session");
	}

	@Test
	void clicksArePacedRatherThanInstant() {
		// Emptying a double chest in a single tick is not a person, and the server has an opinion
		// about how fast slots can be clicked.
		assertTrue(Withdraw.CLICK_EVERY >= 1);
		assertTrue(Withdraw.REACH <= 5.0, "beyond vanilla reach the server rejects the interaction");
	}
}

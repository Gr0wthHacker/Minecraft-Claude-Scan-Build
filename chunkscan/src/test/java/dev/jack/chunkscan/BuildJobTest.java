package dev.jack.chunkscan;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class BuildJobTest {
	@Test void onlyThePlannedExecutorCanAct() {
		BuildJob.start();
		BuildJob.decide(Loop.Phase.FETCH);
		assertTrue(BuildJob.permits(ActionGate.Owner.WITHDRAW));
		assertFalse(BuildJob.permits(ActionGate.Owner.PRINT));
		BuildJob.decide(Loop.Phase.BUILD);
		assertTrue(BuildJob.permits(ActionGate.Owner.PRINT));
		assertTrue(BuildJob.permits(ActionGate.Owner.WITHDRAW),
			"Unbox and ChestScan open chests outside FETCH; refusing them deadlocked the loop");
	}
	@Test void aRejoinReplansInsteadOfContinuingAStaleTrip() {
		BuildJob.decide(Loop.Phase.FETCH);
		BuildJob.replan();
		assertEquals(BuildJob.Phase.PLAN, BuildJob.phase());
		assertFalse(BuildJob.permits(ActionGate.Owner.PRINT));
		assertTrue(BuildJob.permits(ActionGate.Owner.WITHDRAW), "a withdrawal is never phase-gated");
	}
}

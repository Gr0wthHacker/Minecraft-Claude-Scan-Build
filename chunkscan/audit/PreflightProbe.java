package dev.jack.chunkscan;

import java.nio.file.Path;

/** Read-only production-sidecar preflight probe; never starts a client or changes a profile. */
public final class PreflightProbe {
    public static void main(String[] args) {
        try {
            Designs.requireAutonomousApproval(Path.of(args[0]), args[1]);
            System.out.println("APPROVED");
        } catch (Exception rejected) {
            System.out.println("REJECTED: " + rejected.getMessage());
        }
    }
}

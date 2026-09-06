package dev.jack.chunkscan;

/** Client-thread adapter connecting operation lifetimes to the common actuator gate. */
final class AutomationControl {
    private static final ActionGate GATE = new ActionGate();
    private static ActionGate.Owner caller;
    private AutomationControl() {}

    static boolean active(ActionGate.Owner owner) {
        return switch (owner) {
            case PRINT -> Printer.busy();
            case DIG -> Digger.busy();
            case WITHDRAW -> Withdraw.busy();
            case UNBOX -> Unbox.running();
            case CRAFT -> Crafter.phase() != Crafter.Phase.IDLE && Crafter.phase() != Crafter.Phase.DONE
                && Crafter.phase() != Crafter.Phase.FAILED;
            case SMELT -> Smelter.running();
            case SHOP -> Shop.armed() && Screens.container() != null;
            case FARM -> Farm.running() && Screens.container() == null;
            case PHOTO -> Photo.running() && Screens.container() == null;
        };
    }

    static boolean enter(ActionGate.Owner owner) {
		// THE JOB PHASE GATES THE PRINTER AND NOTHING ELSE. A withdrawal is started by ChestScan at
        // a dead end and by Unbox mid-build - both legitimately outside FETCH - and a gate that
        // refused them here never let Withdraw.tick run its own timer: busy() stayed true for ever,
        // Hud.advance returned early above every clock, and the body hovered at the chest in
        // silence until /cscan stop. See BuildJob.permits.
        if (Hud.following() && owner == ActionGate.Owner.PRINT && !BuildJob.permits(owner)) return false;
        if (Printer.busy() && owner != ActionGate.Owner.PRINT) return false;
        if (caller == ActionGate.Owner.FARM && Digger.busy() && owner == ActionGate.Owner.PRINT) return false;
        boolean delegated = (GATE.owner() == ActionGate.Owner.UNBOX && Unbox.phase() == Unbox.Phase.TAKING)
            || caller == ActionGate.Owner.FARM;
        return GATE.enter(owner, AutomationControl::active, delegated);
    }

    static String helper(ActionGate.Owner owner, java.util.function.Supplier<String> tick) {
        if (!active(owner) || !enter(owner)) return null;
        ActionGate.Owner previous = caller;
        caller = owner;
        try { return tick.get(); }
        finally { caller = previous; }
    }

    static boolean blocksMovement() {
        GATE.refresh(AutomationControl::active);
        var owner = GATE.owner();
        return Printer.busy() || (owner == ActionGate.Owner.FARM && Digger.busy())
            || (owner != null && owner != ActionGate.Owner.FARM && owner != ActionGate.Owner.PHOTO);
    }

    static boolean ownsGuidance() {
        GATE.refresh(AutomationControl::active);
        return GATE.owner() == ActionGate.Owner.FARM || GATE.owner() == ActionGate.Owner.PHOTO;
    }

    static void clear() { GATE.clear(); }
}

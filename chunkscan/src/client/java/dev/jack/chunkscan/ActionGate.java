package dev.jack.chunkscan;

import java.util.function.Predicate;

/** Non-preemptive ownership across ticks; a completed operation yields to the next requester. */
final class ActionGate {
    enum Owner { PRINT, DIG, WITHDRAW, UNBOX, CRAFT, SMELT, SHOP, FARM, PHOTO, MINE }
    private Owner owner;

    boolean enter(Owner request, Predicate<Owner> active, boolean delegated) {
        refresh(active);
        if (owner == null) owner = request;
        return owner == request || (delegated && ((owner == Owner.UNBOX && request == Owner.WITHDRAW)
            || (owner == Owner.FARM && (request == Owner.DIG || request == Owner.PRINT))
            // A mining trip is a DIG, a PLACE (bridging, and plugging a lava face) and a
            // WITHDRAW (emptying the pack into the stash) in one cycle. It holds the gate across
            // all three rather than handing it back between them, because the cycle is the job.
            || (owner == Owner.MINE && (request == Owner.DIG || request == Owner.PRINT
                || request == Owner.WITHDRAW))));
    }

    void refresh(Predicate<Owner> active) {
        if (owner != null && !active.test(owner)) owner = null;
    }

    Owner owner() { return owner; }
    void clear() { owner = null; }
}

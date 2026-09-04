package dev.jack.chunkscan.mixin;

import dev.jack.chunkscan.MenuObservations;
import dev.jack.chunkscan.SignWriter;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.network.protocol.game.ClientboundContainerSetContentPacket;
import net.minecraft.network.protocol.game.ClientboundOpenScreenPacket;
import net.minecraft.network.protocol.game.ClientboundOpenSignEditorPacket;
import net.minecraft.network.protocol.game.ClientboundContainerSetSlotPacket;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ClientPacketListener.class)
abstract class ClientPacketListenerMixin {
    @Inject(method = "handleOpenScreen", at = @At("RETURN"))
    private void chunkscan$opened(ClientboundOpenScreenPacket packet, CallbackInfo ci) {
        MenuObservations.LIVE.opened(this, packet.getContainerId());
    }

    @Inject(method = "handleContainerContent", at = @At("RETURN"))
    private void chunkscan$content(ClientboundContainerSetContentPacket packet, CallbackInfo ci) {
        MenuObservations.LIVE.content(this, packet.containerId(), packet.items());
    }

    /**
     * A sign the builder placed writes itself; anyone else's opens the editor as usual.
     *
     * <p>HEAD and cancellable, not RETURN: on a 1.19 server the sign is editable exactly once, so
     * the vanilla editor must never get the chance to send its empty update first.
     */
    @Inject(method = "handleOpenSignEditor", at = @At("HEAD"), cancellable = true)
    private void chunkscan$signEditor(ClientboundOpenSignEditorPacket packet, CallbackInfo ci) {
        if (SignWriter.intercept(packet.getPos(), packet.isFrontText())) ci.cancel();
    }

    @Inject(method = "handleContainerSetSlot", at = @At("RETURN"))
    private void chunkscan$slot(ClientboundContainerSetSlotPacket packet, CallbackInfo ci) {
        MenuObservations.LIVE.slot(this, packet.getContainerId(), packet.getSlot(), packet.getItem());
    }
}
